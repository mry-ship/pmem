from __future__ import annotations

import sys
from pathlib import Path

from pmem import __version__

HOOK_EVENTS = ("session", "prompt", "pre-tool", "before-mcp", "after-mcp", "edited", "post-tool", "compact", "stop")
AGENTS = ("cursor", "claude", "codex")
BRIEF_HELP = "输出精简文本（每条一行）而不是 JSON，免得再用管道筛选"


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(prog="pmem", description="面向项目与团队的 AI 研发记忆系统")
    parser.add_argument("--version", action="version", version=f"pmem {__version__}")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("init", help="在项目中接入 pmem（生成 .memory/ 与各 Agent 的配置）")
    p.add_argument("--root", default=".")
    p.add_argument("--type", choices=("game", "app", "backend", "generic"), default=None,
                   help="项目类型，决定默认大类；只在首次生成 config.yaml / modules.yaml 时生效")
    p.add_argument("--gate", choices=("off", "warn", "block"), default=None,
                   help="闸门力度，默认 block；只在首次生成 config.yaml 时生效")
    p.add_argument("--agents", default="auto",
                   help="要接入的 Agent，逗号分隔：cursor,claude,codex 或 all；"
                        "auto = Cursor 加上项目里已有配置的（.claude/、CLAUDE.md、.codex/、AGENTS.md）")

    p = sub.add_parser("scan", help="输出目录概览，供 Agent 划分模块")
    p.add_argument("--root", default=".")
    p.add_argument("--depth", type=int, default=4)

    p = sub.add_parser("sync", help="重新扫描代码目录：列出新模块候选、要追加的路径、第三方目录和冷候选转正（默认只预览）")
    p.add_argument("--apply", action="store_true", help="写入 modules.yaml（只追加，不改已有模块名）")
    p.add_argument("--root", default=".")

    p = sub.add_parser("doctor", help="自检：配置、模块覆盖率、Cursor 接入状态")
    p.add_argument("--root", default=".")

    p = sub.add_parser("serve", help="启动 MCP 服务（由 Cursor 调用；带看门狗，服务崩溃或卡死时自动重启）")
    p.add_argument("--root", default=None)
    p.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)

    p = sub.add_parser("hook", help="处理 Agent 的 Hook 事件（由 Cursor / Claude Code / Codex 调用）")
    p.add_argument("event", choices=HOOK_EVENTS)
    p.add_argument("--agent", choices=AGENTS, default="cursor")

    p = sub.add_parser("search", help="命令行检索记忆")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--module", default="")
    p.add_argument("--path", default="")
    p.add_argument("--entity", default="")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--as-of", default="", help="只看这一天（YYYY-MM-DD）有效的记忆")
    p.add_argument("--brief", action="store_true", help=BRIEF_HELP)
    p.add_argument("--root", default=".")

    p = sub.add_parser("confirm", help="确认记忆仍然成立（核对过关联代码后），核对日期记为今天")
    p.add_argument("ids", nargs="+")
    p.add_argument("--root", default=".")

    p = sub.add_parser("graph", help="模块的记忆图谱：议题、时间线与相关模块")
    p.add_argument("--module", required=True)
    p.add_argument("--entity", default="")
    p.add_argument("--brief", action="store_true", help=BRIEF_HELP)
    p.add_argument("--root", default=".")

    p = sub.add_parser("terms", help="记忆里的高频词，供 Agent 整理同义叫法（pmem-normalize 技能）")
    p.add_argument("--module", default="")
    p.add_argument("--top", type=int, default=300)
    p.add_argument("--min", type=int, default=2, help="至少出现在几条记忆里")
    p.add_argument("--root", default=".")

    p = sub.add_parser("anchors", help="从记忆正文里提到的文件名、类名.成员 补全关联代码；代码搬家后用 --rename 改写（默认只预览）")
    p.add_argument("--module", default="")
    p.add_argument("--rename", action="append", default=[], metavar="旧路径=新路径",
                   help="代码文件或目录改名、函数搬到别的文件后，改写所有记忆的关联代码；可写多次，也可写 路径#函数名")
    p.add_argument("--apply", action="store_true", help="写回记忆文件")
    p.add_argument("--root", default=".")

    p = sub.add_parser("format", help="把记忆正文里过长的行按句号、分号和编号断开，方便直接阅读（默认只预览）")
    p.add_argument("--module", default="")
    p.add_argument("--apply", action="store_true", help="写回记忆文件")
    p.add_argument("--root", default=".")

    p = sub.add_parser("record", help="命令行写入一条记忆（规则与 MCP 的 record_memory 相同）")
    p.add_argument("--module", required=True)
    p.add_argument("--entity", required=True)
    p.add_argument("--kind", required=True, choices=("conclusion", "exclusion", "correction", "risk", "decision"))
    body = p.add_mutually_exclusive_group(required=True)
    body.add_argument("--content", help="正文；传 - 表示从标准输入读取")
    body.add_argument("--content-file", help="从 UTF-8 文件读取正文（正文含引号或较长时推荐）")
    # extend + nargs：一个参数后可以跟多个值（--alias 闪退 崩溃），也可以重复写；
    # 默认 None 表示没传，带 --draft-id 覆盖时沿用原值；只写参数名不跟值表示清空
    keep = "；带 --draft-id 时不写则沿用原值，只写参数名不跟值表示清空"
    p.add_argument("--supersedes", action="extend", nargs="*", default=None, help="被替代的旧记忆 id" + keep)
    p.add_argument("--anchor", action="extend", nargs="*", default=None, help="关联代码，写成 路径#函数名" + keep)
    p.add_argument("--alias", action="extend", nargs="*", default=None,
                   help="常用的其他叫法，如 --alias 闪退 崩溃；含空格的叫法要加引号" + keep)
    p.add_argument("--draft-id", default="", help="上次写入返回的 draft_id：同一任务再次写入时覆盖那一条")
    p.add_argument("--seed", action="store_true", help="写成种子记忆（pmem-seed 技能用），负责人确认后才转正")
    p.add_argument("--brief", action="store_true", help=BRIEF_HELP)
    p.add_argument("--root", default=".")

    p = sub.add_parser("list", help="列出模块与记忆数量")
    p.add_argument("--root", default=".")

    p = sub.add_parser("archive", help="归档记忆：不再出现在检索里，文件保留可追溯（负责人用）")
    p.add_argument("ids", nargs="+")
    p.add_argument("--restore", action="store_true", help="撤销归档，恢复到归档前的状态")
    p.add_argument("--root", default=".")

    p = sub.add_parser("seed", help="种子记忆：候选模块、待确认列表、转正与退回（配合 pmem-seed 技能）")
    p.add_argument("ids", nargs="*")
    p.add_argument("--module", default="")
    p.add_argument("--plan", action="store_true", help="按改动热度列出值得先补种子记忆的模块")
    p.add_argument("--top", type=int, default=None, help="配合 --plan：列出前几个模块，默认 10")
    action = p.add_mutually_exclusive_group()
    action.add_argument("--accept", action="store_true", help="确认：转为正式记忆")
    action.add_argument("--reject", action="store_true", help="退回：标为归档")
    p.add_argument("--all", action="store_true", help="配合 --accept：确认全部待确认的种子记忆")
    p.add_argument("--json", action="store_true")
    p.add_argument("--root", default=".")

    p = sub.add_parser("migrate", help="模块改名、合并、拆分、废弃，并把记忆搬到新模块下（默认只预览）")
    msub = p.add_subparsers(dest="action", required=True)
    for name, help_text, args in (
        ("rename", "改名：旧名成为别名", ("old", "new")),
        ("merge", "合并：source 并入 target（source 可以是未登记模块）", ("source", "target")),
        ("split", "拆分：把模块的部分路径或议题分给新模块（或已有模块），记忆按关联代码或议题跟着走", ("module",)),
        ("deprecate", "废弃：旧记忆照常可查，拒绝新写入", ("module",)),
        ("move", "搬记忆：把归错模块的记忆按 id 搬到另一个模块", ()),
        ("tidy", "把还在旧模块名下的记忆搬到新名下", ()),
    ):
        mp = msub.add_parser(name, help=help_text)
        for arg in args:
            mp.add_argument(arg)
        if name == "move":
            mp.add_argument("ids", nargs="+", metavar="记忆id")
            mp.add_argument("--to", required=True, metavar="模块", help="搬到哪个模块")
        if name == "deprecate":
            mp.add_argument("--undo", action="store_true", help="撤销废弃")
        if name == "merge":
            mp.add_argument("--alias", action="store_true",
                            help="source 是未登记模块时，把它登记为 target 的别名（以后还会这样写时用；笔误不用加）")
        if name == "split":
            mp.add_argument("--to", action="append", default=[], required=True, metavar="模块=路径或议题[,...]",
                            help="分出去的部分，可写多次，如 --to activity.MergeEvent=Assets/Merge/Event/**")
            mp.add_argument("--by", choices=("path", "entity"), default="path", help="按路径（默认）还是按议题拆")
            mp.add_argument("--assign", action="append", default=[], metavar="记忆id=模块",
                            help="手动指定某条记忆的去向，可写多次")
        mp.add_argument("--apply", action="store_true", help="执行；不加只预览")
        mp.add_argument("--root", default=".")

    p = sub.add_parser("health", help="健康报告：未登记与重复模块、检索落空、过时记忆、被拒写入等（负责人定期看）")
    p.add_argument("--days", type=int, default=60)
    p.add_argument("--json", action="store_true")
    p.add_argument("--root", default=".")

    p = sub.add_parser("wiki", help="从记忆生成可浏览的模块 Wiki（Markdown，每个模块一页）")
    p.add_argument("--out", default=None, help="输出目录，默认 .memory/wiki")
    p.add_argument("--root", default=".")

    p = sub.add_parser("compact", help="列出积累了多条零碎记忆的议题；指定议题时输出全部正文，供 Agent 合并成一条")
    p.add_argument("--module", default="")
    p.add_argument("--entity", default="")
    p.add_argument("--min", type=int, default=5, help="一个议题至少积累多少条才列出")
    p.add_argument("--json", action="store_true")
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
    # Hook 每次工具调用都会触发，跳过 argparse 与 stdout 重配置以减少启动耗时
    if len(args_list) >= 2 and args_list[0] == "hook" and args_list[1] in HOOK_EVENTS:
        rest = args_list[2:]
        if not rest:
            from pmem.cli.hook_cmd import run_hook

            return run_hook(args_list[1])
        if len(rest) == 2 and rest[0] == "--agent" and rest[1] in AGENTS:
            from pmem.cli.hook_cmd import run_hook

            return run_hook(args_list[1], rest[1])
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in SERVICE_COMMANDS:
        return _run_service(args)
    handler = COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)


# ---- 各子命令；依赖在用到时才导入，保持启动快 ----

def _hook(args) -> int:
    from pmem.cli.hook_cmd import run_hook

    return run_hook(args.event, args.agent)


def _serve(args) -> int:
    from pmem.server.app import serve

    serve(args.root, args.worker)
    return 0


def _init(args) -> int:
    from pmem.cli.init_cmd import run_init

    return run_init(Path(args.root), args.type, args.gate, args.agents)


def _scan(args) -> int:
    from pmem.scan.lite import run_scan

    return run_scan(Path(args.root), args.depth)


def _sync(args) -> int:
    from pmem.cli.sync_cmd import run_sync

    return run_sync(_project_root(args.root), args.apply)


def _doctor(args) -> int:
    from pmem.cli.doctor_cmd import run_doctor

    return run_doctor(_project_root(args.root))


def _import(args) -> int:
    from pmem.cli.import_cmd import run_import

    return run_import(_project_root(args.root), Path(args.lancedb), Path(args.catalog) if args.catalog else None,
                      args.author, args.dry_run, args.guess_kind)


def _compact(args) -> int:
    from pmem.cli.compact_cmd import run_compact

    return run_compact(_project_root(args.root), args.module, args.entity, args.min, args.json)


def _reindex(args) -> int:
    from pmem.cli.reindex_cmd import run_reindex

    return run_reindex(_project_root(args.root))


def _report(args) -> int:
    from pmem.metrics.report import run_report

    return run_report(_project_root(args.root), args.days, args.json)


def _bench(args) -> int:
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


def _anchors(args) -> int:
    from pmem.cli.anchors_cmd import run_anchors, run_rename

    if args.rename:
        return run_rename(_project_root(args.root), args.rename, args.apply)
    return run_anchors(_project_root(args.root), args.module or None, args.apply)


def _format(args) -> int:
    from pmem.cli.format_cmd import run_format

    return run_format(_project_root(args.root), args.module or None, args.apply)


def _wiki(args) -> int:
    from pmem.cli.wiki_cmd import run_wiki

    return run_wiki(_project_root(args.root), args.out)


def _seed(args) -> int:
    from pmem.cli.seed_cmd import run_seed

    return run_seed(_project_root(args.root), args.ids, args.module, args.plan, args.top, args.accept, args.reject,
                    args.all, args.json)


def _migrate(args) -> int:
    from pmem.cli.migrate_cmd import run_migrate

    first = getattr(args, "old", None) or getattr(args, "source", None) or getattr(args, "module", None)
    second = getattr(args, "new", None) or getattr(args, "target", None)
    targets = getattr(args, "to", None)
    if args.action == "move":
        second, targets = targets, None
    return run_migrate(_project_root(args.root), args.action, first, second, args.apply,
                       undo=getattr(args, "undo", False), targets=targets,
                       by=getattr(args, "by", "path"), assigns=getattr(args, "assign", None),
                       ids=getattr(args, "ids", None), keep_alias=getattr(args, "alias", False))


def _health(args) -> int:
    from pmem.metrics.health import run_health

    return run_health(_project_root(args.root), args.days, args.json)


COMMANDS = {
    "hook": _hook,
    "serve": _serve,
    "init": _init,
    "scan": _scan,
    "sync": _sync,
    "doctor": _doctor,
    "import": _import,
    "compact": _compact,
    "reindex": _reindex,
    "report": _report,
    "bench": _bench,
    "anchors": _anchors,
    "format": _format,
    "wiki": _wiki,
    "seed": _seed,
    "migrate": _migrate,
    "health": _health,
}


# ---- 直接调用 MemoryService、输出 JSON 的子命令 ----

def _record_content(args) -> str:
    if args.content_file:
        return Path(args.content_file).read_text(encoding="utf-8-sig")
    if args.content != "-":
        return args.content
    # 中文 Windows 上 sys.stdin 按 GBK 解码，管道传入的 UTF-8 会变成乱码
    raw = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
    return raw.decode("utf-8-sig", errors="replace")


SERVICE_COMMANDS = {
    "list": lambda s, a: s.list_modules(),
    "record": lambda s, a: s.record(a.module, a.entity, a.kind, _record_content(a), a.supersedes, a.anchor,
                                    a.draft_id or None, aliases=a.alias, status="seed" if a.seed else None),
    "archive": lambda s, a: s.change_status(a.ids, "restore" if a.restore else "archive"),
    "confirm": lambda s, a: s.confirm(a.ids),
    "graph": lambda s, a: s.graph(a.module, a.entity or None),
    "terms": lambda s, a: s.terms(a.module or None, a.top, a.min),
    "search": lambda s, a: s.search(a.module or None, a.path or None, a.entity or None, a.query or None, a.limit,
                                    as_of=a.as_of or None),
}


def _run_service(args) -> int:
    from pmem.service import MemoryService

    service = MemoryService(_project_root(args.root))
    try:
        result = SERVICE_COMMANDS[args.command](service, args)
        if getattr(args, "brief", False):
            from pmem.cli.brief import render_brief

            print(render_brief(args.command, result))
        else:
            _print_json(result)
    finally:
        service.close()
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
