import asyncio
import json

from pmem.server.app import build_server, resolve_root
from tests.test_service import project  # noqa: F401  复用项目夹具


def call(server, name, args):
    result = asyncio.run(server.call_tool(name, args))
    return json.loads(result.content[0].text)


def test_exposes_memory_tools(project):  # noqa: F811
    server = build_server(project)
    names = sorted(t.name for t in asyncio.run(server.list_tools()))
    assert names == ["confirm_memory", "list_modules", "memory_graph", "record_memory", "search_memory"]


def test_record_and_search_through_tools(project):  # noqa: F811
    server = build_server(project)
    written = call(server, "record_memory", {
        "module": "gameplay.Jigsaw", "entity": "Reward", "kind": "conclusion",
        "content": "拼图奖励重复发放的根因是领取按钮没有防连点。",
    })
    assert written["ok"] is True
    found = call(server, "search_memory", {"path": "src/Jigsaw/Board.cs"})
    assert found["items"][0]["id"] == written["id"]
    listing = call(server, "list_modules", {})
    assert listing["project_root"] == str(project.resolve())


def test_every_response_is_marked_as_pmem(project):  # noqa: F811
    """闸门靠这个标记区分别家记忆服务的同名工具。"""
    server = build_server(project)
    assert call(server, "search_memory", {"module": "gameplay.Jigsaw"})["server"] == "pmem"
    assert call(server, "list_modules", {})["server"] == "pmem"
    assert call(build_server(None), "search_memory", {"query": "x"})["server"] == "pmem"


def test_broken_config_is_reported_per_call_and_recovers_without_restart(project):  # noqa: F811
    config = project / ".memory" / "config.yaml"
    good = config.read_text(encoding="utf-8")
    server = build_server(project)
    config.write_text("vcs: [unclosed\n", encoding="utf-8")
    broken = call(server, "search_memory", {"module": "gameplay.Jigsaw"})
    assert broken["ok"] is False and "配置有误" in broken["error"] and broken["server"] == "pmem"
    config.write_text(good, encoding="utf-8")
    assert call(server, "search_memory", {"module": "gameplay.Jigsaw"})["ok"] is True


def test_unexpected_errors_come_back_marked_as_pmem(project, monkeypatch):  # noqa: F811
    from pmem.service import MemoryService

    def boom(self, *args, **kwargs):
        raise PermissionError("记忆文件被占用")

    monkeypatch.setattr(MemoryService, "confirm", boom)
    result = call(build_server(project), "confirm_memory", {"ids": ["01JA7K3M2X9F4Q8W6ZB1C2D3E4"]})
    assert result == {"ok": False, "error": "pmem 内部错误：PermissionError: 记忆文件被占用", "server": "pmem"}


def test_without_project_tools_explain_how_to_init(tmp_path):
    server = build_server(None)
    assert "pmem init" in call(server, "search_memory", {"query": "x"})["error"]


def test_resolve_root_ignores_unexpanded_variables(project, monkeypatch):  # noqa: F811
    monkeypatch.chdir(project / ".memory")
    assert resolve_root("${workspaceFolder}") == project.resolve()
    assert resolve_root(str(project)) == project.resolve()
