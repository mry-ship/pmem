import asyncio
import json

from pmem.server.app import build_server, resolve_root
from tests.test_service import project  # noqa: F401  复用项目夹具


def call(server, name, args):
    result = asyncio.run(server.call_tool(name, args))
    return json.loads(result.content[0].text)


def test_exposes_exactly_three_tools(project):  # noqa: F811
    server = build_server(project)
    names = sorted(t.name for t in asyncio.run(server.list_tools()))
    assert names == ["list_modules", "record_memory", "search_memory"]


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


def test_without_project_tools_explain_how_to_init(tmp_path):
    server = build_server(None)
    assert "pmem init" in call(server, "search_memory", {"query": "x"})["error"]


def test_resolve_root_ignores_unexpanded_variables(project, monkeypatch):  # noqa: F811
    monkeypatch.chdir(project / ".memory")
    assert resolve_root("${workspaceFolder}") == project.resolve()
    assert resolve_root(str(project)) == project.resolve()
