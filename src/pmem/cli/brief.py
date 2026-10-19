"""--brief：把服务返回的 JSON 压成每条一行的文本，终端里直接能读，不必再用管道筛选。"""
from __future__ import annotations

from pmem.core.entry import KIND_LABELS, strip_kind_prefix
from pmem.index.anchors import STALE_LABEL
from pmem.index.graph import preview

PREVIEW = 120


def _kind(kind: str) -> str:
    return KIND_LABELS.get(kind, kind)


def _stale(row: dict) -> list[str]:
    return [f"    ⚠ {STALE_LABEL}：{'；'.join(row.get('check') or [])}"] if row.get("stale") else []


def _tail(result: dict) -> list[str]:
    lines = [f"! {w}" for w in result.get("warnings") or []]
    if result.get("verify_hint"):
        lines.append(f"提示：{result['verify_hint']}")
    related = result.get("related") or []
    if related:
        names = [r if isinstance(r, str) else f"{r['module']}（{r['via']}）" for r in related]
        lines.append("相关模块：" + "；".join(names))
    return lines


def _search(result: dict) -> list[str]:
    items = result.get("items") or []
    head = f"{result.get('module') or '全部模块'}：{len(items)} 条"
    if result.get("fallback"):
        head += "（议题内没有命中，已退回整个模块）"
    lines = [head]
    for item in items:
        where = f"{item['module']} · " if item.get("module") else ""
        seed = "（种子，待确认）" if item.get("status") == "seed" else ""
        if item.get("seen"):
            text = f"（本对话已给过全文）{item.get('summary') or ''}"
        else:
            body = preview(strip_kind_prefix(item.get("content") or ""), PREVIEW)
            text = f"{item['summary']}｜{body}" if item.get("summary") else body
        scope = "（全项目）" if item.get("scope") == "project" else ""
        lines.append(f"- {where}{_kind(item['kind'])}{seed}{scope}｜{item['entity']}｜{item['date']}｜{item['id']}："
                     f"{text}")
        if item.get("verify"):
            lines.append(f"    验证：{preview(item['verify'], PREVIEW)}")
        lines += _stale(item)
    if result.get("seen_hint"):
        lines.append(f"提示：{result['seen_hint']}")
    return lines + _tail(result)


def _graph(result: dict) -> list[str]:
    if "timeline" in result:
        lines = [f"{result['module']} / {result['entity']} 时间线："]
        for row in result["timeline"]:
            state = f"→ {row['until']} 被 {row['superseded_by']} 替代" if row.get("superseded_by") else "现行"
            lines.append(f"- {row['date']} {_kind(row['kind'])}｜{row['id']}｜{state}：{row['preview']}")
            lines += _stale(row)
        return lines + _tail(result)
    topics = result.get("topics") or []
    lines = [f"{result['module']}：{len(topics)} 个议题"]
    for topic in topics:
        lines.append(f"## {topic['entity']}（现行 {topic['current']}，已替代 {topic['superseded']}，最近 {topic['last']}）")
        for row in topic.get("latest") or []:
            lines.append(f"- {_kind(row['kind'])}｜{row['date']}｜{row['id']}：{row['preview']}")
            lines += _stale(row)
    return lines + _tail(result)


def _record(result: dict) -> list[str]:
    action = "已覆盖" if result.get("overwritten") else "已写入"
    lines = [f"{action} {result['module']} / {result['entity']}：{result['id']}（再次写入同一条时用 --draft-id {result['draft_id']}）"]
    for row in result.get("similar") or []:
        lines.append(f"相近记忆：{_kind(row['kind'])}｜{row['entity']}｜{row['date']}｜{row['id']}：{row['preview']}")
    lines += [f"提示：{hint}" for hint in result.get("hints") or []]
    return lines + _tail(result)


RENDERERS = {"search": _search, "graph": _graph, "record": _record}


def render_brief(command: str, result: dict) -> str:
    if not result.get("ok"):
        extra = {k: v for k, v in result.items() if k not in ("ok", "error")}
        return f"失败：{result.get('error')}" + (f"\n{extra}" if extra else "")
    return "\n".join(RENDERERS[command](result))
