"""读写 modules.yaml：文件开头的注释块原样保留，正文按 YAML 重写（中间的注释会丢失，调用方应先提示）。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from pmem.core.fileio import write_atomic
from pmem.core.registry import RegistryError

_QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"|\'[^\']*\'')


@dataclass
class ModulesFile:
    path: Path
    header: str
    body: str
    data: dict

    @classmethod
    def read(cls, path: Path) -> ModulesFile:
        # Windows 上 autocrlf 检出的是 CRLF；统一成 LF，免得保留的文件头和重写的正文换行混杂
        text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n") if path.exists() else ""
        header, body = split_header(text)
        try:
            data = yaml.safe_load(body) or {}
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            # 行号按整个文件算：正文前面还有保留的注释块
            where = f"第 {mark.line + 1 + header.count(chr(10))} 行" if mark is not None else ""
            raise RegistryError(f"{path.name} {where}格式错误：{getattr(exc, 'problem', None) or exc}") from exc
        if not isinstance(data, dict):
            raise RegistryError(f"{path.name} 的顶层应是键值对（categories、modules 等）")
        return cls(path, header, body, data)

    def lost_comments(self) -> int:
        return body_comments(self.body)

    def write(self, data: dict) -> None:
        write_atomic(self.path, dump_modules(self.header, data))


def split_header(text: str) -> tuple[str, str]:
    """文件开头的注释块原样保留；之后的注释在重写时会丢失，所以单独返回正文统计。"""
    lines = text.splitlines(keepends=True)
    cut = 0
    while cut < len(lines) and (not lines[cut].strip() or lines[cut].lstrip().startswith("#")):
        cut += 1
    return "".join(lines[:cut]), "".join(lines[cut:])


def body_comments(body: str) -> int:
    # 引号里的 " #"（如 "Assets/C# Scripts/**"）不是注释
    return sum(1 for line in body.splitlines()
               if line.lstrip().startswith("#") or " #" in _QUOTED.sub("", line))


def dump_modules(header: str, data: dict) -> str:
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=None, width=1000)
    # 文件只有注释、末行没换行时，正文会接在注释行后面整个变成注释
    if header and not header.endswith("\n"):
        header += "\n"
    return header + text
