"""结构化适用条件：项目声明 facets，记忆写 when，检索按 when 过滤。

设计见 docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md §3.3。
没声明 facets 时 when 不可用；记忆没写 when 的检索不过滤掉。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class FacetError(ValueError):
    """facets / when 校验失败。"""


@dataclass(frozen=True)
class FacetDef:
    name: str
    free: bool  # True：任意文字（声明为 str）；False：只能用 values 里的取值
    values: tuple[str, ...] = ()

    def accepts(self, value: str) -> bool:
        if self.free:
            return bool(value.strip())
        needle = value.casefold()
        return any(v.casefold() == needle for v in self.values)

    def canonical(self, value: str) -> str:
        text = " ".join(str(value).split())
        if self.free:
            return text
        for item in self.values:
            if item.casefold() == text.casefold():
                return item
        return text


def parse_facets(raw: Any) -> dict[str, FacetDef]:
    """解析 config.yaml 的 facets；空或缺省 → 未启用。"""
    if raw is None or raw == {}:
        return {}
    if not isinstance(raw, dict):
        raise FacetError(f"facets 应是键值对，实际是 {type(raw).__name__}")
    facets: dict[str, FacetDef] = {}
    for name, spec in raw.items():
        key = " ".join(str(name).split())
        if not key:
            raise FacetError("facets 的维度名不能为空")
        if isinstance(spec, str) and spec.strip().lower() == "str":
            facets[key] = FacetDef(key, free=True)
            continue
        if isinstance(spec, list):
            values = [" ".join(str(v).split()) for v in spec if v is not None and " ".join(str(v).split())]
            if not values:
                raise FacetError(f"facets.{key} 取值列表不能为空")
            facets[key] = FacetDef(key, free=False, values=tuple(dict.fromkeys(values)))
            continue
        raise FacetError(f"facets.{key} 应是 str 或取值列表，实际是 {type(spec).__name__}")
    return facets


def _as_values(raw: Any, path: str) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, (str, int, float)):
        text = " ".join(str(raw).split())
        return [text] if text else []
    if isinstance(raw, list):
        out = []
        for item in raw:
            if isinstance(item, (dict, list)) or item is None:
                raise FacetError(f"{path} 的值应是字符串或字符串列表")
            text = " ".join(str(item).split())
            if text:
                out.append(text)
        return out
    raise FacetError(f"{path} 的值应是字符串或字符串列表，实际是 {type(raw).__name__}")


def normalize_when(raw: Any, facets: dict[str, FacetDef], *, required: bool = True) -> dict[str, list[str]]:
    """把写入/查询的 when 收成 {维度: [取值]}；按 facets 校验。

    required=True：项目未声明 facets 时若仍传 when 则报错。
    required=False：未声明 facets 时忽略 when（用于旧索引读盘，when 进 extra）。
    """
    if raw is None or raw == {} or raw == "":
        return {}
    if not isinstance(raw, dict):
        raise FacetError(f"when 应是键值对，实际是 {type(raw).__name__}")
    if not facets:
        if required:
            raise FacetError("项目未在 config.yaml 声明 facets，不能使用 when；"
                            "先声明维度（如 platform: [ios, android] 或 model: str）")
        return {}
    out: dict[str, list[str]] = {}
    for key, value in raw.items():
        name = " ".join(str(key).split())
        if not name:
            raise FacetError("when 的维度名不能为空")
        facet = facets.get(name)
        if facet is None:
            known = "、".join(sorted(facets)) or "（无）"
            raise FacetError(f"when 用了未声明的维度 {name!r}；可选：{known}")
        values = _as_values(value, f"when.{name}")
        if not values:
            continue
        bad = [v for v in values if not facet.accepts(v)]
        if bad:
            if facet.free:
                raise FacetError(f"when.{name} 的取值不能为空")
            raise FacetError(f"when.{name} 取值 {bad[0]!r} 不在声明里；可选：{' / '.join(facet.values)}")
        out[name] = list(dict.fromkeys(facet.canonical(v) for v in values))
    return out


def when_structure_issues(raw: Any) -> list[str]:
    """读盘时会被跳过的 when 问题（结构不对）；不按 facets 校验。

    供 doctor / 存储扫描：坏维仍跳过以免拖垮整条记忆，但必须能被看见。
    """
    if raw is None or raw == {} or raw == "":
        return []
    if not isinstance(raw, dict):
        return [f"when 应是键值对，实际是 {type(raw).__name__}"]
    issues: list[str] = []
    for key, value in raw.items():
        name = " ".join(str(key).split())
        if not name:
            issues.append("when 含空维度名（读盘已跳过）")
            continue
        try:
            _as_values(value, f"when.{name}")
        except FacetError as exc:
            issues.append(f"{exc}（读盘已跳过该维）")
    return issues


def parse_when_loose(raw: Any) -> dict[str, list[str]]:
    """读盘时不按 facets 校验，只收成 {维度: [取值]}。

    非对象 → 空（调用方应对非对象报错）；某个维度结构不对则跳过该维，保留其余合法维。
    跳过的维度用 when_structure_issues 查出，由 doctor / 存储警告，避免静默丢条件。
    """
    if raw is None or raw == {} or raw == "":
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, value in raw.items():
        name = " ".join(str(key).split())
        if not name:
            continue
        try:
            values = _as_values(value, f"when.{name}")
        except FacetError:
            continue
        if values:
            out[name] = list(dict.fromkeys(values))
    return out


def conflicts(entry_when: dict[str, list[str]], query: dict[str, list[str]]) -> bool:
    """查询 when 与记忆 when 是否明确冲突：同一维度有声明且无交集。

    记忆没写 when、或记忆没写该维度 → 不冲突。
    """
    if not query or not entry_when:
        return False
    for key, wanted in query.items():
        have = entry_when.get(key)
        if not have:
            continue
        want = {v.casefold() for v in wanted}
        if not want.intersection(h.casefold() for h in have):
            return True
    return False
