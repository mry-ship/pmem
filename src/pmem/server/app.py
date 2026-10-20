from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from pmem.core.config import find_root

INSTRUCTIONS = (
    "项目研发记忆：按模块（category.Module）沉淀根因、排除项、决定与风险。"
    "改代码前用 search_memory 按文件路径或模块查一次；改了模块就用 record_memory 写一条功能记录（kind=feature，"
    "需求来源与必须保持的行为），排除了某个方向、确认了根因、发现看代码看不出的约束或风险时另记一条教训。"
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


def _stamp(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_mtime_ns, stat.st_size


def build_server(root: Path | None) -> MCPServer:
    from pmem.core.config import CONFIG_FILE, MEMORY_DIR, ConfigError
    from pmem.service import MemoryService

    missing = {"ok": False, "error": "当前工作区还没有接入 pmem：请在项目根目录运行 pmem init"}
    holder: dict = {}
    # 框架在线程池里并发执行同步工具；索引、sqlite 连接、模型懒加载都不是线程安全的
    lock = threading.Lock()
    config_path = root / MEMORY_DIR / CONFIG_FILE if root is not None else None

    def call(action) -> str:
        if root is None:
            return _dump(missing)
        with lock:
            try:
                # 服务常驻：config.yaml 改了就整个重建，检索、写入、嵌入等设置下一次调用即生效
                stamp = _stamp(config_path)
                if "service" in holder and holder.get("stamp") != stamp:
                    holder.pop("service").close()
                if "service" not in holder:
                    holder["service"] = MemoryService(root, source="mcp")
                    holder["stamp"] = stamp
                return _dump(action(holder["service"]))
            except ConfigError as exc:
                return _dump({"ok": False, "error": f"pmem 配置有误：{exc}；改好后再调用即可，无需重启"})
            except Exception as exc:  # noqa: BLE001  未预料的错误也要带来源标记返回，闸门才认得出是 pmem 的结果
                return _dump({"ok": False, "error": f"pmem 内部错误：{type(exc).__name__}: {exc}"})

    server = MCPServer("pmem", instructions=INSTRUCTIONS)

    @server.tool()
    def search_memory(
        module: str = "",
        path: str = "",
        entity: str = "",
        query: str = "",
        limit: int = 0,
        as_of: str = "",
        full: bool = False,
        ids: list[str] | None = None,
        source_conversation: str = "",
    ) -> str:
        """检索项目研发记忆。改代码前传 path（要改的文件）或 module（category.Module）；entity 是模块内议题，可省；
        query 是关键词或问题描述（按同义词表展开），都不确定时只传 query 全局检索。as_of=YYYY-MM-DD 看那天有效的记忆；
        limit 不传按项目配置。ids=[...] 按 id 取全文，优先于其他参数；full=true 时本对话给过的也给全文。
        返回 items（教训，全文）和 features（功能记录与规划，只有标题）；seen=true 的只给标题，要全文带 full=true；
        stale、applies 等字段的含义在结果的 *_hint 里说明（每个对话说明一次）。source_conversation 由系统填写，无需传。"""
        return call(lambda s: s.search(module or None, path or None, entity or None, query or None, limit,
                                       source_conversation or None, as_of or None, full=bool(full),
                                       ids=ids or None))

    @server.tool()
    def record_memory(
        module: str,
        entity: str,
        kind: str,
        content: str,
        supersedes: list[str] | None = None,
        anchors: list[str] | None = None,
        aliases: list[str] | None = None,
        summary: str = "",
        verify: str = "",
        applies: str = "",
        scope: str = "",
        draft_id: str = "",
        source_conversation: str = "",
    ) -> str:
        """记录一条研发记忆。kind：feature 功能记录（改了模块就写：需求来源、必须保持的行为、适用条件、入口）、
        plan 未实现的需求；教训 exclusion 排除的方向、conclusion 根因或坑、correction 推翻旧结论、risk 看代码看不出的约束、
        decision 方案取舍。module：category.Module；entity：模块内议题短名。
        content 自包含（现象、原因、证据、影响范围），不写“改了哪个方法”。summary：一句话结论或必须保持的行为（60 字内），
        摘要、Wiki 和去重后的检索只显示它。verify：怎么确认结论仍成立（命令、测试名、现象），结论和更正尽量填。
        applies：成立前提（120 字内）。scope=project：编码、环境、跨模块约定这类全项目都会踩的坑。
        aliases：现象和术语的其他叫法（如 ["闪退", "崩溃"]），换说法也能搜到。
        anchors：相关代码，尽量写到函数（路径#函数名；只写文件时该文件任何改动都会标需核实），不填按本对话改过的文件补。
        supersedes：本模块里被推翻的旧结论、说同一件事的旧功能记录、已实现的规划（plan）的 id。
        同一任务再写同一模块时带上次返回的 draft_id 覆盖，没填的可选字段沿用原值。
        返回的 similar 是同议题已有记忆：重复或被推翻时带 draft_id 重写并填 supersedes。"""
        # 模型常给可选数组顺手填 []，且 draft_id 可能是闸门补的：空列表按“没传”处理，覆盖时沿用原值
        return call(lambda s: s.record(module, entity, kind, content, supersedes or None, anchors or None,
                                       draft_id or None, source_conversation or None, aliases or None,
                                       summary=summary or None, scope=scope or None, verify=verify or None,
                                       applies=applies or None))

    @server.tool()
    def confirm_memory(ids: list[str], source_conversation: str = "") -> str:
        """确认记忆仍然成立：对照关联代码核对过 stale=true 的记忆、结论依然正确时调用，核对日期记为今天，
        之后不再因更早的代码改动标为 stale，排序时也按核对日期计算新旧。已不成立的不要确认，改写 correction。"""
        return call(lambda s: s.confirm(ids, source_conversation or None))

    @server.tool()
    def memory_graph(module: str, entity: str = "") -> str:
        """查看模块的记忆图谱。只传 module：模块概览，列出各议题（现行/已被替代条数、首末日期、最新两条现行结论摘要）
        和相关模块（共享代码或正文提及），用于一次看清模块全貌；再传 entity：给出该议题的时间线（谁在哪天替代了谁）和相关模块。"""
        return call(lambda s: s.graph(module, entity or None))

    @server.tool()
    def list_modules(category: str = "") -> str:
        """列出项目的模块与记忆数量、常用议题。不确定模块名时先调用它。"""
        return call(lambda s: {**s.list_modules(category or None), "project_root": str(s.root)})

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
