"""pmem map：记忆演化图 + 图上自检（漏记、断链、悬而未决、过期），顶部给总评。

总评衡量“存储做得好不好”（结构完整、有没有漏），不衡量“对 AI 有没有用”——后者看 pmem report 与 pmem bench。
"""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from wcmatch import glob as wglob

from pmem.core.entry import VISIBLE_STATUSES
from pmem.core.registry import RegistryError
from pmem.index.memmap import build_map
from pmem.metrics.health import _contradictions
from pmem.scan.lite import BULK_COMMIT
from pmem.service import MemoryService

GAP_DAYS = 30
_GLOB = wglob.GLOBSTAR | wglob.BRACE | wglob.DOTGLOB | wglob.FORCEUNIX | wglob.IGNORECASE
TOP = 20


def _gaps(service: MemoryService, entries: list, days: int) -> tuple[list[dict], dict]:
    """近 days 天有提交（只改免记录文件的不算、超大提交不算）的模块里，同期一条功能记录都没写的。"""
    since = (date.today() - timedelta(days=days)).isoformat()
    exempt = [str(p) for p in service.config.get("gate.record_exempt") or []]
    registry = service.registry
    commits: Counter = Counter()
    files: dict[str, set] = defaultdict(set)
    try:
        history = service.vcs.commits_since(since)
    except Exception:  # noqa: BLE001
        history = []
    for _, changed in history:
        if not 0 < len(changed) <= BULK_COMMIT:
            continue
        touched = set()
        for rel in changed:
            if rel.startswith(".memory/") or any(wglob.globmatch(rel, p, flags=_GLOB) for p in exempt):
                continue
            try:
                match = registry.module_for_path(rel)
            except RegistryError:
                continue
            if match is None or registry.modules.get(match.module_id) is None:
                continue
            if registry.modules[match.module_id].deprecated:
                continue
            touched.add(match.module_id)
            files[match.module_id].add(rel)
        commits.update(touched)
    recorded = Counter(e.module for e in entries if e.kind == "feature" and e.note_date >= since)
    gaps = [{"module": m, "commits": n, "files": len(files[m])} for m, n in commits.most_common() if not recorded[m]]
    coverage = {"active": len(commits), "recorded": sum(1 for m in commits if recorded[m]), "since": since}
    return gaps, coverage


def _broken(entries: list) -> list[dict]:
    """断链：更正没有写替代对象（读的人不知道它推翻了哪条，旧结论仍然现行）；同议题一正一反却没有替代关系。"""
    visible = [e for e in entries if e.status in VISIBLE_STATUSES]
    hidden = {old for e in entries for old in e.replaces()}
    rows = [{"module": e.module, "entity": e.entity, "ids": [e.id], "reason": "更正没有写替代哪条（supersedes）"}
            for e in visible if e.kind == "correction" and not e.supersedes and e.id not in hidden]
    for pair in _contradictions([e for e in visible if e.id not in hidden]):
        rows.append({"module": pair["module"], "entity": pair["entity"], "ids": [pair["old"], pair["new"]],
                     "reason": f"同议题一正一反、正文相似度 {pair['overlap']}，却没有替代关系"})
    return rows


def build_memmap(root: Path, days: int = GAP_DAYS) -> dict:
    service = MemoryService(root)
    try:
        entries = service.index.entries()
        model = build_map(entries)
        live = {n["id"] for m in model["modules"] for t in m["topics"] for n in t["nodes"] if n["current"]}
        stale = service.index.check_anchors([e for e in entries if e.id in live])
        gaps, coverage = _gaps(service, entries, days)
        title = service.config.get("project.name") or service.root.name
    finally:
        service.close()
    by_id = {e.id: e for e in entries}
    unresolved = [{"module": m["module"], "entity": t["entity"], "ids": [t["unresolved"]]}
                  for m in model["modules"] for t in m["topics"] if t["unresolved"]]
    stale_rows = [{"module": by_id[i].module, "entity": by_id[i].entity, "ids": [i], "reason": "；".join(p)}
                  for i, p in sorted(stale.items())]
    for m in model["modules"]:
        for t in m["topics"]:
            for n in t["nodes"]:
                if n["id"] in stale:
                    n["stale"] = stale[n["id"]]
    broken = _broken(entries)
    model.update({
        "title": title,
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "days": days,
        "summary": {
            "modules": len(model["modules"]),
            "current": model["current"],
            "total": model["total"],
            "coverage": coverage,
            "gaps": len(gaps),
            "broken": len(broken),
            "unresolved": len(unresolved),
            "stale": len(stale_rows),
        },
        "checks": {"gaps": gaps, "broken": broken, "unresolved": unresolved, "stale": stale_rows},
    })
    return model


def render_summary(model: dict) -> str:
    s = model["summary"]
    cov = s["coverage"]
    rate = f"{cov['recorded']}/{cov['active']}（{cov['recorded'] / cov['active']:.0%}）" if cov["active"] else "近期没有提交"
    lines = [
        f"记忆图：{s['modules']} 个模块，现行 {s['current']} 条（含历史共 {s['total']} 条）",
        f"功能记录覆盖：近 {model['days']} 天有提交的模块里写了功能记录的 {rate}",
        f"漏记 {s['gaps']} 个模块 · 断链 {s['broken']} 处 · 悬而未决 {s['unresolved']} 个议题 · 过期 {s['stale']} 条",
        "（这些衡量存储结构是否完整，不衡量对 AI 是否有用；后者看 pmem report 与 pmem bench）",
    ]
    checks = model["checks"]
    sections = (
        ("漏记（近期有提交、同期没有功能记录）", [f"{g['module']}：{g['commits']} 次提交、{g['files']} 个文件"
                                         for g in checks["gaps"]],
         "改这些模块的人补一条 feature（需求来源、必须保持的行为）"),
        ("断链", [f"{r['module']} / {r['entity']}：{'、'.join(r['ids'])}，{r['reason']}" for r in checks["broken"]],
          ("更正推翻了某条旧记忆就补上替代关系（新写一条 supersedes 两者）；只是纠正代码里的旧行为、没有对应的旧记忆，可以不管；"
           "一正一反的按 pmem health 的提示处理")),
        ("悬而未决（只有排除项、后面没有落地）", [f"{r['module']} / {r['entity']}：{r['ids'][0]}" for r in checks["unresolved"]],
         "后来找到了做法就写 conclusion/decision/feature；确实还没解决的可以不管"),
        ("过期（关联代码改过、未核对）", [f"{r['module']} / {r['entity']}：{r['ids'][0]}，{r['reason']}"
                                for r in checks["stale"]],
         "核对后仍成立 pmem confirm <id>，不成立写 correction 替代"),
    )
    for title, rows, action in sections:
        if not rows:
            continue
        lines += ["", f"【{title}】", *[f"  {r}" for r in rows[:TOP]]]
        if len(rows) > TOP:
            lines.append(f"  ……另有 {len(rows) - TOP} 条，见图上自检")
        lines.append(f"  → {action}")
    return "\n".join(lines)
