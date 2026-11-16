"""判断检索返回的记忆是否被 Agent 采用：比对记忆正文与对话中 Agent 回复的字面重合。

只看字面（中文 4 字片段 + 标识符）：bge-small-zh 的语义相似度在长对话里取最大值后，
无关对话也能到 0.8，区分不开；字面重合在无关对话里不超过 0.11。结果是保守下限，
Agent 完全换说法复述的情况不计入。

长文正文指纹很多，Agent 只复述结论句时覆盖率会被稀释。若提供足够长的可复述标题
（summary/title），取「正文得分」与「标题得分」的较大值；阈值仍为 0.15，不降严。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_CJK_RUN = re.compile(r"[\u4e00-\u9fff]{4,}")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-/]{3,}")
_COMMON_WORDS = {
    "this", "that", "with", "from", "have", "true", "false", "none", "null", "json",
    "pmem", "memory", "module", "search_memory", "record_memory", "cursor", "agent",
}
THRESHOLD = 0.15
# 标题太短时单个 4 字片段就能过阈值，噪声大；少于此指纹数的标题不单独计分
MIN_CITABLE_GRAMS = 12
# cites.json 缓存版本：改判定规则时递增，避免沿用旧 verdict
CITE_CACHE_VERSION = 3


def fingerprints(text: str) -> set[str]:
    grams: set[str] = set()
    for run in _CJK_RUN.findall(text):
        grams.update(run[i:i + 4] for i in range(len(run) - 3))
    for word in _IDENT.findall(text):
        word = word.strip(".-/").lower()
        if len(word) >= 4 and word not in _COMMON_WORDS:
            grams.add(word)
    return grams


def _coverage(own: set[str], reply_grams: set[str]) -> float:
    return len(own & reply_grams) / len(own) if own else 0.0


def assistant_text(transcript: Path) -> str:
    texts: list[str] = []
    try:
        lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or record.get("role") != "assistant":
            continue
        content = (record.get("message") or {}).get("content") or []
        for part in content if isinstance(content, list) else []:
            if isinstance(part, dict) and part.get("type") == "text":
                texts.append(str(part.get("text") or ""))
    return "\n\n".join(texts)


def judge(memories: dict[str, str], reply: str,
          citables: dict[str, str] | None = None) -> dict[str, dict]:
    """返回 {记忆 id: {score, cited}}，score 为记忆指纹在回复中出现的比例。

    citables 可选：记忆 id → 可复述标题（summary/title）。标题指纹不少于
    MIN_CITABLE_GRAMS 时，与正文覆盖率取较大值。
    """
    reply_grams = fingerprints(reply)
    citables = citables or {}
    result = {}
    for mid, text in memories.items():
        score = _coverage(fingerprints(text), reply_grams)
        title = citables.get(mid) or ""
        title_grams = fingerprints(title)
        if len(title_grams) >= MIN_CITABLE_GRAMS:
            score = max(score, _coverage(title_grams, reply_grams))
        result[mid] = {"score": round(score, 3), "cited": score >= THRESHOLD}
    return result
