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
    # 来源标记：Cursor 传给 Hook 的工具名不带服务名，闸门靠它区分别家记忆服务的同名工具
    return json.dumps({**data, "server": "pmem"}, ensure_ascii=False, separators=(",", ":"))


def resolve_root(raw: str | None) -> Path | None:
    """优先用 --root（忽略未被替换的 ${...} 变量），否则从工作目录向上找 .memory/config.yaml。"""
    for candidate in (raw, os.environ.get("PMEM_ROOT"), os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()):
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
        as_of: str = "",
        source_conversation: str = "",
    ) -> str:
        """检索项目研发记忆。改代码前先查：传 path（要改的文件路径）或 module（category.Module）；
        entity 为模块内议题（如 Reward、Config），可省略；query 为关键词或问题描述，会按项目同义词表自动展开。
        都不确定时只传 query 做全局检索。as_of（YYYY-MM-DD）只看那天有效的记忆，用于回答“当时的结论”。
        返回按相关度排序的记忆；stale=true 表示写下（或上次核对）后关联代码改过或已删除，用前先核对。
        source_conversation 由系统自动填写，无需传。"""
        if service is None:
            return _dump(missing)
        return _dump(service.search(module or None, path or None, entity or None, query or None, limit,
                                    source_conversation or None, as_of or None))

    @server.tool()
    def record_memory(
        module: str,
        entity: str,
        kind: str,
        content: str,
        supersedes: list[str] | None = None,
        anchors: list[str] | None = None,
        aliases: list[str] | None = None,
        draft_id: str = "",
        source_conversation: str = "",
    ) -> str:
        """记录一条研发记忆。只在三个时机写：根因确认、方向被排除或方案确定、改完并验证通过。
        module：category.Module；entity：模块内议题；kind：conclusion / exclusion / correction / risk / decision；
        content：自包含的结论（为什么、证据、影响范围），不要写“改了哪个方法”这类版本库已有的信息。
        aliases：现象和关键术语的其他常用叫法（如 ["闪退", "崩溃", "crash"]），以后换个说法也能搜到。
        推翻旧结论时在 supersedes 写旧记忆 id；anchors 写相关代码位置（相对路径#符号），不填时系统按本次对话改过的该模块文件补上。
        同一任务对同一模块再次写入时，带上次返回的 draft_id 覆盖，避免重复；覆盖时没填的 supersedes / anchors / aliases 沿用原值。
        返回的 similar 是同模块最相近的已有记忆：重复或被推翻时带 draft_id 重写并填 supersedes；hints 是写作提示。"""
        if service is None:
            return _dump(missing)
        # 模型常给可选数组顺手填 []，且 draft_id 可能是闸门补的：空列表按“没传”处理，覆盖时沿用原值
        return _dump(
            service.record(module, entity, kind, content, supersedes or None, anchors or None, draft_id or None,
                           source_conversation or None, aliases or None)
        )

    @server.tool()
    def confirm_memory(ids: list[str], source_conversation: str = "") -> str:
        """确认记忆仍然成立：对照关联代码核对过 stale=true 的记忆、结论依然正确时调用，核对日期记为今天，
        之后不再因更早的代码改动标为 stale，排序时也按核对日期计算新旧。已不成立的不要确认，改写 correction。"""
        if service is None:
            return _dump(missing)
        return _dump(service.confirm(ids, source_conversation or None))

    @server.tool()
    def memory_graph(module: str, entity: str = "") -> str:
        """查看模块的记忆图谱。只传 module：模块概览，列出各议题（现行/已被替代条数、首末日期、最新两条现行结论摘要）
        和相关模块（共享代码或正文提及），用于一次看清模块全貌；再传 entity：给出该议题的时间线（谁在哪天替代了谁）和相关模块。"""
        if service is None:
            return _dump(missing)
        return _dump(service.graph(module, entity or None))

    @server.tool()
    def list_modules(category: str = "") -> str:
        """列出项目的模块与记忆数量、常用议题。不确定模块名时先调用它。"""
        if service is None:
            return _dump(missing)
        result = service.list_modules(category or None)
        result["project_root"] = str(service.root)
        return _dump(result)

    return server


def serve(raw_root: str | None, worker: bool = False) -> None:
    root = resolve_root(raw_root)
    config = _load_config(root)
    settings = (config.get("server") if config else None) or {}
    if worker or not settings.get("watchdog", True):
        build_server(root).run("stdio")
        return
    import sys

    from pmem.server.watchdog import DEFAULT_TIMEOUT, Watchdog

    command = [sys.executable, "-m", "pmem.cli.main", "serve", "--worker"]
    if root is not None:
        command += ["--root", str(root)]
    try:
        timeout = float(settings.get("request_timeout") or DEFAULT_TIMEOUT)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT
    on_restart = None
    if config is not None:
        from pmem.metrics.events import log_event

        cache_dir = config.cache_dir
        on_restart = lambda kind, reason: log_event(cache_dir, "server_restart", kind=kind, reason=reason)
    Watchdog(command, sys.stdin.buffer, sys.stdout.buffer, timeout, on_restart).run()


def _load_config(root: Path | None):
    if root is None:
        return None
    from pmem.core.config import Config, ConfigError

    try:
        return Config.load(root)
    except (ConfigError, OSError, ValueError):
        return None
