"""MCP / CLI 工具返回契约（v0.7 §3.5）：TypedDict 登记字段，测试按此检查真实返回。

设计见 docs/superpowers/specs/2026-10-21-pmem-typesafe-design.md §3.5。
只描述对外形状；运行时仍是普通 dict。Python 3.10 用 total=False 表达可选字段。
"""
from __future__ import annotations

from typing import Any, TypedDict


class FailResult(TypedDict, total=False):
    ok: bool
    error: str
    code: str


class MemoryItem(TypedDict, total=False):
    """search_memory 的 items 一行（教训全文）；seen 折叠后可能没有 content。"""

    id: str
    entity: str
    kind: str
    date: str
    stale: bool
    author: str
    content: str
    summary: str
    verify: str
    applies: str
    when: dict[str, list[str]]
    enforced_by: list[str]
    scope: str
    module: str
    check: list[str]
    verified: str
    status: str
    seen: bool
    inherited: bool


class FeatureItem(TypedDict, total=False):
    """search_memory 的 features 一行（功能记录/规划，默认只有标题）。"""

    id: str
    entity: str
    kind: str
    date: str
    stale: bool
    summary: str
    applies: str
    when: dict[str, list[str]]
    enforced_by: list[str]
    module: str
    check: list[str]
    status: str
    seen: bool


class ChildRow(TypedDict, total=False):
    module: str
    count: int
    children: int
    latest: list[dict[str, Any]]


class SearchResult(TypedDict, total=False):
    ok: bool
    module: str | None
    items: list[MemoryItem]
    features: list[FeatureItem]
    children: list[ChildRow]
    related: list[str]
    features_hint: str
    applies_hint: str
    when_hint: str
    enforced_hint: str
    verify_hint: str
    inherited_hint: str
    seen_hint: str
    as_of: str
    expanded: list[str]
    fallback: str
    degraded: str
    warnings: list[str]
    hint: str
    module_exists: bool
    similar_modules: list[str]
    context: dict[str, Any]
    error: str
    code: str


class RecordResult(TypedDict, total=False):
    ok: bool
    id: str
    module: str
    entity: str
    kind: str
    path: str
    overwritten: bool
    draft_id: str
    warnings: list[str]
    hints: list[str]
    similar: list[dict[str, Any]]
    sibling_similar: list[dict[str, Any]]
    error: str
    code: str


class GraphTopic(TypedDict, total=False):
    entity: str
    latest: list[dict[str, Any]]


class GraphResult(TypedDict, total=False):
    ok: bool
    module: str
    topics: list[GraphTopic]
    entity: str
    timeline: list[dict[str, Any]]
    related: list[dict[str, Any]]
    lineage: list[str]
    children: list[ChildRow]
    verify_hint: str
    entities: list[str]
    error: str
    code: str


class ModuleRow(TypedDict, total=False):
    module: str
    count: int
    entities: list[str]
    registered: bool
    parent: str | None
    children: list[str]
    aliases: list[str]
    deprecated: bool


class ListModulesResult(TypedDict, total=False):
    ok: bool
    categories: list[str]
    modules: list[ModuleRow]
    registered_empty: list[str]
    error: str
    code: str


def _type_name(value: Any) -> str:
    return type(value).__name__


def _check_item(row: Any, *, path: str, require_content: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(row, dict):
        return [f"{path} 应是键值对，实际是 {_type_name(row)}"]
    for key in ("id", "entity", "kind", "date"):
        if key not in row:
            errors.append(f"{path} 缺少 {key}")
        elif not isinstance(row[key], str):
            errors.append(f"{path}.{key} 应是字符串，实际是 {_type_name(row[key])}")
    if "stale" not in row:
        errors.append(f"{path} 缺少 stale")
    elif not isinstance(row["stale"], bool):
        errors.append(f"{path}.stale 应是布尔值，实际是 {_type_name(row['stale'])}")
    if require_content and "content" not in row and not row.get("seen"):
        errors.append(f"{path} 教训行应有 content（或 seen=true）")
    if "when" in row and row["when"] is not None and not isinstance(row["when"], dict):
        errors.append(f"{path}.when 应是键值对，实际是 {_type_name(row['when'])}")
    if "enforced_by" in row and not isinstance(row["enforced_by"], list):
        errors.append(f"{path}.enforced_by 应是列表，实际是 {_type_name(row['enforced_by'])}")
    return errors


def check_search(response: dict) -> list[str]:
    """检查 search_memory 返回；ok=False 时只要求 error。"""
    if not isinstance(response, dict):
        return ["返回应是键值对"]
    if "ok" not in response:
        return ["缺少 ok"]
    if not response["ok"]:
        return [] if isinstance(response.get("error"), str) else ["失败返回缺少 error 字符串"]
    errors: list[str] = []
    items = response.get("items")
    if items is None:
        errors.append("成功返回应有 items")
    elif not isinstance(items, list):
        errors.append(f"items 应是列表，实际是 {_type_name(items)}")
    else:
        for i, row in enumerate(items):
            errors += _check_item(row, path=f"items[{i}]", require_content=True)
    features = response.get("features")
    if features is not None:
        if not isinstance(features, list):
            errors.append(f"features 应是列表，实际是 {_type_name(features)}")
        else:
            for i, row in enumerate(features):
                errors += _check_item(row, path=f"features[{i}]")
    for hint in ("features_hint", "applies_hint", "when_hint", "enforced_hint", "verify_hint",
                 "inherited_hint", "seen_hint"):
        if hint in response and not isinstance(response[hint], str):
            errors.append(f"{hint} 应是字符串，实际是 {_type_name(response[hint])}")
    if "children" in response and not isinstance(response["children"], list):
        errors.append(f"children 应是列表，实际是 {_type_name(response['children'])}")
    if "related" in response and not isinstance(response["related"], list):
        errors.append(f"related 应是列表，实际是 {_type_name(response['related'])}")
    return errors


def check_record(response: dict) -> list[str]:
    if not isinstance(response, dict) or "ok" not in response:
        return ["返回应是含 ok 的键值对"]
    if not response["ok"]:
        return [] if isinstance(response.get("error"), str) else ["失败返回缺少 error 字符串"]
    errors = []
    for key in ("id", "module", "entity", "kind", "path", "draft_id"):
        if key not in response:
            errors.append(f"成功写入缺少 {key}")
        elif not isinstance(response[key], str):
            errors.append(f"{key} 应是字符串，实际是 {_type_name(response[key])}")
    if "overwritten" in response and not isinstance(response["overwritten"], bool):
        errors.append(f"overwritten 应是布尔值，实际是 {_type_name(response['overwritten'])}")
    return errors


def check_graph(response: dict) -> list[str]:
    if not isinstance(response, dict) or "ok" not in response:
        return ["返回应是含 ok 的键值对"]
    if not response["ok"]:
        return [] if isinstance(response.get("error"), str) else ["失败返回缺少 error 字符串"]
    errors = []
    if "module" in response and not isinstance(response["module"], str):
        errors.append(f"module 应是字符串，实际是 {_type_name(response['module'])}")
    if "topics" in response:
        if not isinstance(response["topics"], list):
            errors.append(f"topics 应是列表，实际是 {_type_name(response['topics'])}")
        else:
            for i, topic in enumerate(response["topics"]):
                if not isinstance(topic, dict) or "entity" not in topic or "latest" not in topic:
                    errors.append(f"topics[{i}] 应有 entity 与 latest")
                elif not isinstance(topic["latest"], list):
                    errors.append(f"topics[{i}].latest 应是列表")
    if "timeline" in response and not isinstance(response["timeline"], list):
        errors.append(f"timeline 应是列表，实际是 {_type_name(response['timeline'])}")
    if "related" in response and not isinstance(response["related"], list):
        errors.append(f"related 应是列表，实际是 {_type_name(response['related'])}")
    return errors


def check_list_modules(response: dict) -> list[str]:
    if not isinstance(response, dict) or "ok" not in response:
        return ["返回应是含 ok 的键值对"]
    if not response["ok"]:
        return [] if isinstance(response.get("error"), str) else ["失败返回缺少 error 字符串"]
    errors = []
    if "categories" not in response or not isinstance(response["categories"], list):
        errors.append("成功返回应有 categories 列表")
    if "modules" not in response or not isinstance(response["modules"], list):
        errors.append("成功返回应有 modules 列表")
    else:
        for i, row in enumerate(response["modules"]):
            if not isinstance(row, dict):
                errors.append(f"modules[{i}] 应是键值对")
                continue
            for key in ("module", "count", "entities", "registered"):
                if key not in row:
                    errors.append(f"modules[{i}] 缺少 {key}")
            if "module" in row and not isinstance(row["module"], str):
                errors.append(f"modules[{i}].module 应是字符串")
            if "count" in row and not isinstance(row["count"], int):
                errors.append(f"modules[{i}].count 应是整数")
            if "entities" in row and not isinstance(row["entities"], list):
                errors.append(f"modules[{i}].entities 应是列表")
            if "registered" in row and not isinstance(row["registered"], bool):
                errors.append(f"modules[{i}].registered 应是布尔值")
    if "registered_empty" in response and not isinstance(response["registered_empty"], list):
        errors.append("registered_empty 应是列表")
    return errors
