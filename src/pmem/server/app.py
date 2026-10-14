from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from pmem.core.config import find_root

INSTRUCTIONS = (
    "项目研发记忆：按模块（category.Module）沉淀根因、排除项、决定与风险。"
    "改代码前用 search_memory 按文件路径或模块查一次；得出值得留存的结论后用 record_memory 记一条。"
)


def _dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def resolve_root(raw: str | None) -> Path | None:
    """优先用 --root（忽略未被替换的 ${...} 变量），否则从工作目录向上找 .memory/config.yaml。"""
    for candidate in (raw, os.environ.get("PMEM_ROOT"), os.getcwd()):
        if candidate and "${" not in candidate:
            root = find_root(candidate)
            if root is not None:
                return root
    return None


def build_server(root: Path | None) -> MCPServer:
    from pmem.service import MemoryService

    service = MemoryService(root, source="mcp") if root is not None else None
    missing = {"ok": False, "error": "当前工作区还没有接入 pmem：请在项目根目录运行 pmem init"}
    server = MCPServer("pmem", instructions=INSTRUCTIONS)

    @server.tool()
    def search_memory(
        module: str = "",
        path: str = "",
        entity: str = "",
        query: str = "",
        limit: int = 5,
        source_conversation: str = "",
    ) -> str:
        """检索项目研发记忆。改代码前先查：传 path（要改的文件路径）或 module（category.Module）；
        entity 为模块内议题（如 Reward、Config），可省略；query 为关键词或问题描述。
        都不确定时只传 query 做全局检索。返回按相关度排序的记忆，stale=true 表示关联代码已变。
        source_conversation 由系统自动填写，无需传。"""
        if service is None:
            return _dump(missing)
        return _dump(service.search(module or None, path or None, entity or None, query or None, limit,
                                    source_conversation or None))

    @server.tool()
    def record_memory(
        module: str,
        entity: str,
        kind: str,
        content: str,
        supersedes: list[str] | None = None,
        anchors: list[str] | None = None,
        draft_id: str = "",
        source_conversation: str = "",
    ) -> str:
        """记录一条研发记忆。只在三个时机写：根因确认、方向被排除或方案确定、改完并验证通过。
        module：category.Module；entity：模块内议题；kind：conclusion / exclusion / correction / risk / decision；
        content：自包含的结论（为什么、证据、影响范围），不要写“改了哪个方法”这类版本库已有的信息。
        推翻旧结论时在 supersedes 写旧记忆 id；anchors 写相关代码位置（相对路径#符号）。
        同一任务对同一模块再次写入时，带上次返回的 draft_id 覆盖，避免重复。"""
        if service is None:
            return _dump(missing)
        return _dump(
            service.record(module, entity, kind, content, supersedes, anchors, draft_id or None,
                           source_conversation or None)
        )

    @server.tool()
    def list_modules(category: str = "") -> str:
        """列出项目的模块与记忆数量、常用议题。不确定模块名时先调用它。"""
        if service is None:
            return _dump(missing)
        result = service.list_modules(category or None)
        result["project_root"] = str(service.root)
        return _dump(result)

    return server


def serve(raw_root: str | None) -> None:
    build_server(resolve_root(raw_root)).run("stdio")
