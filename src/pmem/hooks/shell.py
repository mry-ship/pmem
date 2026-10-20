"""终端命令解析：会写到哪些文件、是否在跑脚本，以及命令里的 pmem search/record 调用。"""
from __future__ import annotations

import os
import re
from pathlib import Path

_NULL_TARGETS = {"$null", "/dev/null", "nul", "&1", "&2"}
# 1> 2> *> &> >| 都算；->、=> 是代码里的箭头。目标可带引号
_REDIRECT = re.compile(r"(?<![-=>])([0-9*&]?)>>?\|?\s*(&\d|'[^']*'|\"[^\"]*\"|[^\s|;&<>]+)")
_STDOUT_FDS = {"", "1", "*", "&"}
_PS_WRITERS = {"set-content", "add-content", "out-file", "new-item", "ni", "clear-content", "remove-item", "ri", "sc",
               "ac"}
_TEE = {"tee", "tee-object"}
# 命令里再套一层终端：powershell -Command "..."、cmd /c "..."、bash -c "..."，以及直接运行的脚本文件
_POWERSHELLS = {"powershell", "pwsh"}
_POSIX_SHELLS = {"bash", "sh", "zsh"}
_SHELL_SCRIPT_SUFFIXES = (".ps1", ".bat", ".cmd", ".sh")
_PS_VALUE_FLAGS = {"-executionpolicy", "-ep", "-windowstyle", "-outputformat", "-inputformat", "-workingdirectory",
                   "-configurationname"}
_MAX_NESTING = 3
# 跟在 pmem search 后面会吞掉输出的管道；输出被丢弃的检索不算查过
_DISCARD_STAGES = {"out-null", "out-file", "set-content", "add-content"}
VARIABLE_PATH = re.compile(r"[$%]|\{")
WILDCARD_PATH = re.compile(r"[*?\[]")
# bash -c、bash -lc、sh -ec：合在一起的短参数里带 c 就是内联命令
_POSIX_INLINE_FLAG = re.compile(r"-[a-zA-Z]*c[a-zA-Z]*")
_RM = {"rm", "del", "erase", "rmdir", "rd"}
_COPY = {"cp", "copy", "copy-item", "cpi"}
_MOVE = {"mv", "move", "move-item", "mi", "rename-item", "rni", "ren"}
_PATH_PARAMS = ("-path", "-literalpath", "-filepath", "-destination")
_SCRIPT_SUFFIXES = (".py", ".js", ".mjs", ".cjs")
_INTERPRETERS = {"python", "python3", "py", "node", "deno"}
_SCRIPT_MAX_BYTES = 200_000
_CODE_WRITES = re.compile(
    r"open\([^)]*['\"][wax]b?\+?['\"]|write_text|write_bytes|writeFileSync|appendFileSync|\.unlink\("
    r"|os\.(?:remove|rename|replace)\(|shutil\.(?:copy\w*|move|rmtree)\(|WriteAll\w+|AppendAll\w+"
)
_PATH_LITERAL = re.compile(r"['\"]([^'\"\s]*[/\\][^'\"\s]*|[^'\"\s/\\]+\.\w{1,8})['\"]")
_DOTNET_WRITE = re.compile(r"\[(?:System\.)?IO\.File\]::(?:WriteAll\w+|AppendAll\w+|Delete|Copy|Move)\(\s*['\"]([^'\"]+)",
                           re.IGNORECASE)
_PATCH_FILE = re.compile(r"^(?:\+\+\+ b|--- a)/(\S+)", re.MULTILINE)
# here-string（@' ... '@）与 heredoc（<<EOF ... EOF）的正文是数据，不是要执行的命令
_HERE_STRING = re.compile(r"@(['\"])[ \t]*\r?\n.*?\r?\n\1@", re.DOTALL)
_HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1([^\n]*)\n.*?\n[ \t]*\2[ \t]*(?=\r?\n|$)", re.DOTALL)
_CD = {"cd", "chdir", "set-location", "sl", "pushd", "push-location"}
# 只读命令：命令行里只有这些时不需要执行前后比对文件
_READ_ONLY = {
    "ls", "dir", "gci", "get-childitem", "cat", "type", "gc", "get-content", "head", "tail", "less", "more",
    "rg", "grep", "findstr", "select-string", "sls", "find", "where", "where.exe", "which", "get-command",
    "echo", "write-output", "write-host", "pwd", "get-location", "test-path", "get-item", "gi", "resolve-path",
    "select-object", "select", "sort-object", "sort", "measure-object", "measure", "format-table", "ft",
    "format-list", "fl", "out-string", "where-object", "?", "group-object", "wc",
    "get-date", "get-process", "env", "printenv", "date", "whoami", "hostname", "tree", "stat", "file",
    *_CD, "popd", "pop-location", "exit", "true", "false", "sleep", "start-sleep", "clear", "cls",
}
_GIT_READ_ONLY = {"status", "log", "diff", "show", "blame", "branch", "rev-parse", "ls-files", "ls-tree", "grep",
                  "remote", "describe", "shortlog", "cat-file", "reflog", "help", "version", "fetch"}
_SVN_READ_ONLY = {"status", "st", "stat", "log", "diff", "di", "info", "cat", "list", "ls", "blame", "praise",
                  "annotate", "ann", "propget", "pg", "proplist", "pl", "help", "?", "h", "--version"}
_PMEM_READ_ONLY = {"search", "graph", "list", "terms", "doctor", "report", "compact", "scan", "--help", "-h"}
# 只改变后面命令运行方式的前缀（sudo rm x 真正执行的是 rm），值为会吞掉下一个参数的选项
_PREFIXES = {
    "sudo": {"-u", "-g", "-p", "-C", "-D", "-U", "-h", "-r", "-t"}, "doas": {"-u", "-C"},
    "env": {"-u", "-C", "--unset", "--chdir"}, "command": set(), "builtin": set(),
    "nohup": set(), "exec": {"-a"}, "time": {"-f", "-o", "--format", "--output"}, "nice": {"-n"},
    "stdbuf": {"-i", "-o", "-e"},
}


def _strip_heredocs(command: str) -> str:
    command = _HERE_STRING.sub("''", command or "")
    return _HEREDOC.sub(lambda m: f"<<{m[2]}{m[3]}", command)


def _statements(command: str) -> list[str]:
    """按换行和 ; && || 拆成语句（管道还连在一起）；行尾的 ` 或 \\ 是续行，先接回去。"""
    return [statement for statement, _ in _statements_with_ops(command)]


def _statements_with_ops(command: str) -> list[tuple[str, str]]:
    """语句及其前面的连接符（第一条为空串）；`a || b` 里的 b 只在 a 失败时才执行。"""
    joined = re.sub(r"[`\\][ \t]*\r?\n", " ", _strip_heredocs(command))
    parts = re.split(r"\s*(\|\||&&|[;\r\n])\s*", joined)
    return [(parts[i], parts[i - 1] if i else "") for i in range(0, len(parts), 2)]


def _stages(statement: str) -> list[str]:
    # >| 是强制覆盖的重定向，不是管道
    return re.split(r"\s*(?<!>)\|\s*", statement)


def _segments(command: str) -> list[str]:
    """按换行和 ; && || | 拆成单条命令。"""
    return [stage for statement in _statements(command) for stage in _stages(statement)]


def _tokens(segment: str) -> list[str]:
    # 尾随的逗号、分号不属于路径（如 "a/b.py", 这样出现在列表里的写法）
    return [t.strip("'\"").rstrip(",;").strip("'\"") for t in re.findall(r"'[^']*'|\"[^\"]*\"|\S+", segment)]


def _program(token: str) -> str:
    return re.split(r"[\\/]", token)[-1].lower().removesuffix(".exe")


def _unwrap(tokens: list[str]) -> list[str]:
    """去掉 sudo、env A=1、command 这类前缀，留下真正执行的命令；前缀后面没有命令时原样返回（单独的 env 是只读）。"""
    while tokens and (prefix := _program(tokens[0])) in _PREFIXES:
        valued = _PREFIXES[prefix]
        i = 1
        while i < len(tokens) and (tokens[i].startswith("-") or (prefix == "env" and "=" in tokens[i])):
            if prefix == "command" and tokens[i] in ("-v", "-V"):
                return tokens
            i += 2 if tokens[i] in valued else 1
        if i >= len(tokens):
            return tokens
        tokens = tokens[i:]
    return tokens


def _command(segment: str) -> tuple[list[str], str]:
    """（参数, 归一化的命令名）：去掉 PowerShell 的 & / . 调用前缀和 sudo / env 等前缀，
    命令名去路径和 .exe（/bin/rm、rm.exe 都是 rm）。"""
    tokens = _tokens(segment)
    if tokens and tokens[0] in ("&", "."):
        tokens = tokens[1:]
    tokens = _unwrap(tokens)
    return tokens, (_program(tokens[0]) if tokens else "")


def _redirects(segment: str) -> list[tuple[str, str]]:
    """（文件描述符, 目标）；目标去掉引号。"""
    return [(fd, target.strip("'\"")) for fd, target in _REDIRECT.findall(segment)]


def _expand(token: str) -> str:
    return os.path.expandvars(re.sub(r"\$env:(\w+)", lambda m: os.environ.get(m[1], m[0]), token))


def _read_small(path: str, base: str | None) -> str:
    full = Path(_expand(path))
    if not full.is_absolute():
        full = Path(base or ".") / full
    try:
        return full.read_text(encoding="utf-8", errors="replace") if full.stat().st_size <= _SCRIPT_MAX_BYTES else ""
    except OSError:
        return ""


def _code_targets(code: str) -> list[str]:
    """脚本或内联代码里写了文件时，把其中像路径的字符串都当作目标；宁可多拦一次，也别漏掉。"""
    return _PATH_LITERAL.findall(code) if _CODE_WRITES.search(code) else []


def _script_of(tokens: list[str]) -> str | None:
    """解释器（python、node 等）后的第一个参数：脚本路径或内联代码；`uv run x.py` 也算。不是在跑代码时为 None。"""
    names = [_program(t) for t in tokens]
    start = next((i + 1 for i, n in enumerate(names) if n in _INTERPRETERS), None)
    if start is not None:
        return next((t for t in tokens[start:] if not t.startswith("-")), "")
    if names[:2] == ["uv", "run"]:
        script = next((t for t in tokens[2:] if not t.startswith("-")), "")
        return script if script.lower().endswith(_SCRIPT_SUFFIXES) else None
    return None


def _git_targets(rest: list[str], base: str | None) -> list[str]:
    if not rest:
        return []
    sub, args = rest[0].lower(), rest[1:]
    if sub in ("checkout", "restore") and "--" in args:
        return args[args.index("--") + 1:]
    if sub == "checkout":
        # 不带 -- 时，参数可能是分支也可能是文件；工作区里存在的才当作要还原的文件
        return [t for t in args if not t.startswith("-") and (Path(base or ".") / _expand(t)).is_file()]
    if sub in ("restore", "rm", "mv"):
        return [t for t in args if not t.startswith("-")]
    if sub in ("apply", "am"):
        return [p for t in args if not t.startswith("-") for p in _PATCH_FILE.findall(_read_small(t, base))]
    return []


def _copy_targets(head: str, rest: list[str]) -> list[str]:
    named = {t.lower(): rest[i + 1] for i, t in enumerate(rest[:-1]) if t.lower() in _PATH_PARAMS}
    positional = [t for t in rest if not t.startswith("-") and t not in named.values()]
    if head in _MOVE:
        return [*named.values(), *positional]
    lowered = [t.lower() for t in rest]
    for flag in ("-t", "--target-directory"):
        if flag in lowered[:-1]:
            return [rest[lowered.index(flag) + 1]]
    destination = named.get("-destination") or (positional[-1] if len(positional) > 1 else None)
    return [destination] if destination else []


def _nested(tokens: list[str]) -> tuple[str | None, str | None]:
    """命令本身又起了一层终端时，返回（内联命令, 脚本路径）；不是时两者都为 None。"""
    head, rest = tokens[0], tokens[1:]
    if head.lower().endswith(_SHELL_SCRIPT_SUFFIXES):
        return None, head
    program, lowered = _program(head), [t.lower() for t in rest]
    if program in _POWERSHELLS:
        for i, flag in enumerate(lowered):
            if flag in ("-command", "-c"):
                return " ".join(rest[i + 1:]), None
            if flag in ("-file", "-f"):
                return None, (rest[i + 1] if i + 1 < len(rest) else None)
        positional = [t for i, t in enumerate(rest)
                      if not t.startswith("-") and (i == 0 or lowered[i - 1] not in _PS_VALUE_FLAGS)]
        return (" ".join(positional) or None), None
    if program == "cmd":
        at = next((i for i, flag in enumerate(lowered) if flag in ("/c", "/k")), None)
        return (" ".join(rest[at + 1:]) if at is not None else None), None
    if program in _POSIX_SHELLS:
        at = next((i for i, flag in enumerate(rest) if _POSIX_INLINE_FLAG.fullmatch(flag)), None)
        if at is not None:
            return (rest[at + 1] if at + 1 < len(rest) else None), None
        return None, next((t for t in rest if t.lower().endswith(_SHELL_SCRIPT_SUFFIXES)), None)
    return None, None


def _in_place(head: str, rest: list[str]) -> bool:
    """sed -i、perl -pi -e 这类就地改文件的写法。"""
    if head == "sed":
        return any(t.startswith("-i") for t in rest)
    return head == "perl" and any(t.startswith("-") and not t.startswith("--") and "i" in t[1:] for t in rest)


def _in_place_targets(head: str, rest: list[str]) -> list[str]:
    """就地改写的全部文件：-e/-f 给出脚本时位置参数都是文件，否则第一个位置参数是脚本。"""
    files: list[str] = []
    script_given = skip = False
    for token in rest:
        if skip:
            skip = False
            continue
        if token in ("-e", "--expression", "-f", "--file") or (
                head == "perl" and token.startswith("-") and not token.startswith("--") and "e" in token[1:]):
            script_given = skip = True
            continue
        if not token.startswith("-"):
            files.append(token)
    return files if script_given else files[1:]


# PowerShell 写文件命令里带值的参数；其余以 - 开头的是开关（-Recurse、-Force），不会吞掉后面的路径
_PS_VALUE_PARAMS = {"-value", "-encoding", "-itemtype", "-type", "-name", "-filter", "-include", "-exclude",
                    "-inputobject", "-stream", "-width", "-target", "-credential"}
# 第二个位置参数是写入内容而不是路径
_PS_CONTENT_WRITERS = {"set-content", "sc", "add-content", "ac", "out-file"}


def _ps_targets(head: str, rest: list[str]) -> list[str]:
    paths: list[str] = []
    positional: list[str] = []
    skip = False
    for i, token in enumerate(rest):
        if skip:
            skip = False
            continue
        lowered = token.lower()
        if lowered in ("-path", "-filepath", "-literalpath") and i + 1 < len(rest):
            paths.append(rest[i + 1])
            skip = True
        elif lowered in _PS_VALUE_PARAMS:
            skip = True
        elif not token.startswith("-"):
            positional.append(token)
    if not paths:
        paths = positional[:1] if head in _PS_CONTENT_WRITERS else positional
    return [p for raw in paths for p in raw.split(",") if p.strip()]


def scan(command: str, base: str | None, depth: int = 0) -> tuple[list[str], bool]:
    """（终端命令会写到的文件, 是否在跑脚本或内联代码）。命令里先 cd 再写相对路径时，返回的路径带上 cd 的目录。"""
    targets: list[str] = _DOTNET_WRITE.findall(command or "")
    runs_code = False
    cwd = ""  # 相对 base 的当前目录，随命令里的 cd / Set-Location 变化
    for segment in _segments(command):
        found: list[str] = [target for _, target in _redirects(segment)]
        tokens, head = _command(segment)
        if not tokens:
            targets += _under(cwd, found)
            continue
        rest = tokens[1:]
        here = str(Path(base or ".") / cwd) if cwd else base
        if head in _CD:
            args = [t for t in rest if not t.startswith("-")]
            if args:
                cwd = os.path.normpath(os.path.join(cwd, _expand(args[0])))
            continue
        script = _script_of(tokens)
        if script is not None:
            runs_code = True
            if script.lower().endswith(_SCRIPT_SUFFIXES):
                found += _code_targets(_read_small(script, here))
        inline, shell_script = _nested(tokens)
        if inline is not None or shell_script is not None:
            runs_code = True
            if depth < _MAX_NESTING:
                inner = inline if inline is not None else _read_small(shell_script, here)
                found += scan(inner, here, depth + 1)[0]
            targets += _under(cwd, found)
            continue
        found += _segment_targets(head, rest, here)
        targets += _under(cwd, found)
    # 内联代码（python -c、heredoc、管道送入的脚本）会被分号拆散，按整条命令找
    if runs_code:
        targets += _code_targets(command)
    seen: list[str] = []
    for target in targets:
        if target.lower() not in _NULL_TARGETS and not target.startswith("-") and target not in seen:
            seen.append(target)
    return seen, runs_code


def _under(cwd: str, paths: list[str]) -> list[str]:
    if not cwd:
        return paths
    return [p if p.lower() in _NULL_TARGETS or os.path.isabs(_expand(p)) else os.path.join(cwd, p) for p in paths]


def _segment_targets(head: str, rest: list[str], base: str | None) -> list[str]:
    """单条命令按命令名认出的写入目标。"""
    if _in_place(head, rest):
        return _in_place_targets(head, rest)
    if head in _PS_WRITERS:
        return _ps_targets(head, rest)
    if head in _TEE or head in _RM:
        return [p for t in rest if not t.startswith("-") for p in t.split(",") if p.strip()]
    if head == "git":
        return _git_targets(rest, base)
    if head in _COPY or head in _MOVE:
        return _copy_targets(head, rest)
    return []


def may_change_unseen(command: str) -> bool:
    """命令里有不认识的程序（构建、格式化、git stash/reset 等），可能改了解析不出来的文件，需要执行前后比对。
    只有只读命令和已按名字认出目标的写命令时为 False。"""
    for segment in _segments(command):
        tokens, _ = _command(segment)
        if not tokens:
            continue
        names = [_program(t) for t in tokens]
        if names[0] in _LAUNCHERS and "pmem" in names:
            tokens = tokens[names.index("pmem"):]
        head, rest = _program(tokens[0]), tokens[1:]
        sub = rest[0].lower() if rest else ""
        if head == "find" and any(t.lower() in ("-delete", "-exec", "-execdir") for t in rest):
            return True
        if head in _READ_ONLY or (head == "pmem" and sub in _PMEM_READ_ONLY):
            continue
        if head == "git" and (sub in _GIT_READ_ONLY or (sub in ("checkout", "restore") and "--" in rest)):
            continue
        if head == "svn" and sub in _SVN_READ_ONLY:
            continue
        # 写命令认出了目标才算看清；目标从管道传入（ls | Remove-Item）时照样要比对
        if (head in _TEE | _RM | _COPY | _MOVE | _PS_WRITERS or _in_place(head, rest)) \
                and _segment_targets(head, rest, None):
            continue
        return True
    return False


def shell_write_targets(command: str, base: str | None = None) -> list[str]:
    """终端命令会写到的文件。base 是命令的工作目录，用来读命令里引用的脚本和补丁。"""
    return scan(command, base)[0]


def _output_discarded(segment: str, later_stages: list[str]) -> bool:
    """命令的输出被重定向或被管道吞掉（> $null、| Out-Null、> a.txt），Agent 看不到结果。"""
    # 只看标准输出：2>$null、2>&1 不影响 Agent 看到结果
    if any(fd in _STDOUT_FDS for fd, _ in _redirects(segment)):
        return True
    return any(_command(stage)[1] in _DISCARD_STAGES for stage in later_stages)


# 以这些程序开头时，pmem 可以出现在它们的参数之后（如 uv run --extra embed pmem record）
_LAUNCHERS = {"uv", "uvx", "pipx", "python", "python3", "py"}


def cli_args(command: str, subcommand: str) -> list[dict]:
    """终端里的 `pmem search/record ...` 与对应 MCP 工具等价，按出现顺序返回每一处的 module/path 参数。
    search、graph 的输出被丢弃时（> $null、| Out-Null），Agent 并没有看到记忆，不算；写在 || 后面的不一定执行，也不算。"""
    found: list[dict] = []
    for statement, op in _statements_with_ops(command):
        if op == "||" and subcommand in ("search", "graph"):
            continue
        stages = _stages(statement)
        for n, segment in enumerate(stages):
            tokens = _command(segment)[0]
            names = [_program(t) for t in tokens]
            start = next(
                (i + 2 for i in range(len(tokens) - 1)
                 if names[i] == "pmem" and tokens[i + 1] == subcommand and (i == 0 or names[0] in _LAUNCHERS)),
                None,
            )
            if start is None:
                continue
            if subcommand in ("search", "graph") and _output_discarded(segment, stages[n + 1:]):
                continue
            rest = tokens[start:]
            args: dict = {}
            # 取第一个：换行被转码吞掉时，下一行命令的 --module 会接在同一段里
            for i, token in enumerate(rest):
                name, eq, value = token.partition("=")
                if name in ("--module", "--path"):
                    if eq:
                        args.setdefault(name[2:], value)
                    elif i + 1 < len(rest):
                        args.setdefault(name[2:], rest[i + 1])
            found.append(args)
    return found
