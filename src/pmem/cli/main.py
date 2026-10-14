from __future__ import annotations

import argparse

from pmem import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pmem", description="面向项目与团队的 AI 研发记忆系统")
    parser.add_argument("--version", action="version", version=f"pmem {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
