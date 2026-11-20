"""闸门组合类共享属性声明（v0.7 §3.6）：消掉混入类上对 root/config/state 等的假报错。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pmem.core.config import Config
from pmem.core.entry import Entry
from pmem.core.registry import ModuleRegistry
from pmem.hooks.state import SessionState


class GateAttrs:
    """Gate 在 __init__ 里赋值；各混入类继承本类，便于类型检查认共享属性。"""

    root: Path
    payload: dict[str, Any]
    config: Config
    conversation: str
    state: SessionState | None
    registry: ModuleRegistry
    defer_stale: bool
    _files: dict[str, Path]
    _entries: dict[str, list[Entry]]
    _deferred: dict[str, Entry]
