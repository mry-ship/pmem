"""冒烟测试：像 Cursor 一样通过 stdio 启动 `pmem serve`，列出工具并调用 list_modules。"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main() -> None:
    params = StdioServerParameters(command="pmem", args=["serve", "--root", str(ROOT)])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        print("工具：", [t.name for t in tools.tools])
        result = await session.call_tool("list_modules", {})
        print(result.content[0].text[:300])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
