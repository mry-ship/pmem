from __future__ import annotations

import sys
from pathlib import Path

from pmem import __version__

HOOK_EVENTS = ("prompt", "pre-tool", "before-mcp", "after-mcp", "edited", "compact", "stop")


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(prog="pmem", description="面向项目与团队的 AI 研发记忆系统")
    parser.add_argument("--version", action="version", version=f"pmem {__version__}")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("init", help="在项目中接入 pmem（生成 .memory/ 与 .cursor/ 配置）")
    p.add_argument("--root", default=".")
    p.add_argument("--type", choices=("game", "app", "backend", "generic"), default=None, help="项目类型，决定默认大类")
    p.add_argument("--gate", choices=("off", "warn", "block"), default="warn", help="闸门力度")

    p = sub.add_parser("scan", help="输出目录概览，供 Agent 划分模块")
    p.add_argument("--root", default=".")
    p.add_argument("--depth", type=int, default=4)

    p = sub.add_parser("doctor", help="自检：配置、模块覆盖率、Cursor 接入状态")
    p.add_argument("--root", default=".")

    p = sub.add_parser("serve", help="启动 MCP 服务（由 Cursor 调用）")
    p.add_argument("--root", default=None)

    p = sub.add_parser("hook", help="处理 Cursor Hook 事件（由 Cursor 调用）")
    p.add_argument("event", choices=HOOK_EVENTS)

    p = sub.add_parser("search", help="命令行检索记忆")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--module", default="")
    p.add_argument("--path", default="")
    p.add_argument("--entity", default="")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--root", default=".")

    p = sub.add_parser("record", help="命令行写入一条记忆（规则与 MCP 的 record_memory 相同）")
    p.add_argument("--module", required=True)
    p.add_argument("--entity", required=True)
    p.add_argument("--kind", required=True, choices=("conclusion", "exclusion", "correction", "risk", "decision"))
    body = p.add_mutually_exclusive_group(required=True)
    body.add_argument("--content", help="正文；传 - 表示从标准输入读取")
    body.add_argument("--content-file", help="从 UTF-8 文件读取正文（正文含引号或较长时推荐）")
    p.add_argument("--supersedes", action="append", default=[])
    p.add_argument("--anchor", action="append", default=[])
    p.add_argument("--root", default=".")

    p = sub.add_parser("list", help="列出模块与记忆数量")
    p.add_argument("--root", default=".")

    p = sub.add_parser("import", help="从参考实现的 LanceDB 记忆库导入（只读源库，重复导入不会重复写）")
    p.add_argument("--lancedb", required=True, help="LanceDB 目录")
    p.add_argument("--catalog", default=None, help="参考实现的 modules.yaml，用于填充大类与议题")
    p.add_argument("--author", default="imported", help="源库没有作者信息，统一记为此作者")
    p.add_argument("--guess-kind", action="store_true", help="按正文开头的关键词推断类型（默认全部记为 conclusion）")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--root", default=".")

    p = sub.add_parser("reindex", help="清空本机索引缓存并重建（换了嵌入模型或检索异常时用）")
    p.add_argument("--root", default=".")

    p = sub.add_parser("report", help="本机收益报告：检索命中、避坑、跨人复用、记忆采用率等")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--json", action="store_true")
    p.add_argument("--root", default=".")

    p = sub.add_parser("bench", help="对照实验：同一任务有/无记忆各跑一遍（需要 Cursor SDK 与 CURSOR_API_KEY）")
    p.add_argument("cases", nargs="?", default="bench/cases.yaml")
    p.add_argument("--arms", default="on,off", help="要跑的组，逗号分隔：on,off")
    p.add_argument("--repeats", type=int, default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--only", action="append", default=[], help="只跑指定用例 id，可重复")
    p.add_argument("--out", default="bench-results")
    p.add_argument("--dry-run", action="store_true", help="不调用 Agent，只验证起始提交上验收确实失败")
    p.add_argument("--root", default=".")
    return parser


def _project_root(raw: str) -> Path:
    from pmem.core.config import find_root

    root = find_root(raw)
    if root is None:
        print(f"{Path(raw).resolve()} 不在 pmem 项目中，请先运行 pmem init", file=sys.stderr)
        raise SystemExit(2)
    return root


def _print_json(data: dict) -> None:
    import json

    print(json.dumps(data, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args_list = sys.argv[1:] if argv is None else argv
    if len(args_list) == 2 and args_list[0] == "hook" and args_list[1] in HOOK_EVENTS:
        from pmem.cli.hook_cmd import run_hook

        return run_hook(args_list[1])
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "hook":
        from pmem.cli.hook_cmd import run_hook

        return run_hook(args.event)
    if args.command == "serve":
        from pmem.server.app import serve

        serve(args.root)
        return 0
    if args.command == "init":
        from pmem.cli.init_cmd import run_init

        return run_init(Path(args.root), args.type, args.gate)
    if args.command == "scan":
        from pmem.scan.lite import run_scan

        return run_scan(Path(args.root), args.depth)
    if args.command == "doctor":
        from pmem.cli.doctor_cmd import run_doctor

        return run_doctor(_project_root(args.root))
    if args.command == "import":
        from pmem.cli.import_cmd import run_import

        return run_import(_project_root(args.root), Path(args.lancedb), Path(args.catalog) if args.catalog else None,
                          args.author, args.dry_run, args.guess_kind)
    if args.command == "reindex":
        from pmem.cli.reindex_cmd import run_reindex

        return run_reindex(_project_root(args.root))
    if args.command == "report":
        from pmem.metrics.report import run_report

        return run_report(_project_root(args.root), args.days, args.json)
    if args.command == "bench":
        from pmem.bench.runner import dry_run_executor, run_bench

        root = _project_root(args.root)
        arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
        records = run_bench(
            root, root / args.cases, root / args.out, arms=arms, repeats=1 if args.dry_run else args.repeats,
            model=args.model, executor=dry_run_executor if args.dry_run else None, only=args.only or None,
        )
        if args.dry_run:
            bad = sorted({r.case for r in records if r.passed})
            print("用例有效：起始提交上验收均失败" if not bad else f"这些用例在起始提交上已能通过，需要调整：{'、'.join(bad)}")
            return 1 if bad else 0
        print(f"结果见 {root / args.out / 'summary.md'}")
        return 0
    if args.command in ("search", "list", "record"):
        from pmem.service import MemoryService

        service = MemoryService(_project_root(args.root))
        try:
            if args.command == "list":
                _print_json(service.list_modules())
            elif args.command == "record":
                if args.content_file:
                    content = Path(args.content_file).read_text(encoding="utf-8-sig")
                else:
                    content = sys.stdin.read() if args.content == "-" else args.content
                result = service.record(args.module, args.entity, args.kind, content, args.supersedes, args.anchor)
                _print_json(result)
                return 0 if result.get("ok") else 1
            else:
                _print_json(service.search(args.module or None, args.path or None, args.entity or None,
                                           args.query or None, args.limit))
        finally:
            service.close()
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
