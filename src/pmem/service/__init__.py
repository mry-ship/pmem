"""MCP 工具与命令行背后的业务规则，两边共用。

按职责分文件，新增一类操作时加一个 *Ops 类并在下面组合进来：
- base：依赖的懒加载（配置、模块目录、索引、版本库）、错误返回的形状、共用小工具；
- search：search_memory、memory_graph、list_modules（只读）；
- record：record_memory 的全部写入规则；
- status：confirm、归档与恢复、种子转正与退回；
- curation：高频词、可合并的议题分组（只读统计）。
"""
from __future__ import annotations

from pmem.service.curation import COMPACT_MIN_GROUP, CurationOps
from pmem.service.record import RecordOps
from pmem.service.search import SearchOps
from pmem.service.status import StatusOps

__all__ = ["COMPACT_MIN_GROUP", "MemoryService"]


class MemoryService(SearchOps, RecordOps, StatusOps, CurationOps):
    """MCP 工具与命令行背后的业务规则，两边共用。"""
