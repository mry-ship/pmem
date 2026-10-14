"""最小 MCP 服务：回显参数，用于验证 preToolUse 的 updated_input 是否作用于 MCP 工具。"""
from __future__ import annotations

import json
import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pmem-spike")


@mcp.tool()
def echo(text: str, injected: str = "") -> str:
    """原样返回 text 与 injected，并附上服务进程的工作目录。injected 为空说明 Hook 注入未生效。"""
    return json.dumps({"text": text, "injected": injected, "cwd": os.getcwd()}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
