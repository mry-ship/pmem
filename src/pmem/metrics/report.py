"""pmem report：从本机事件日志与记忆库算出可量化的收益。"""
from __future__ import annotations

import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

from pmem.catalog.coverage import module_heat
from pmem.core.entry import KIND_LABELS, VISIBLE_STATUSES
from pmem.index.store import ulid_ms
from pmem.metrics.cite import assistant_text, judge
from pmem.metrics.events import MIN_SEARCHES_FOR_IDLE, read_events
from pmem.scan.lite import file_heat
from pmem.service import MemoryService

AVOID_KINDS = {"exclusion", "risk", "correction"}
MIN_GROUP = 5
HOT_TOP = 10
CLI_LINK_SECONDS = 30
OWN_WRITE_SLACK = 60
USAGE_TOP = 5
MIN_RETURNS_TO_REVIEW = 3


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _link_cli_searches(events: list[dict]) -> None:
    """Agent 在终端里跑 pmem search 时，检索事件本身不知道对话 id，按时间最近的 search_call 补上。
    闸门在命令执行完才记 search_call（旧版在执行前记），所以前后都要找。"""
    calls = [e for e in events if e["type"] in ("search_call", "search_call_unseen")
             and e.get("via") == "cli" and e.get("conv")]
    for e in events:
        if e["type"] == "search" and not e.get("conv"):
            near = [c for c in calls if abs(e["ts"] - c["ts"]) <= CLI_LINK_SECONDS]
            if near:
                e["conv"] = min(near, key=lambda c: abs(e["ts"] - c["ts"]))["conv"]


def _conversations(events: list[dict]) -> dict[str, dict]:
    convs: dict[str, dict] = defaultdict(lambda: {
        "prompts": 0, "stops": 0, "edits": 0, "input_tokens": 0, "output_tokens": 0,
        "returned": set(), "recorded": set(), "transcript": None, "start": None, "end": None,
    })
    for e in events:
        conv = e.get("conv")
        if not conv:
            continue
        c = convs[conv]
        c["start"] = e["ts"] if c["start"] is None else min(c["start"], e["ts"])
        c["end"] = e["ts"] if c["end"] is None else max(c["end"], e["ts"])
        kind = e["type"]
        if kind == "prompt":
            c["prompts"] += 1
        elif kind == "edit":
            c["edits"] += 1
        elif kind == "stop":
            c["stops"] += 1
            c["input_tokens"] += e.get("input_tokens") or 0
            c["output_tokens"] += e.get("output_tokens") or 0
            c["returned"].update(e.get("returned") or [])
            c["recorded"].update(e.get("recorded") or [])
            c["transcript"] = e.get("transcript") or c["transcript"]
        elif kind in ("mcp_search", "search"):
            c["returned"].update(e.get("ids") or [])
        elif kind in ("mcp_record", "record"):
            c["recorded"].update(e.get("ids") or ([e["id"]] if e.get("id") else []))
    return convs


def _citations(cache_dir: Path, convs: dict[str, dict], contents: dict[str, str]) -> dict:
    cache_path = cache_dir / "cites.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cache = {}
    returned = cited = 0
    cited_ids: Counter = Counter()
    judged_ids: Counter = Counter()
    for conv, c in convs.items():
        ids = sorted(i for i in c["returned"] - c["recorded"] if i in contents)
        transcript = Path(c["transcript"]) if c["transcript"] else None
        if not ids or transcript is None or not transcript.exists():
            continue
        stamp = f"{transcript.stat().st_mtime_ns}:{','.join(ids)}"
        hit = cache.get(conv)
        if not hit or hit.get("stamp") != stamp:
            verdict = judge({i: contents[i] for i in ids}, assistant_text(transcript))
            hit = {"stamp": stamp, "cited": [i for i, v in verdict.items() if v["cited"]]}
            cache[conv] = hit
        returned += len(ids)
        cited += len(hit["cited"])
        cited_ids.update(hit["cited"])
        judged_ids.update(ids)
    try:
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass
    return {"returned": returned, "cited": cited, "top": cited_ids.most_common(5),
            "by_id": dict(cited_ids), "judged": dict(judged_ids)}


def _usage(convs: dict[str, dict], events: list[dict], citations: dict, visible: list, since: float) -> dict:
    """每条记忆在统计期内被返回、被采用的次数（同一对话只算一次）。"""
    known = {e.id: e for e in visible}
    returned: Counter = Counter()
    for c in convs.values():
        returned.update(i for i in c["returned"] - c["recorded"] if i in known)
    for e in events:
        if e["type"] == "search" and e.get("ok") and not e.get("conv"):
            returned.update(i for i in e.get("ids") or [] if i in known)
    cited, judged = Counter(citations["by_id"]), Counter(citations["judged"])

    def row(i: str) -> dict:
        e = known[i]
        return {"id": i, "module": e.module, "entity": e.entity, "returned": returned[i], "cited": cited[i],
                "content": e.content}

    idle = [e for e in visible if returned[e.id] == 0 and ulid_ms(e.id) / 1000 < since]
    return {
        "returned_memories": len(returned),
        "top": [row(i) for i, _ in cited.most_common() if i in known][:USAGE_TOP],
        "review": [row(i) for i, n in judged.most_common()
                   if i in known and n >= MIN_RETURNS_TO_REVIEW and cited[i] == 0][:USAGE_TOP],
        "idle": len(idle),
        "idle_modules": Counter(e.module for e in idle).most_common(3),
    }


def _compare(convs: dict[str, dict]) -> dict:
    groups: dict[str, list[dict]] = {"hit": [], "miss": []}
    for c in convs.values():
        if c["edits"] == 0 or c["stops"] == 0:
            continue
        groups["hit" if c["returned"] - c["recorded"] else "miss"].append(c)
    out = {}
    for name, rows in groups.items():
        out[name] = {
            "n": len(rows),
            "input_tokens": _median([r["input_tokens"] for r in rows]),
            "output_tokens": _median([r["output_tokens"] for r in rows]),
            "turns": _median([max(r["prompts"], r["stops"]) for r in rows]),
            "edits": _median([r["edits"] for r in rows]),
            "minutes": _median([(r["end"] - r["start"]) / 60 for r in rows]),
        }
    out["enough"] = all(out[g]["n"] >= MIN_GROUP for g in ("hit", "miss"))
    return out


def build_report(root: Path, days: int = 30, now: float | None = None, heat: bool = True) -> dict:
    now = now or time.time()
    since = now - days * 86400
    service = MemoryService(root)
    try:
        cache_dir = service.config.cache_dir
        events = list(read_events(cache_dir, since))
        _link_cli_searches(events)
        entries = service.index.entries()
        hidden = service.index.superseded()
        registry = service.registry
        user = service.user
        uncommitted = service.vcs.uncommitted_count(service.config.entries_dir)
        analysis_reminder = bool(service.config.get("gate.analysis_reminder")) and service.config.get("gate.mode") != "off"
    finally:
        service.close()
    contents = {e.id: e.content for e in entries}

    searches = [e for e in events if e["type"] == "search" and e.get("ok")]
    hits = [e for e in searches if e.get("ids")]
    avoided = [e for e in hits if AVOID_KINDS & set(e.get("kinds") or [])]
    reused = [e for e in hits if any(a and a != e.get("user") for a in e.get("authors") or [])]
    reused_authors = {a for e in reused for a in e.get("authors") or [] if a and a != e.get("user")}

    # 写入数以记忆文件为准：事件日志可以被关闭，文件不会
    mine = [e for e in entries if e.author == user and ulid_ms(e.id) / 1000 >= since]
    record_kinds = Counter(e.kind for e in mine)

    # MCP 检索在返回结果后记为 mcp_search；终端检索在执行前记为 search_call
    calls = [e for e in events if e["type"] in ("search_call", "mcp_search")]
    gates = [e for e in events if e["type"] == "gate"]
    gate_converted = sum(
        1 for g in gates
        if any(c.get("conv") == g.get("conv") and c.get("module") == g.get("module") and c["ts"] >= g["ts"] for c in calls)
    )
    written = [
        {"conv": e["conv"], "module": e.get("module"), "ts": e["ts"]}
        for e in events if e["type"] in ("record", "mcp_record", "record_call") and e.get("conv")
    ] + [
        {"conv": e.source_conversation, "module": e.module, "ts": ulid_ms(e.id) / 1000}
        for e in mine if e.source_conversation
    ]
    nudges = [(e, m) for e in events if e["type"] == "stop" for m in e.get("nudged") or []]
    nudge_converted = sum(
        1 for stop, module in nudges
        if any(w["conv"] == stop.get("conv") and w["module"] == module and w["ts"] >= stop["ts"] for w in written)
    )

    # 排查类对话：提问含排查用语且查过记忆；以最后一次 stop 记下的“只查没改也没记”的模块为准
    analysis_convs = {e["conv"] for e in events if e["type"] == "prompt" and e.get("analysis") and e.get("conv")}
    consulted_convs = {e.get("conv") for e in events if e["type"] in ("search_call", "mcp_search", "search")}
    last_analyzed = {e["conv"]: e.get("analyzed") or [] for e in events if e["type"] == "stop" and e.get("conv")}
    left = {c: m for c, m in last_analyzed.items() if m and c in analysis_convs}

    convs = _conversations(events)
    # 对话期间自己新写的记忆被返回、被复述不算复用；终端写入的事件不带对话 id，所以按记忆文件的创建时间判断
    authored = [(ulid_ms(e.id) / 1000, e.id) for e in entries if e.author == user]
    for c in convs.values():
        c["recorded"].update(i for ts, i in authored if c["start"] - OWN_WRITE_SLACK <= ts <= c["end"] + OWN_WRITE_SLACK)
    visible = [e for e in entries if e.id not in hidden and e.status in VISIBLE_STATUSES]
    authors_by_module: dict[str, set] = defaultdict(set)
    for e in visible:
        authors_by_module[e.module].add(e.author)
    registered = [m for m, mod in registry.modules.items() if not mod.merged_into]

    hot = []
    if heat:
        _, file_counts = file_heat(root, vcs=service.vcs)
        totals = module_heat(registry, file_counts)
        hot = [(m, n, len([e for e in visible if e.module == m])) for m, n in totals.most_common(HOT_TOP)]

    citations = _citations(cache_dir, convs, contents)
    return {
        "days": days,
        "search": {
            "total": len(searches),
            "by_source": dict(Counter(e.get("source") for e in searches)),
            "hits": len(hits),
            "avoided": len(avoided),
            "reused": len(reused),
            "reused_authors": len(reused_authors),
        },
        "citations": citations,
        "usage": _usage(convs, events, citations, visible, since),
        "records": {"total": sum(record_kinds.values()), "by_kind": dict(record_kinds)},
        "habits": {
            "gates": len(gates), "gate_converted": gate_converted,
            "nudges": len(nudges), "nudge_converted": nudge_converted,
            "analysis_conversations": len(analysis_convs & consulted_convs),
            "analysis_left": len(left),
            "analysis_left_modules": len({m for mods in left.values() for m in mods}),
            "analysis_reminder": analysis_reminder,
            "conversations": len(convs),
        },
        "compare": _compare(convs),
        "assets": {
            "memories": len(visible),
            "new": len([e for e in visible if ulid_ms(e.id) / 1000 >= since]),
            "by_kind": dict(Counter(e.kind for e in visible)),
            "modules_with_memory": len(authors_by_module),
            "modules_registered": len(registered),
            "single_author": sorted(m for m, a in authors_by_module.items() if len(a) == 1),
            "hot": hot,
            "uncommitted": uncommitted,
        },
    }


def _pct(part: int, whole: int) -> str:
    return f"{part / whole:.0%}" if whole else "—"


def _num(value: float | None, unit: str = "") -> str:
    if value is None:
        return "—"
    if value >= 10000:
        return f"{value / 10000:.1f} 万{unit}"
    return f"{value:.0f}{unit}" if value >= 10 else f"{value:.1f}{unit}"


def _snippet(text: str, width: int = 40) -> str:
    line = " ".join(text.split())
    return line if len(line) <= width else line[:width] + "…"


def _render_usage(u: dict, memories: int, searches: int) -> list[str]:
    lines = ["", "【记忆使用】同一对话里返回多次只算一次；对话中自己新写的不计入",
             f"  被返回过的记忆 {u['returned_memories']} 条（占有效记忆 {_pct(u['returned_memories'], memories)}）"]
    if u["top"]:
        lines.append("  最常被用到：")
        lines += [f"    {r['module']}/{r['entity']} 用到 {r['cited']} 次、返回 {r['returned']} 次：{_snippet(r['content'])}"
                  for r in u["top"]]
    if u["review"]:
        lines.append(f"  返回 {MIN_RETURNS_TO_REVIEW} 次以上却从没被用到（可能过时、写得不清楚或归错模块，值得复查）：")
        lines += [f"    [{r['id']}] {r['module']}/{r['entity']} 返回 {r['returned']} 次：{_snippet(r['content'])}"
                  for r in u["review"]]
    if searches >= MIN_SEARCHES_FOR_IDLE and u["idle"]:
        where = "、".join(f"{m} {n} 条" for m, n in u["idle_modules"])
        lines.append(f"  统计期之前写的记忆里有 {u['idle']} 条一次都没被检索到（主要在 {where}）")
    return lines


def render(report: dict) -> str:
    s, c, r, h, a = (report[k] for k in ("search", "citations", "records", "habits", "assets"))
    kinds = "、".join(f"{KIND_LABELS.get(k, k)} {n}" for k, n in sorted(r["by_kind"].items(), key=lambda kv: -kv[1]))
    lines = [
        f"pmem 收益报告（最近 {report['days']} 天，仅本机）",
        "",
        "【收益】",
        f"  检索记忆 {s['total']} 次，命中 {s['hits']} 次（{_pct(s['hits'], s['total'])}）",
        f"  避坑提示 {s['avoided']} 次：命中结果里含排除项、风险或更正",
        f"  跨人复用 {s['reused']} 次：用到了 {s['reused_authors']} 位同事写的记忆",
        (f"  记忆被采用：对话中返回 {c['returned']} 条，Agent 回复里明确用到 {c['cited']} 条"
         f"（{_pct(c['cited'], c['returned'])}，按字面重合计，是保守下限）"),
        f"  新写记忆 {r['total']} 条" + (f"（{kinds}）" if kinds else ""),
        "",
        "【习惯】",
        f"  改代码前被提醒先查 {h['gates']} 次，随后真的查了 {h['gate_converted']} 次（{_pct(h['gate_converted'], h['gates'])}）",
        f"  结束时被提醒记录 {h['nudges']} 次，随后写了 {h['nudge_converted']} 次（{_pct(h['nudge_converted'], h['nudges'])}）",
    ]
    if h.get("analysis_conversations"):
        lines.append(
            f"  排查类对话 {h['analysis_conversations']} 个，其中 {h['analysis_left']} 个结束时仍有查过记忆、"
            f"却没改代码也没写记忆的模块（共 {h['analysis_left_modules']} 个）"
            + ("；如果常有结论被漏记，可在 .memory/config.yaml 打开 gate.analysis_reminder"
               if h["analysis_left"] and not h.get("analysis_reminder") else "")
        )
    lines += _render_usage(report["usage"], a["memories"], s["total"])
    cmp_ = report["compare"]
    lines += ["", "【对话对照】改了代码的对话，按“是否用到他人/既有记忆”分组，取中位数"]
    lines.append(f"  {'':<10}{'对话数':>6}{'输入 token':>12}{'输出 token':>12}{'轮数':>6}{'编辑':>6}{'时长(分)':>9}")
    for name, label in (("hit", "用到记忆"), ("miss", "未用到")):
        g = cmp_[name]
        lines.append(f"  {label:<10}{g['n']:>6}{_num(g['input_tokens']):>12}{_num(g['output_tokens']):>12}"
                     f"{_num(g['turns']):>6}{_num(g['edits']):>6}{_num(g['minutes']):>9}")
    if not cmp_["enough"]:
        lines.append(f"  样本不足（每组至少 {MIN_GROUP} 个对话才有参考意义）；两组任务难度也不同，只看趋势，严格对比用 pmem bench")
    lines += [
        "",
        "【知识资产】",
        (f"  有效记忆 {a['memories']} 条，本期新增 {a['new']} 条；"
         f"{a['modules_with_memory']}/{a['modules_registered']} 个登记模块已有记忆"),
    ]
    if a.get("uncommitted"):
        lines.append(f"  本机还有 {a['uncommitted']} 条记忆未提交，队友看不到")
    if a["single_author"]:
        lines.append(f"  只有一位作者的模块 {len(a['single_author'])} 个（知识集中在一个人）：" + "、".join(a["single_author"][:8]))
    if a["hot"]:
        bare = [m for m, _, n in a["hot"] if n == 0]
        lines.append(f"  近半年改动最多的 {len(a['hot'])} 个模块中，{len(a['hot']) - len(bare)} 个已有记忆")
        if bare:
            lines.append("  值得优先补记忆：" + "、".join(bare))
    return "\n".join(lines)


def run_report(root: Path, days: int, as_json: bool) -> int:
    report = build_report(root, days)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report))
    return 0
