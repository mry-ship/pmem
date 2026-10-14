from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pmem import __version__

HOOK_EVENTS = ("prompt", "pre-tool", "before-mcp", "after-mcp", "edited", "compact", "stop")


def build_parser() -> argparse.ArgumentParser:
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

    p = sub.add_parser("list", help="列出模块与记忆数量")
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
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
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
    if args.command in ("search", "list"):
        from pmem.service import MemoryService

        service = MemoryService(_project_root(args.root))
        try:
            if args.command == "list":
                _print_json(service.list_modules())
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
