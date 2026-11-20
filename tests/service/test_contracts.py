"""工具返回契约：字段改名、漏写、类型变了会失败（v0.7 §3.5）。"""
from __future__ import annotations

import pytest

from pmem.service import MemoryService
from pmem.service.contracts import check_graph, check_list_modules, check_record, check_search


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    root = tmp_path / "proj"
    mem = root / ".memory"
    mem.mkdir(parents=True)
    (mem / "config.yaml").write_text(
        "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n",
        encoding="utf-8",
    )
    (mem / "modules.yaml").write_text(
        "categories: { gameplay: {} }\nmodules:\n  gameplay.Jigsaw: { paths: [src/**] }\n",
        encoding="utf-8",
    )
    (root / "src").mkdir()
    return root


@pytest.fixture
def service(project):
    svc = MemoryService(project)
    yield svc
    svc.close()


def test_search_record_graph_list_match_contracts(service):
    text = "排除：契约测试用的坑，根因在服务端幂等，不要在客户端去重。"
    written = service.record("gameplay.Jigsaw", "Reward", "exclusion", text)
    assert check_record(written) == [], check_record(written)

    search = service.search(module="gameplay.Jigsaw", query="幂等")
    assert check_search(search) == [], check_search(search)

    graph = service.graph("gameplay.Jigsaw")
    assert check_graph(graph) == [], check_graph(graph)

    listed = service.list_modules()
    assert check_list_modules(listed) == [], check_list_modules(listed)


def test_fail_shapes_still_have_error():
    assert check_search({"ok": False, "error": "x"}) == []
    assert check_record({"ok": False, "error": "x", "code": "when_invalid"}) == []
    assert check_search({"ok": False}) == ["失败返回缺少 error 字符串"]
    assert check_search({"ok": True}) == ["成功返回应有 items"]
