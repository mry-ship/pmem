"""把终端命令拆开：剥离 heredoc、按 ; && || | 和换行拆语句与管道、分词、取命令名、去前缀。"""
from __future__ import annotations

import os
import re
from pathlib import Path

from pmem.hooks.shell.constants import (
    _HERE_STRING_OPEN,
    _HEREDOC_OPEN,
    _MAX_HEREDOCS,
    _PREFIXES,
    _REDIRECT,
    _SCRIPT_MAX_BYTES,
)


def _strip_heredocs(command: str) -> str:
    command = _cut_bodies(command or "", _HERE_STRING_OPEN, lambda m: re.compile(r"\r?\n" + m[1] + "@"),
                          lambda m: "''")
    return _cut_bodies(command, _HEREDOC_OPEN,
                       lambda m: re.compile(r"(?m)^[ \t]*" + re.escape(m[2]) + r"[ \t]*\r?$"),
                       lambda m: f"<<{m[2]}{m[3]}")


def _cut_bodies(command: str, opener: re.Pattern, closer, replacement) -> str:
    """把开头（opener）到结束符（closer）之间的正文换成 replacement；结束符必须在正文之后另起一行（正文可为空）。
    找不到结束符的保持原样；最多处理 _MAX_HEREDOCS 处，代码里的 1<<20 这类移位不会拖慢解析。"""
    out: list[str] = []
    pos = 0
    for count, match in enumerate(opener.finditer(command)):
        if count >= _MAX_HEREDOCS:
            break
        if match.start() < pos:
            continue
        body_start = match.end()
        end = closer(match).search(command, body_start - 1 if command[body_start - 1:body_start] == "\n" else body_start)
        if end is None:
            continue
        out.append(command[pos:match.start()])
        out.append(replacement(match))
        pos = end.end()
    out.append(command[pos:])
    return "".join(out)


def _statements(command: str) -> list[str]:
    """按换行和 ; && || 拆成语句（管道还连在一起）；行尾的 ` 或 \\ 是续行，先接回去。"""
    return [statement for statement, _ in _statements_with_ops(command)]


def _statements_with_ops(command: str) -> list[tuple[str, str]]:
    """语句及其前面的连接符（第一条为空串）；`a || b` 里的 b 只在 a 失败时才执行。
    单个 & 也拆（cmd 的顺序执行、bash 的后台执行，两侧不必有空格）；2>&1、&>、|& 里的不算。
    PowerShell 的 `& 程序` 拆出一个空语句，不影响识别。"""
    joined = re.sub(r"[`\\][ \t]*\r?\n", " ", _strip_heredocs(command))
    parts = re.split(r"\s*(\|\||&&|[;\r\n]|(?<![&>|<])&(?![&>]))\s*", joined)
    return [(parts[i], parts[i - 1] if i else "") for i in range(0, len(parts), 2)]


def _stages(statement: str) -> list[str]:
    # >| 是强制覆盖的重定向，不是管道
    return re.split(r"\s*(?<!>)\|\s*", statement)


def _segments(command: str) -> list[str]:
    """按换行和 ; && || | 拆成单条命令。"""
    return [stage for statement in _statements(command) for stage in _stages(statement)]


def _tokens(segment: str) -> list[str]:
    # 尾随的逗号、分号不属于路径（如 "a/b.py", 这样出现在列表里的写法）；
    # PowerShell 的数组参数 `a, b` 并成 `a,b` 一个参数，各命令再按逗号拆
    tokens: list[str] = []
    joining = False
    for raw in re.findall(r"'[^']*'|\"[^\"]*\"|\S+", segment):
        token = raw.strip("'\"").rstrip(",;").strip("'\"")
        if joining and tokens and token and not token.startswith("-"):
            tokens[-1] += "," + token
        elif token or not raw.startswith(","):
            tokens.append(token)
        joining = raw.endswith(",")
    return tokens


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


def _unbalanced_quotes(segment: str) -> bool:
    return segment.count('"') % 2 == 1 or segment.count("'") % 2 == 1
