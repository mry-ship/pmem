"""pmem health：记忆库健康报告，供模块负责人定期收口（未登记模块、重复模块、检索落空、过时记忆等）。"""
from __future__ import annotations

import difflib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from pmem.catalog.coverage import coverage_report
from pmem.catalog.migrate import MigrateError, stray_moves
from pmem.core.entry import KIND_LABELS
from pmem.core.quality import similar_entity_pairs
from pmem.core.registry import RegistryError
from pmem.index.tokenize import tokenize
from pmem.metrics.events import read_events
from pmem.service import COMPACT_MIN_GROUP, MemoryService

TOP = 10
NEGATIVE_KINDS = ("exclusion", "correction")
# 词集合的 Jaccard 相似度；长正文天然偏低，实测同议题无关的一正一反记忆在 0.11 以下
CONTRADICTION_OVERLAP = 0.15
MIN_SEARCHES_FOR_IDLE = 20
SEARCH_EVENTS = ("search", "mcp_search", "search_call")
# 按顺序匹配拒绝原因；“上限”的提示里也提到 draft_id，所以排在前面
REJECT_REASONS = (
    ("正文长度", "字数不在允许范围"),
    ("敏感信息", "疑似敏感信息"),
    ("上限", "当天同议题条数达到上限"),
    ("draft_id", "草稿覆盖不被允许"),
    ("不能覆盖", "草稿覆盖不被允许"),
    ("不能改到", "草稿覆盖不被允许"),
    ("已废弃", "模块已废弃（只读）"),
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


def _contradictions(visible: list) -> list[dict]:
    """同模块同议题、都还现行、正文高度相似但一条肯定一条否定（结论/决定 对 排除/更正）的记忆对。
    较早那条在较晚那条写下之后被核对过，视为负责人已看过，不再提示。"""
    groups: dict[tuple[str, str], list] = defaultdict(list)
    for e in visible:
        if e.kind != "risk":
            groups[(e.module, e.entity)].append(e)
    pairs = []
    for (module, entity), items in groups.items():
        tokens = {e.id: set(tokenize(e.content)) for e in items}
        for i, a in enumerate(items):
            for b in items[i + 1:]:
                if (a.kind in NEGATIVE_KINDS) == (b.kind in NEGATIVE_KINDS):
                    continue
                if a.id in b.supersedes or b.id in a.supersedes:
                    continue
                old, new = sorted((a, b), key=lambda e: (e.note_date, e.id))
                if old.checked_date >= new.note_date and old.verified:
                    continue
                union = tokens[a.id] | tokens[b.id]
                score = len(tokens[a.id] & tokens[b.id]) / len(union) if union else 0.0
                if score >= CONTRADICTION_OVERLAP:
                    pairs.append({"module": module, "entity": entity, "old": old.id, "old_kind": old.kind,
                                  "new": new.id, "new_kind": new.kind, "overlap": round(score, 2)})
    pairs.sort(key=lambda p: -p["overlap"])
    return pairs[:TOP]


def build_health(root: Path, days: int = 60, now: float | None = None) -> dict:
    now = now or time.time()
    since = now - days * 86400
    service = MemoryService(root)
    try:
        registry = service.registry
        visible = service.index.visible()
        events = list(read_events(service.config.cache_dir, since))
        stale = service.index.check_anchors(visible)
        compact = service.compact_groups(min_size=COMPACT_MIN_GROUP)
        try:
            strays, stray_problem = stray_moves(service.storage, registry), None
        except MigrateError as exc:
            # 合并冲突后同一个记忆文件在新旧模块目录各留一份：作为一节列出，不让整份报告变成异常
            strays, stray_problem = [], str(exc)
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
    restarts = [e for e in events if e["type"] == "server_restart" and e.get("kind") != "reload"]
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
        "stray_problem": stray_problem,
        "unmapped_dirs": unmapped,
        "searches": len(searches),
        "misses": _misses(searches),
        "stale": {"total": len(stale), "by_module": stale_by_module.most_common(TOP),
                  "ids": sorted(stale)[:TOP]},
        "contradictions": _contradictions(visible),
        "idle_modules": idle,
        "rejected": {"total": len(rejected),
                     "by_reason": Counter(reject_reason(e.get("error") or "") for e in rejected).most_common(),
                     "by_module": Counter(e.get("module") or "？" for e in rejected).most_common(5)},
        "server_restarts": Counter(e.get("reason") or "？" for e in restarts).most_common(TOP),
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
    section("记忆文件重复", [h["stray_problem"]] if h.get("stray_problem") else [],
            "对比两份内容，删掉旧模块目录下那份后再运行 pmem migrate tidy --apply")
    section("没有归属模块的代码目录", [f"{folder}：{n} 个文件" for folder, n in h["unmapped_dirs"]],
            "在 modules.yaml 里把目录加进对应模块的 paths；新业务就登记新模块")
    section(f"检索落空热点（本机 {h['searches']} 次检索）", [f"{m} / {what}：{n} 次" for m, what, n in h["misses"]],
            "这些问题反复查不到：有结论就补写记忆，叫法不同就按 pmem-normalize 技能登记同义词")
    s = h["stale"]
    section(f"可能过时的记忆（{s['total']} 条）", [f"{m}：{n} 条" for m, n in s["by_module"]],
            "打开关联代码核对：仍成立 pmem confirm <id>，不成立写 correction 替代；过时又没有替代结论的 pmem archive <id>")
    section("疑似互相矛盾的记忆", [
        f"{c['module']} / {c['entity']}：{c['old']}（{KIND_LABELS.get(c['old_kind'], c['old_kind'])}）"
        f" 与 {c['new']}（{KIND_LABELS.get(c['new_kind'], c['new_kind'])}），正文相似度 {c['overlap']}"
        for c in h["contradictions"]
    ], "打开两条对照：确实冲突就写 correction 替代过时的那条（supersedes 填它的 id）；"
       "只是互补就 pmem confirm <较早那条的 id>，之后不再提示")
    if h["idle_modules"]:
        section(f"统计期内本机没检索过的模块（{len(h['idle_modules'])} 个）", ["、".join(h["idle_modules"][:20])],
                "可能是没人改这些模块，也可能是路径没登记全导致闸门没提醒；对照 pmem doctor 的覆盖率看")
    r = h["rejected"]
    section(f"被拒绝的写入（{r['total']} 次）", [f"{label}：{n} 次" for label, n in r["by_reason"]]
            + ([f"集中在：{'、'.join(f'{m} {n} 次' for m, n in r['by_module'])}"] if r["by_module"] else []),
            "字数或上限拒绝多：提醒合并成一条再写；模块名错误多：给常用叫法加 aliases")
    section(f"MCP 服务被看门狗重启（{sum(n for _, n in h['server_restarts'])} 次）",
            [f"{reason}：{n} 次" for reason, n in h["server_restarts"]],
            "偶发可忽略；反复崩溃看 Cursor 的 MCP 日志，反复超时可调大 config.yaml 的 server.request_timeout")
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
