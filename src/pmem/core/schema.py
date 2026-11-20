"""外部输入边界校验（v0.7）：只用标准库，供 config / modules / 记忆头 / Hook 共用。

设计见 docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md §3.4。
报错带字段路径；拼错的键给出相近键名提示（只警告，不拒绝）。
"""
from __future__ import annotations

import difflib
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


def suggest_key(name: str, known: list[str] | tuple[str, ...] | set[str], *, cutoff: float = 0.6) -> str | None:
    """拼错键时找最相近的已知键；没有足够相似的返回 None。"""
    if not name or not known:
        return None
    matches = difflib.get_close_matches(str(name), [str(k) for k in known], n=1, cutoff=cutoff)
    return matches[0] if matches else None


def unknown_key_warnings(
    data: Any,
    known: dict[str, set[str] | frozenset[str] | None],
    *,
    file_path: str,
    section: str | None = None,
) -> list[str]:
    """对照已知键表，对拼错/多余的键给出警告（不拒绝）。

    known：顶层键 → 该节允许的子键集合；值为 None 表示该节不再往下检查（自由形状）。
    section：只检查某一节时传入节名。
    """
    if data is None:
        return []
    try:
        root = expect_mapping(data, file_path)
    except SchemaError:
        return []
    warnings: list[str] = []
    top_known = set(known)
    if section is None:
        for key in root:
            if key not in top_known:
                hint = suggest_key(str(key), top_known)
                tip = f"，是不是 {hint}？" if hint else ""
                warnings.append(f"{file_path}：不认识的键 {key}{tip}（已忽略）")
        for key, child_known in known.items():
            if child_known is None or key not in root:
                continue
            child = root.get(key)
            if not isinstance(child, dict):
                continue
            for name in child:
                if name not in child_known:
                    hint = suggest_key(str(name), child_known)
                    tip = f"，是不是 {key}.{hint}？" if hint else ""
                    warnings.append(f"{file_path}：不认识的键 {key}.{name}{tip}（已忽略）")
        return warnings
    # 单节
    if section not in root or not isinstance(root.get(section), dict):
        return warnings
    child_known = known.get(section)
    if child_known is None:
        return warnings
    for name in root[section]:
        if name not in child_known:
            hint = suggest_key(str(name), child_known)
            tip = f"，是不是 {section}.{hint}？" if hint else ""
            warnings.append(f"{file_path}：不认识的键 {section}.{name}{tip}（已忽略）")
    return warnings
