"""真实检索评测：题目来自本仓库的检索记录，答案是同一对话里 Agent 回复确实用到的记忆。

  抽题：uv run python scripts/eval_real_queries.py build
        读本机事件日志和采用记录（cites.json），写 tests/fixtures/eval/real_queries.yaml
  评测：uv run python scripts/eval_real_queries.py run [--keyword] [--root 记忆库所在目录]
        按每道题当天的记忆库状态（as_of）重放检索，统计前 1 / 前 3 命中率和 MRR

答案只来自当时返回过的记忆，偏向当时的排序；用来比较版本之间排序的先后，不是绝对召回率。
脚本只用 MemoryService.index.search 的公共参数，可以拷到旧版本的工作树里用同一份题目重放。
"""
from __future__ import annotations

import argparse
import inspect
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "eval"
DATASET = EVAL_DIR / "real_queries.yaml"
SETS = {"real": DATASET, "path": EVAL_DIR / "path_queries.yaml", "alias": EVAL_DIR / "alias_queries.yaml"}
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _ulid_ms(ulid: str) -> int:
    """旧版本没有 pmem.core.ids.ulid_ms，这里自带一份。"""
    ms = 0
    for ch in ulid[:10].upper():
        ms = ms * 32 + CROCKFORD.index(ch)
    return ms


def _repair(query: str) -> str | None:
    """终端检索的中文参数在 Windows 上可能被按 GBK 误解码（如“绉嶅瓙”），能还原就还原，还原不了的丢弃。"""
    try:
        fixed = query.encode("gbk").decode("utf-8")
    except UnicodeError:
        fixed = query
    fixed = " ".join(fixed.split()).rstrip("},")
    return None if "\ufffd" in fixed or "?" in fixed or not fixed else fixed


def build(root: Path, out: Path) -> None:
    from pmem.core.config import Config
    from pmem.metrics.events import read_events
    from pmem.metrics.report import _link_cli_searches

    config = Config.load(root)
    events = list(read_events(config.cache_dir, 0))
    _link_cli_searches(events)
    cites = json.loads((config.cache_dir / "cites.json").read_text(encoding="utf-8"))
    cited = {conv: set(v.get("cited") or []) for conv, v in cites.items()}
    existing = {p.stem for p in config.entries_dir.glob("*/*.md")}
    cases: dict[tuple, dict] = {}
    for e in sorted(events, key=lambda e: e["ts"]):
        if e["type"] != "search" or not e.get("ok") or not e.get("query") or not e.get("module") or not e.get("conv"):
            continue
        expect = [i for i in e.get("ids") or [] if i in cited.get(e["conv"], set()) and i in existing]
        if not expect:
            continue
        query = _repair(e["query"])
        if query is None:
            continue
        key = (e["module"], query)
        case = cases.setdefault(key, {"module": key[0], "q": key[1], "ts": round(e["ts"], 3),
                                      "as_of": datetime.fromtimestamp(e["ts"]).date().isoformat(), "expect": []})
        case["expect"] += [i for i in expect if i not in case["expect"]]
    rows = sorted(cases.values(), key=lambda c: (c["as_of"], c["module"], c["q"]))
    header = ("# 由 scripts/eval_real_queries.py build 生成：本仓库真实检索，答案是同一对话里 Agent 回复确实用到的记忆。\n"
              "# 重新生成会覆盖；ts 是检索时刻，评测时按那天的记忆库状态（as_of）重放，并去掉检索之后才写下的记忆。\n")
    out.write_text(header + yaml.safe_dump({"queries": rows}, allow_unicode=True, sort_keys=False, width=200),
                   encoding="utf-8")
    print(f"写入 {len(rows)} 道题：{out}")


def build_known(root: Path) -> None:
    """按现行记忆自动出题，不依赖检索记录：
    path：按文件检索（只传路径），答案是锚点在这个文件上的教训；
    alias：查询词是记忆的一个别名，且这个叫法不在标题和正文里出现，考同义叫法能不能搜到。"""
    from pmem.service import MemoryService

    service = MemoryService(root)
    try:
        entries = [e for e in service.index.visible(None) if e.kind not in ("feature", "plan")]
    finally:
        service.close()
    by_file: dict[tuple, list[str]] = {}
    aliases = []
    for e in entries:
        for anchor in e.anchors or []:
            file = anchor.split("#", 1)[0]
            if (root / file).is_file():
                ids = by_file.setdefault((e.module, file), [])
                if e.id not in ids:
                    ids.append(e.id)
        text = f"{e.summary or ''}\n{e.content}".lower()
        fresh = [a for a in e.aliases or [] if a.strip() and a.lower() not in text]
        if fresh:
            aliases.append({"module": e.module, "q": fresh[0], "expect": [e.id]})
    paths = [{"module": m, "path": f, "expect": ids} for (m, f), ids in sorted(by_file.items())]
    for name, rows in (("path", paths), ("alias", aliases)):
        header = f"# 由 scripts/eval_real_queries.py build-known 按现行记忆生成（{name}），重新生成会覆盖。\n"
        SETS[name].write_text(header + yaml.safe_dump({"queries": rows}, allow_unicode=True, sort_keys=False,
                                                      width=200), encoding="utf-8")
        print(f"写入 {len(rows)} 道题：{SETS[name]}")


def run(root: Path, keyword: bool, dataset: Path = DATASET, ranks: bool = False) -> None:
    from pmem.service import MemoryService

    data = yaml.safe_load(dataset.read_text(encoding="utf-8"))
    service = MemoryService(root)
    index = service.index
    accepts = inspect.signature(index.search).parameters
    hit1 = hit3 = 0
    rr = 0.0
    skipped = 0
    started = time.perf_counter()
    misses = []
    current = {e.id for e in index.visible(None)}
    try:
        for case in data["queries"]:
            if "ts" in case:
                # as_of 只到天：同一天检索之后才写下的记忆（多是这次对话得出的新结论）不能算进当时的候选
                before = {e.id for e in index.visible(case["as_of"]) if _ulid_ms(e.id) / 1000 <= case["ts"]}
                kwargs = {"as_of": case["as_of"], "today": date.fromisoformat(case["as_of"])}
            else:
                before, kwargs = current, {}
            expect = [i for i in case["expect"] if i in before]
            if not expect:
                skipped += 1
                continue
            kwargs.update(limit=30, semantic=not keyword)
            if "feature_limit" in accepts:
                kwargs["feature_limit"] = 3
            # 旧版本没有 path 参数：路径只用来定位模块，和当时的行为一致
            if case.get("path") and "path" in accepts:
                kwargs["path"] = case["path"]
            result = index.search(case["module"], None, case.get("q"), **kwargs)
            ranked = [item["id"] for item in result.items if item["id"] in before][:5]
            ranked += [item["id"] for item in getattr(result, "features", []) if item["id"] in before]
            rank = next((n for n, i in enumerate(ranked, 1) if i in expect), None)
            if ranks:
                print(f"RANK\t{case['module']}\t{case.get('q') or case.get('path')}\t{rank or 0}\t{' '.join(ranked)}")
            hit1 += rank == 1
            hit3 += rank is not None and rank <= 3
            rr += 1 / rank if rank else 0
            if rank != 1:
                misses.append(f"{case['module']}「{case.get('q') or case.get('path')}」→ {rank or '未返回'}")
    finally:
        service.close()
    n = len(data["queries"]) - skipped
    print(f"{dataset.stem} {'仅关键词' if keyword else '语义 + 关键词'}：{n} 道题（{skipped} 道的答案当时不可见，跳过）"
          f" top1={hit1}/{n}（{hit1 / n:.0%}） top3={hit3}/{n}（{hit3 / n:.0%}） MRR={rr / n:.3f}"
          f" 耗时 {time.perf_counter() - started:.1f}s")
    print("  排名不在第一的前 10 道：" + "；".join(misses[:10]))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["build", "build-known", "run"])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--keyword", action="store_true", help="只用关键词，不加载语义模型")
    parser.add_argument("--set", choices=sorted(SETS), default="real", help="题目：real 真实检索、path 按文件、alias 换说法")
    parser.add_argument("--ranks", action="store_true", help="逐题输出排名和返回顺序，便于对比两个版本")
    parser.add_argument("--out", type=Path, default=DATASET)
    args = parser.parse_args()
    if args.action == "build":
        build(args.root.resolve(), args.out)
    elif args.action == "build-known":
        build_known(args.root.resolve())
    else:
        run(args.root.resolve(), args.keyword, SETS[args.set], args.ranks)


if __name__ == "__main__":
    main()
