"""从每条命令里认出会写到的文件，以及对外接口：scan、shell_write_targets、may_change_unseen、
searched_before_writes、cli_args。认得出的命令事前拦截；认不出的交给执行前后快照比对。"""
from __future__ import annotations

import os
from pathlib import Path

from pmem.hooks.shell.constants import (
    _CD,
    _CODE_WRITES,
    _COPY,
    _DISCARD_STAGES,
    _DOTNET_WRITE,
    _FIND_WRITES,
    _GIT_READ_ONLY,
    _MAX_NESTING,
    _MAX_ORDERED_STATEMENTS,
    _MOVE,
    _NULL_TARGETS,
    _PATCH_FILE,
    _PATH_LITERAL,
    _PATH_PARAMS,
    _PIPED_ITEMS,
    _PMEM_CLI,
    _PMEM_READ_ONLY,
    _POPD,
    _POSIX_INLINE_FLAG,
    _POSIX_SHELLS,
    _POWERSHELLS,
    _PS_CONTENT_WRITERS,
    _PS_VALUE_FLAGS,
    _PS_VALUE_PARAMS,
    _PS_WRITERS,
    _READ_ONLY,
    _RENAME,
    _RM,
    _SCRIPT_SUFFIXES,
    _SEQUENTIAL_OPS,
    _SHELL_SCRIPT_SUFFIXES,
    _STDOUT_FDS,
    _SVN_READ_ONLY,
    _TEE,
    MAX_PARSED_COMMAND,
    VARIABLE_PATH,
    WILDCARD_PATH,
    is_interpreter,
    is_launcher,
)
from pmem.hooks.shell.lexer import (
    _command,
    _expand,
    _program,
    _read_small,
    _redirects,
    _segments,
    _stages,
    _statements,
    _statements_with_ops,
    _unbalanced_quotes,
)


def _code_targets(code: str, base: str | None) -> list[str]:
    """脚本或内联代码里写了文件时，把其中像路径的字符串都当作目标；宁可多拦一次，也别漏掉。
    指向工作目录本身或它的上级的字面量（ROOT = "C:/repo"）只是拼路径用的，当成目标会要求查遍所有模块。"""
    if not _CODE_WRITES.search(code):
        return []
    here = Path(base or ".").resolve()
    return [p for p in _PATH_LITERAL.findall(code) if not _is_ancestor(p, here)]


def _is_ancestor(path: str, here: Path) -> bool:
    try:
        full = Path(_expand(path))
        full = (full if full.is_absolute() else here / full).resolve()
    except (OSError, ValueError):
        return False
    return full == here or full in here.parents


def _script_of(tokens: list[str]) -> str | None:
    """解释器（python、node 等）后的第一个参数：脚本路径或内联代码；`uv run x.py` 也算。不是在跑代码时为 None。"""
    names = [_program(t) for t in tokens]
    start = next((i + 1 for i, n in enumerate(names) if is_interpreter(n)), None)
    if start is not None:
        return next((t for t in tokens[start:] if not t.startswith("-")), "")
    if names[:2] == ["uv", "run"]:
        script = next((t for t in tokens[2:] if not t.startswith("-")), "")
        return script if script.lower().endswith(_SCRIPT_SUFFIXES) else None
    return None


def _git_global(rest: list[str]) -> tuple[str, list[str]]:
    """去掉子命令前的全局选项：（-C、--work-tree 指定的目录, 子命令及其参数）。"""
    directory = ""
    i = 0
    while i < len(rest) and rest[i].startswith("-"):
        option = rest[i]
        if option.startswith("--work-tree="):
            directory = os.path.join(directory, option.split("=", 1)[1])
            i += 1
        elif option in ("-C", "--work-tree") and i + 1 < len(rest):
            directory = os.path.join(directory, rest[i + 1])
            i += 2
        elif option in ("-c", "--git-dir", "--namespace") and i + 1 < len(rest):
            i += 2
        else:
            i += 1
    return directory, rest[i:]


def _git_targets(rest: list[str], base: str | None) -> list[str]:
    directory, rest = _git_global(rest)
    if not rest:
        return []
    here = os.path.join(base or ".", directory)
    sub, args = rest[0].lower(), rest[1:]
    if sub in ("checkout", "restore") and "--" in args:
        found = args[args.index("--") + 1:]
    elif sub == "checkout":
        # 不带 -- 时，参数可能是分支也可能是文件或目录；工作区里存在的才当作要还原的路径
        found = [t for t in args if not t.startswith("-") and (Path(here) / _expand(t)).exists()]
    elif sub in ("restore", "rm", "mv"):
        found = [t for t in args if not t.startswith("-")]
    elif sub in ("apply", "am"):
        # 补丁里的路径相对仓库根，不随 -C 变
        return [p for t in args if not t.startswith("-") for p in _PATCH_FILE.findall(_read_small(t, here))]
    else:
        found = []
    return _under(directory, found)


def _copy_targets(head: str, rest: list[str], base: str | None = None) -> list[str]:
    """复制、移动、改名的写入目标。移动和改名时源文件也算（被移走）；目的地是已有目录（或以 / 结尾）时
    取“目录/源文件名”，免得把写进 src/ 的一个文件当成改了整个 src。"""
    named = _named_params(rest, (*_PATH_PARAMS, "-newname"))
    positional = _positional(rest)
    target_dir = None
    for i, token in enumerate(rest[:-1]):
        # cp 的 -t 是目标目录，-T 是“目的地不当目录”的开关，大小写不能混
        if token == "-t" or token.lower() == "--target-directory":
            target_dir = rest[i + 1]
    target_dir = next((t.split("=", 1)[1] for t in rest if t.lower().startswith("--target-directory=")), target_dir)
    sources = [v for k, v in named.items() if k in ("-path", "-literalpath")]
    if head in _RENAME:
        sources = sources or positional[:1]
        new_name = named.get("-newname") or (positional[1] if len(positional) > 1 and not named else None)
        renamed = [os.path.join(os.path.dirname(s), new_name) for s in sources[:1]] if new_name else []
        return [*sources, *renamed]
    if target_dir is not None:
        destination, sources = target_dir, sources + positional
    elif "-destination" in named:
        destination, sources = named["-destination"], sources + positional
    elif len(sources) + len(positional) > 1:
        destination, sources = positional[-1], sources + positional[:-1]
    else:
        destination, sources = None, sources + positional
    landed = _into_directory(destination, sources, base) if destination else []
    return [*sources, *landed] if head in _MOVE else landed


def _positional(rest: list[str]) -> list[str]:
    """位置参数：跳过 -Path a 这类具名参数和 -ErrorAction SilentlyContinue 这类开关的值。"""
    found: list[str] = []
    skip = False
    for token in rest:
        if skip:
            skip = False
            continue
        lowered = token.lower()
        if token == "-t" or lowered in _PS_VALUE_PARAMS or lowered in _PATH_PARAMS or lowered in (
                "--target-directory", "-newname"):
            skip = True
        elif not token.startswith("-"):
            found.append(token)
    return found


def _into_directory(destination: str, sources: list[str], base: str | None) -> list[str]:
    is_dir = destination.endswith(("/", "\\")) or (Path(base or ".") / _expand(destination)).is_dir()
    if not is_dir or not sources or any(WILDCARD_PATH.search(s) or VARIABLE_PATH.search(s) for s in sources):
        return [destination]
    return [os.path.join(destination, os.path.basename(s.rstrip("/\\"))) for s in sources]


def _named_params(rest: list[str], names: tuple[str, ...]) -> dict[str, str]:
    """PowerShell 的具名参数，`-Path a` 和 `-Path:a` 两种写法都认。"""
    found: dict[str, str] = {}
    for i, token in enumerate(rest):
        name, colon, value = token.partition(":")
        if name.lower() not in names:
            continue
        if colon and value:
            found[name.lower()] = value
        elif not colon and i + 1 < len(rest):
            found[name.lower()] = rest[i + 1]
    return found


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
            # 引号被 ; && 拆开时内联命令散成多个参数，全部接回去（bash -c 之后的 $0 $1 参数一并带上也无害）
            return (" ".join(rest[at + 1:]) if at + 1 < len(rest) else None), None
        return None, next((t for t in rest if t.lower().endswith(_SHELL_SCRIPT_SUFFIXES)), None)
    return None, None


def _in_place(head: str, rest: list[str]) -> bool:
    """sed -i、perl -pi -e 这类就地改文件的写法。"""
    if head == "sed":
        return any(t.startswith(("-i", "--in-place")) for t in rest)
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
        # 脚本和参数写在一起：--expression=…、--file=…、sed 的 -es/a/b/
        if token.startswith(("--expression=", "--file=")) or (head == "sed" and token[:2] in ("-e", "-f")
                                                              and len(token) > 2):
            script_given = True
            continue
        if not token.startswith("-"):
            files.append(token)
    return files if script_given else files[1:]


# PowerShell 写文件命令里带值的参数；其余以 - 开头的是开关（-Recurse、-Force），不会吞掉后面的路径
# 第二个位置参数是写入内容而不是路径（Tee-Object 的第一个位置参数是文件，-Variable 时不写文件）


def _ps_targets(head: str, rest: list[str]) -> list[str]:
    paths: list[str] = []
    positional: list[str] = []
    skip = False
    for i, token in enumerate(rest):
        if skip:
            skip = False
            continue
        lowered = token.lower()
        name, colon, _ = lowered.partition(":")
        if colon and name in ("-path", "-filepath", "-literalpath"):
            paths.append(token[len(name) + 1:])
        elif colon and name.startswith("-"):
            continue
        elif lowered in ("-path", "-filepath", "-literalpath") and i + 1 < len(rest):
            paths.append(rest[i + 1])
            skip = True
        elif lowered in _PS_VALUE_PARAMS:
            skip = True
        elif not token.startswith("-"):
            positional.append(token)
    if not paths:
        paths = positional[:1] if head in _PS_CONTENT_WRITERS else positional
    found = [p for raw in paths for p in raw.split(",") if p.strip()]
    name = _named_params(rest, ("-name",)).get("-name")
    if head in ("new-item", "ni") and name:
        # New-Item -Path 目录 -Name 文件名：写的是目录下的这个文件；没给 -Path 时就在当前目录
        return [os.path.join(p, name) for p in found] or [name]
    return found


def scan(command: str, base: str | None, depth: int = 0) -> tuple[list[str], bool]:
    """（终端命令会写到的文件, 是否在跑脚本或内联代码）。命令里先 cd 再写相对路径时，返回的路径带上 cd 的目录。"""
    targets, runs_code, _ = _scan(command, base, depth)
    seen: list[str] = []
    for target in targets:
        if target.lower() not in _NULL_TARGETS and not target.startswith("-") and target not in seen:
            seen.append(target)
    return seen, runs_code


def _scan(command: str, base: str | None, depth: int) -> tuple[list[str], bool, str]:
    """（写入目标, 是否在跑代码, 命令结束时相对 base 的当前目录）。"""
    if len(command or "") > MAX_PARSED_COMMAND:
        return [], True, ""
    targets: list[str] = _DOTNET_WRITE.findall(command or "")
    runs_code = False
    cwd = ""  # 相对 base 的当前目录，随命令里的 cd / Set-Location / pushd / popd 变化
    stack: list[str] = []
    outer: str | None = None  # 引号被拆开的 bash -c "cd x && …" 结束后要回到的外层目录
    for segment in _segments(command):
        if outer is not None and _unbalanced_quotes(segment):
            # 这一段带着内联命令的右引号：它本身还在内层目录里执行，之后回到外层
            targets += _under(cwd, _segment_writes(segment, base, cwd))
            cwd, outer = outer, None
            continue
        found: list[str] = [target for _, target in _redirects(segment)]
        tokens, head = _command(segment)
        if not tokens:
            targets += _under(cwd, found)
            continue
        rest = tokens[1:]
        here = str(Path(base or ".") / cwd) if cwd else base
        if head in _CD:
            # cmd 的 cd /d 是切换盘符的开关，不是目录
            args = [t for t in rest if not t.startswith("-") and t.lower() != "/d"]
            if args and args[0].startswith("~"):
                # 主目录不在项目里，之后的相对路径解析不出；跑代码一样交给执行后的快照比对
                runs_code = True
                cwd = os.path.join("..", "~")
            elif args:
                if head in ("pushd", "push-location"):
                    stack.append(cwd)
                cwd = os.path.normpath(os.path.join(cwd, _expand(args[0])))
            elif "-" in rest:
                runs_code = True
            continue
        if head in _POPD:
            cwd = stack.pop() if stack else cwd
            continue
        script = _script_of(tokens)
        if script is not None:
            runs_code = True
            if script.lower().endswith(_SCRIPT_SUFFIXES):
                found += _code_targets(_read_small(script, here), here)
        inline, shell_script = _nested(tokens)
        if inline is not None or shell_script is not None:
            runs_code = True
            if depth < _MAX_NESTING:
                inner = inline if inline is not None else _read_small(shell_script, here)
                inner_targets, _, inner_cwd = _scan(inner, here, depth + 1)
                found += inner_targets
                # bash -c "cd src && rm x" 按 && 拆语句时引号被拆开，后半段落在外层，内层的 cd 要带出来，
                # 到右引号所在的那一段为止
                if inline is not None and inner_cwd and _unbalanced_quotes(segment):
                    targets += _under(cwd, found)
                    outer = cwd
                    cwd = os.path.normpath(os.path.join(cwd, inner_cwd))
                    continue
            targets += _under(cwd, found)
            continue
        found += _segment_targets(head, rest, here)
        targets += _under(cwd, found)
    # 内联代码（python -c、heredoc、管道送入的脚本）会被分号拆散，按整条命令找
    if runs_code:
        targets += _code_targets(command, base)
    return targets, runs_code, cwd


def _segment_writes(segment: str, base: str | None, cwd: str) -> list[str]:
    found = [target for _, target in _redirects(segment)]
    tokens, head = _command(segment)
    if tokens:
        here = str(Path(base or ".") / cwd) if cwd else base
        found += _segment_targets(head, tokens[1:], here)
    return found


# 检索之后靠这些连接符接着执行的语句才算“查过再写”；|| 只在检索失败时执行，& 是并行


def searched_before_writes(command: str, base: str | None = None) -> dict[str, list[dict]]:
    """命令里每个写入目标之前、按顺序执行的 pmem search/graph 调用：{目标: [检索参数, ...]}。
    先写后查、隔着 || 或 & 的检索都不算；语句太多时一律不算（照常检查）。"""
    pairs = _statements_with_ops(command)
    if len(pairs) > _MAX_ORDERED_STATEMENTS:
        return {}
    result: dict[str, list[dict]] = {}
    searches: list[dict] = []
    for i, (statement, op) in enumerate(pairs):
        if i and op not in _SEQUENTIAL_OPS:
            searches = []
        for target in scan("\n".join(s for s, _ in pairs[:i + 1]), base)[0]:
            result.setdefault(target, list(searches))
        searches = searches + cli_args(statement, "search") + cli_args(statement, "graph")
    return result


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
    if head == "tee-object":
        return _ps_targets(head, rest)
    if head in _TEE or head in _RM:
        return [p for t in _positional(rest) for p in t.split(",") if p.strip()]
    if head == "git":
        return _git_targets(rest, base) + _output_option(rest)
    if head in _COPY or head in _MOVE:
        return _copy_targets(head, rest, base)
    if head == "sort":
        return _output_option(rest, short="-o")
    return []


def _output_option(rest: list[str], short: str | None = None) -> list[str]:
    """--output=文件、--output 文件（sort 还有 -o 文件）：只读命令也能借它写文件。"""
    found = [t.split("=", 1)[1] for t in rest if t.startswith("--output=")]
    found += [rest[i + 1] for i, t in enumerate(rest[:-1]) if t == "--output" or (short and t == short)]
    found += [t[2:] for t in rest if short and t.startswith(short) and len(t) > 2]
    return found


def may_change_unseen(command: str) -> bool:
    """命令里有不认识的程序（构建、格式化、git stash/reset 等），可能改了解析不出来的文件，需要执行前后比对。
    只有只读命令和已按名字认出目标的写命令时为 False。"""
    if len(command or "") > MAX_PARSED_COMMAND:
        return True
    for statement in _statements(command):
        for n, segment in enumerate(_stages(statement)):
            if _changes_unseen(segment, piped=n > 0):
                return True
    return False


# 只读命令里能写文件或执行任意程序的选项


def _changes_unseen(segment: str, piped: bool) -> bool:
    tokens, _ = _command(segment)
    if not tokens or not tokens[0]:
        return False
    names = [_program(t) for t in tokens]
    if is_launcher(names[0]) and any(n in _PMEM_CLI for n in names):
        tokens = tokens[next(i for i, n in enumerate(names) if n in _PMEM_CLI):]
    head, rest = _program(tokens[0]), tokens[1:]
    if head == "git":
        rest = _git_global(rest)[1]
    sub = rest[0].lower() if rest else ""
    lowered = [t.lower() for t in rest]
    if head == "find" and any(t in _FIND_WRITES for t in lowered):
        return True
    if head == "rg" and any(t == "--pre" or t.startswith("--pre=") for t in lowered):
        return True
    if head == "tee-object" and "-variable" in lowered and not _segment_targets(head, rest, None):
        return False
    if head in ("sort", "git") and _output_option(rest, short="-o" if head == "sort" else None):
        # 目标已由 scan 认出，但只读白名单会跳过它；按写命令处理
        return False
    if head in _READ_ONLY or (head in _PMEM_CLI and sub in _PMEM_READ_ONLY):
        return False
    if head == "git" and (sub in _GIT_READ_ONLY or (sub in ("checkout", "restore") and "--" in rest)):
        return False
    if head == "svn" and sub in _SVN_READ_ONLY:
        return False
    # 写命令认出了目标才算看清；删除、复制、移动在管道下游时，要处理的文件来自上游（ls | Remove-Item），
    # 参数里的不全，照样比对。tee、Set-Content 从管道接的是内容，目标仍在参数里
    recognized = (head in _TEE | _RM | _COPY | _MOVE | _PS_WRITERS or _in_place(head, rest)) \
        and bool(_segment_targets(head, rest, None))
    return not recognized or (piped and head in _PIPED_ITEMS)


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
                 if names[i] in _PMEM_CLI and tokens[i + 1] == subcommand and (i == 0 or is_launcher(names[0]))),
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
