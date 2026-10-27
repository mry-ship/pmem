"""外部输入边界校验（v0.7 起步）：只用标准库，供 config / modules / 记忆头 / Hook 共用。

设计见 docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md §3.4。
本模块目前提供通用报错与基础类型检查；各调用方逐步从零散 isinstance 迁过来。
"""
from __future__ import annotations

from typing import Any


class SchemaError(ValueError):
    """带字段路径的校验错误，例如「.memory/config.yaml：gate.mode …」。"""

    def __init__(self, path: str, message: str):
        self.path = path
        self.detail = message
        super().__init__(f"{path}：{message}" if path else message)


def expect_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SchemaError(path, f"应是键值对，实际是 {type(value).__name__}")
    return value


def expect_list(value: Any, path: str) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    raise SchemaError(path, f"应是列表（或单个字符串），实际是 {type(value).__name__}")


def expect_str(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise SchemaError(path, f"应是字符串，实际是 {type(value).__name__}")
    return value


def expect_bool(value: Any, path: str) -> bool:
    if isinstance(value, bool):
        return value
    raise SchemaError(path, f"应是布尔值，实际是 {type(value).__name__}")


def expect_number(value: Any, path: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError(path, f"应是数字，实际是 {type(value).__name__}")
    number = float(value)
    if minimum is not None and number < minimum:
        raise SchemaError(path, f"应 ≥ {minimum}，实际是 {number}")
    return number


def expect_one_of(value: Any, path: str, choices: tuple[str, ...]) -> str:
    text = expect_str(value, path)
    if text not in choices:
        raise SchemaError(path, f"应是 {' / '.join(choices)} 之一，实际是 {text!r}")
    return text
