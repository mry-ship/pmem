"""pmem health：记忆库健康报告，供模块负责人定期收口（未登记模块、重复模块、检索落空、过时记忆等）。"""
from __future__ import annotations

import difflib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from pmem.core.quality import similar_entity_pairs
from pmem.core.registry import RegistryError
from pmem.metrics.events import read_events
from pmem.service import COMPACT_MIN_GROUP, MemoryService

TOP = 10
MIN_SEARCHES_FOR_IDLE = 20
SEARCH_EVENTS = ("search", "mcp_search", "search_call")
# 按顺序匹配拒绝原因；“上限”的提示里也提到 draft_id，所以排在前面
REJECT_REASONS = (
    ("正文长度", "字数不在允许范围"),
    ("敏感信息", "疑似敏感信息"),
    ("上限", "当天同议题条数达到上限"),
    ("draft_id", "草稿覆盖不被允许"),
    ("大类", "大类不存在"),
    ("模块", "模块名有误"),
    ("entity", "缺少议题"),
    ("kind", "类型不对"),
    ("status", "状态不对"),
)


def reject_reason(error: str) -> str:
    return next((label for key, label in REJECT_REASONS if key in error), "其他")


def _duplicate_modules(ids: list[str]) -> list[list[str]]:
    """短名相同（跨大类）或几乎相同的模块组。"""
    by_name: dict[str, list[str]] = defaultdict(list)
    for mid in ids:
        by_name[mid.split(".", 1)[-1].lower()].append(mid)
    groups = {tuple(sorted(group)) for group in by_name.values() if len(group) > 1}
    names = {mids[0].split(".", 1)[-1]: mids for mids in by_name.values()}
    for a, b in similar_entity_pairs(list(names)):
        groups.add(tuple(sorted({*names[a], *names[b]})))
    return [list(g) for g in sorted(groups)]


def _is_registered(registry, mid: str) -> bool:
    try:
        return registry.resolve_module(mid).known
    except RegistryError:
        return False


def _misses(searches: list[dict]) -> list[tuple[str, str, int]]:
    """检索落空（没返回任何记忆）与议题落空（按议题没找到、退回整模块）的热点。"""
    counter: Counter = Counter()
    for e in searches:
        module = e.get("module") or "（全局）"
        if not e.get("ids"):
            what = e.get("entity") or (e.get("query") or "")[:30]
            if not what:
                what = "（整模块浏览：当时模块里还没有记忆）" if e.get("module") else "（按路径检索：路径未登记到模块）"
            counter[(module, what)] += 1
        elif e.get("fallback") == "module" and e.get("entity"):
            counter[(module, f"议题 {e['entity']}（退回整模块）")] += 1
    return [(m, what, n) for (m, what), n in counter.most_common(TOP)]


def build_health(root: Path, days: int = 60, now: float | None = None) -> dict:
    from pmem.cli.doctor_cmd import coverage_report
    from pmem.cli.migrate_cmd import stray_moves

    now = now or time.time()
    since = now - days * 86400
    service = MemoryService(root)
    try:
        registry = service.registry
        visible = service.index.visible()
        events = list(read_events(service.config.cache_dir, since))
        stale = service.index.check_anchors(visible)
        compact = service.compact_groups(min_size=COMPACT_MIN_GROUP)
        strays = stray_moves(service.storage, registry)
        unmapped = coverage_report(service.root, registry)["unmapped"]
    finally:
        service.close()

    registered = [mid for mid, m in registry.modules.items() if not m.merged_into]
    counts = Counter(e.module for e in visible)

    unregistered = []
    for mid, n in sorted(counts.items()):
        if _is_registered(registry, mid):
            continue
        unregistered.append({
            "module": mid, "memories": n, "candidate": mid in registry.candidates,
            "similar": difflib.get_close_matches(mid, registered, n=2, cutoff=0.6),
        })

    searches = [e for e in events if e["type"] == "search" and e.get("ok")]
    searched = {e.get("module") for e in events if e["type"] in SEARCH_EVENTS}
    idle = sorted(m for m in registered if counts[m] and m not in searched and not registry.modules[m].deprecated) \
        if len(searches) >= MIN_SEARCHES_FOR_IDLE else None

    rejected = [e for e in events if e["type"] == "record_rejected"]
    stale_by_module = Counter(e.module for e in visible if e.id in stale)
    entities: dict[str, list[str]] = defaultdict(list)
    for e in visible:
        entities[e.module].append(e.entity)

    return {
        "days": days,
        "memories": len(visible),
        "modules_registered": len(registered),
        "unregistered": unregistered,
        "duplicates": _duplicate_modules(registered + [u["module"] for u in unregistered]),
        "strays": [{"id": s.entry_id, "from": s.source, "to": s.target} for s in strays],
        "unmapped_dirs": unmapped,
        "searches": len(searches),
        "misses": _misses(searches),
        "stale": {"total": len(stale), "by_module": stale_by_module.most_common(TOP),
                  "ids": sorted(stale)[:TOP]},
        "idle_modules": idle,
        "rejected": {"total": len(rejected),
                     "by_reason": Counter(reject_reason(e.get("error") or "") for e in rejected).most_common(),
                     "by_module": Counter(e.get("module") or "？" for e in rejected).most_common(5)},
        "seeds": Counter(e.module for e in visible if e.status == "seed").most_common(),
        "compact": [(g["module"], g["entity"], g["count"]) for g in compact.get("groups", [])][:TOP],
        "entity_pairs": [(m, a, b) for m, names in sorted(entities.items()) for a, b in similar_entity_pairs(names)][:TOP],
    }


def render(h: dict) -> str:
    lines = [f"pmem 健康报告（统计期 {h['days']} 天；检索与写入数据只来自本机）",
             f"现行记忆 {h['memories']} 条，登记模块 {h['modules_registered']} 个"]
    problems = 0

    def section(title: str, rows: list[str], action: str) -> None:
        nonlocal problems
        if not rows:
            return
        problems += 1
        lines.extend(["", f"【{title}】", *[f"  {r}" for r in rows], f"  → {action}"])

    section("未登记模块（写入时自动新建）", [
        f"{u['module']}：{u['memories']} 条" + ("（冷候选，可转正）" if u["candidate"] else "")
        + (f"，相近：{'、'.join(u['similar'])}" if u["similar"] else "")
        for u in h["unregistered"]
    ], "笔误或归错就 pmem migrate merge <未登记模块> <正确模块>；确属新业务就在 modules.yaml 登记它的 paths")
    section("疑似重复模块", ["、".join(g) for g in h["duplicates"]],
            "确认是同一业务后 pmem migrate merge <被并入> <保留>")
    section("记忆还在旧模块名下", [f"{s['id']}：{s['from']} → {s['to']}" for s in h["strays"][:TOP]]
            + ([f"……另有 {len(h['strays']) - TOP} 条"] if len(h["strays"]) > TOP else []),
            "pmem migrate tidy --apply 把它们搬到新模块名下")
    section("没有归属模块的代码目录", [f"{folder}：{n} 个文件" for folder, n in h["unmapped_dirs"]],
            "在 modules.yaml 里把目录加进对应模块的 paths；新业务就登记新模块")
    section(f"检索落空热点（本机 {h['searches']} 次检索）", [f"{m} / {what}：{n} 次" for m, what, n in h["misses"]],
            "这些问题反复查不到：有结论就补写记忆，叫法不同就按 pmem-normalize 技能登记同义词")
    s = h["stale"]
    section(f"可能过时的记忆（{s['total']} 条）", [f"{m}：{n} 条" for m, n in s["by_module"]],
            "打开关联代码核对：仍成立 pmem confirm <id>，不成立写 correction 替代；过时又没有替代结论的 pmem archive <id>")
    if h["idle_modules"]:
        section(f"统计期内本机没检索过的模块（{len(h['idle_modules'])} 个）", ["、".join(h["idle_modules"][:20])],
                "可能是没人改这些模块，也可能是路径没登记全导致闸门没提醒；对照 pmem doctor 的覆盖率看")
    r = h["rejected"]
    section(f"被拒绝的写入（{r['total']} 次）", [f"{label}：{n} 次" for label, n in r["by_reason"]]
            + ([f"集中在：{'、'.join(f'{m} {n} 次' for m, n in r['by_module'])}"] if r["by_module"] else []),
            "字数或上限拒绝多：提醒合并成一条再写；模块名错误多：给常用叫法加 aliases")
    section("待确认的种子记忆", [f"{m}：{n} 条" for m, n in h["seeds"]],
            "pmem seed 查看，确认后 pmem seed --accept --module <模块>")
    section(f"零碎记忆可合并（每个议题 {COMPACT_MIN_GROUP} 条以上）", [f"{m} / {e}：{n} 条" for m, e, n in h["compact"]],
            "在 Cursor 里说“按 pmem-compact 技能合并记忆”")
    section("同一模块里名字相近的议题", [f"{m}：{a} / {b}" for m, a, b in h["entity_pairs"]],
            "是同一议题时，以后写入统一用一个名字；旧记忆可按 pmem-compact 合并")
    if not problems:
        lines += ["", "没有需要处理的问题"]
    return "\n".join(lines)


def run_health(root: Path, days: int, as_json: bool) -> int:
    report = build_health(root, days)
    print(json.dumps(report, ensure_ascii=False, indent=2) if as_json else render(report))
    return 0
