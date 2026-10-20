"""写入时的质量提示：只提示、不拦截，帮助 Agent 把记忆写成下一个人用得上的结论。"""
from __future__ import annotations

import difflib
import re

from pmem.core.entry import RECORD_KINDS

_REASON = re.compile(
    r"根因|原因|因为|由于|所以|导致|结论|排除|风险|注意|不要|不能|勿|禁止|决定|边界|坑|前提|证据|实测|验证|否则|因此"
    r"|为了|目的|口径|差在|区别|澄清|回归|已知|避免|防止|以免"
    r"|because|root cause|risk|don't|must not"
)
# 相似度 0.5–0.8 的实体名几乎都是无关议题；2–3 个字母的短名（如 UI）被包含多是巧合
SIMILAR_ENTITY_RATIO = 0.8
SAME_ENTITY_RATIO = 0.85
MIN_CONTAINED_LEN = 4
_CHANGELOG_START = re.compile(r"^(已经?|新增|修复|改为|调整|重做|实现|完成|落地|删除|补充|更新|优化)")
# “决定”类要写取舍：为什么选它、排除了什么、代价；只写做法的，看代码就知道
_WHY = re.compile(
    r"原因|因为|由于|为了|目的|避免|防止|以免|否则|排除|而不是|而非|不用|不再|代价|风险|取舍|权衡|考虑到|踩坑|坑"
    r"|because|instead|trade-?off|otherwise"
)
VERIFY_KINDS = ("conclusion", "correction")
# 功能记录要能回答“谁要的、哪些行为不能被改掉”，否则后来的人会把它当冗余代码改回去
_REQUIREMENT = re.compile(
    r"需求|要求|用户|产品|策划|设计|必须|保持|不能|不要|不可|约定|规则|为了|以便|目的|期望|应当|应该|只在|仅在"
    r"|require|must|should|expect"
)
_LABEL_PREFIX = re.compile(r"^\s*(?:决定|结论)(?:\s*[（(][^）)]{0,40}[）)])?\s*[：:]\s*")


def content_hints(content: str, recommend_max: int, kind: str | None = None) -> list[str]:
    hints = []
    text = content.strip()
    # 正文开头的“决定：”“结论：”只是类型标签，却会命中原因词，先去掉再判断；“根因：”“风险：”本身就是原因，保留
    body = _LABEL_PREFIX.sub("", text, count=1).lower()
    has_reason = bool(_REASON.search(body))
    if kind in RECORD_KINDS:
        if not _REQUIREMENT.search(body):
            hints.append("功能记录要写需求来源和必须保持的行为：谁要求的、为什么，哪些行为以后不能改掉、在什么条件下成立；"
                         "不写改了哪个方法。")
    elif _CHANGELOG_START.match(body) and not has_reason:
        hints.append("读起来像变更记录：改了什么版本库里都有，记忆应写为什么这么改、排除了哪些方向、留下什么风险。")
    elif not has_reason:
        hints.append("没看到原因、结论或风险：下一个人最需要的是“为什么”和“别怎么做”。")
    elif kind == "decision" and not _WHY.search(body):
        hints.append("这条决定只写了怎么做：做法看代码就知道，记忆要写为什么这样选、排除了哪些做法、代价或风险是什么。")
    if len(text) > recommend_max:
        hints.append(f"正文 {len(text)} 字，超过建议的 {recommend_max} 字：只留下一个人最需要的结论，细节放进文档或提交说明。")
    return hints


def verify_hint(kind: str, verify: str | None) -> str | None:
    if kind in VERIFY_KINDS and not verify:
        return ("没填 verify：写一句怎么确认问题已解决或结论仍成立（命令、测试名、可观察的现象），"
                "下次遇到同样的问题可以直接验证，不用从头排查。")
    return None


def entity_hint(entity: str, known: list[str]) -> str | None:
    """实体在模块里从未出现过、且有相近的已有实体时提示，避免同一议题起多个名字；真正的新议题不打扰。"""
    if not known or entity.lower() in {k.lower() for k in known}:
        return None
    scored = sorted((-ratio, k) for k in known if (ratio := _related(entity, k)) is not None)
    if not scored:
        return None
    names = [k for _, k in scored[:3]]
    return f"实体 {entity} 在该模块里是第一次出现；相近的已有：{'、'.join(names)}。如果是同一议题，请改用已有名字。"


def similar_entity_pairs(names: list[str]) -> list[tuple[str, str]]:
    """同一模块里很可能是同一议题的实体对（只差大小写、复数、符号，或几乎相同）。"""
    first: dict[str, str] = {}
    for name in names:
        first.setdefault(name.lower(), name)
    unique = sorted(first.values())
    return [(a, b) for i, a in enumerate(unique) for b in unique[i + 1:]
            if _norm(a) == _norm(b) or _ratio(a, b) >= SAME_ENTITY_RATIO]


def _norm(name: str) -> str:
    return re.sub(r"s$", "", re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", name.lower()))


def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _related(a: str, b: str) -> float | None:
    """写入时值得提一句的相近名字：规整后相同、互相包含（短名不算）、或相似度高。"""
    x, y = _norm(a), _norm(b)
    if x == y:
        return 1.0
    shorter, longer = sorted((x, y), key=len)
    ratio = _ratio(a, b)
    if (len(shorter) >= MIN_CONTAINED_LEN and shorter in longer) or ratio >= SIMILAR_ENTITY_RATIO:
        return ratio
    return None
