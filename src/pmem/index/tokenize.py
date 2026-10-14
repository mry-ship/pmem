from __future__ import annotations

import re

_RUN = re.compile(r"[A-Za-z0-9_]+|[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
_PART = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")


def tokenize(text: str) -> list[str]:
    """关键词切分：中文按相邻两字切，英文按整词 + 驼峰/下划线拆分，统一小写。"""
    tokens: list[str] = []
    for match in _RUN.finditer(text or ""):
        run = match.group()
        if run[0].isascii():
            tokens.append(run.lower())
            parts = [p.lower() for chunk in run.split("_") for p in _PART.findall(chunk)]
            if len(parts) > 1:
                tokens.extend(parts)
        elif len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens
