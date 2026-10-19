"""读写 modules.yaml：文件开头的注释块原样保留，正文按 YAML 重写（中间的注释会丢失，调用方应先提示）。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

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
        return cls(path, header, body, yaml.safe_load(body) or {})

    def lost_comments(self) -> int:
        return body_comments(self.body)

    def write(self, data: dict) -> None:
        self.path.write_text(dump_modules(self.header, data), encoding="utf-8", newline="\n")


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
    return header + text
