from __future__ import annotations

import re


def _mentions(text: str, term: str) -> bool:
    if term.isascii():
        return re.search(rf"(?<![A-Za-z0-9_]){re.escape(term.lower())}(?![A-Za-z0-9_])", text) is not None
    return term.lower() in text


def expansions(query: str, groups: list[list[str]]) -> list[str]:
    """查询里出现了某个同义词组的成员时，返回同组其余叫法（查询里已有的不重复）。"""
    text = (query or "").lower()
    extra: list[str] = []
    for group in groups:
        if any(_mentions(text, term) for term in group):
            extra += [t for t in group if not _mentions(text, t) and t not in extra]
    return extra
