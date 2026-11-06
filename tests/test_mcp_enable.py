import json
import sqlite3
from pathlib import Path

from pmem.generate.mcp_enable import (
    cursor_approval_key,
    cursor_server_config_hash,
    enable_claude_project_mcp,
    enable_codex_project_mcp,
    enable_cursor_project_mcp,
)
from pmem.generate.templates import MCP_SERVER, PLAIN_MCP_SERVER


def test_cursor_hash_matches_known_playwright_approval():
    # Cursor 里已批准的 project-0-TileMatch-playwright:-433220a0
    assert cursor_server_config_hash(
        {"command": "npx", "args": ["-y", "@playwright/mcp@latest"]}
    ) == "-433220a0"


def test_cursor_pmem_hash_stable_with_workspace_placeholder():
    assert cursor_server_config_hash(MCP_SERVER) == "66633844"
    assert cursor_approval_key("project-0-Demo-pmem", MCP_SERVER).endswith(":66633844")


def test_enable_skips_under_pytest_unless_forced(monkeypatch):
    monkeypatch.delenv("PMEM_SKIP_MCP_ENABLE", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_mcp_enable.py::x")
    assert "测试环境跳过" in enable_cursor_project_mcp(Path("."))
    assert "测试环境跳过" in enable_claude_project_mcp(Path("."))
    assert "测试环境跳过" in enable_codex_project_mcp(Path("."))


def test_enable_cursor_writes_project_approval(tmp_path, monkeypatch):
    root = tmp_path / "DemoProj"
    root.mkdir()
    (root / ".cursor").mkdir()
    (root / ".cursor" / "mcp.json").write_text(
        json.dumps({"mcpServers": {"pmem": MCP_SERVER}}), encoding="utf-8"
    )

    db = tmp_path / "state.vscdb"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
    con.execute(
        "INSERT INTO ItemTable(key,value) VALUES (?,?)",
        ("cursor/approvedProjectMcpServers", json.dumps(["project-0-Other-x:1"])),
    )
    con.commit()
    con.close()
    monkeypatch.setattr("pmem.generate.mcp_enable.cursor_state_db", lambda: db)
    monkeypatch.setenv("PMEM_SKIP_MCP_ENABLE", "0")

    msg = enable_cursor_project_mcp(root, MCP_SERVER)
    assert "已项目级批准" in msg
    con = sqlite3.connect(db)
    approved = json.loads(
        con.execute(
            "SELECT value FROM ItemTable WHERE key=?",
            ("cursor/approvedProjectMcpServers",),
        ).fetchone()[0]
    )
    con.close()
    assert "project-0-Other-x:1" in approved
    assert f"project-0-{root.name}-pmem:66633844" in approved


def test_enable_claude_project_mcp_lists_pmem(tmp_path, monkeypatch):
    root = tmp_path / "MyApp"
    root.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    claude = home / ".claude.json"
    key = str(root.resolve()).replace("\\", "/")
    claude.write_text(
        json.dumps({"projects": {key: {"enabledMcpjsonServers": [], "disabledMcpjsonServers": ["pmem"]}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr("pmem.generate.mcp_enable.Path.home", staticmethod(lambda: home))
    monkeypatch.setenv("PMEM_SKIP_MCP_ENABLE", "0")

    msg = enable_claude_project_mcp(root)
    assert "已项目级启用" in msg
    data = json.loads(claude.read_text(encoding="utf-8"))
    proj = data["projects"][key]
    assert proj["enabledMcpjsonServers"] == ["pmem"]
    assert "pmem" not in proj["disabledMcpjsonServers"]
    assert proj["hasTrustDialogAccepted"] is True


def test_enable_codex_trusts_project(tmp_path, monkeypatch):
    root = tmp_path / "CodexApp"
    root.mkdir()
    home = tmp_path / "home"
    codex = home / ".codex"
    codex.mkdir(parents=True)
    cfg = codex / "config.toml"
    cfg.write_text("# empty\n", encoding="utf-8")
    monkeypatch.setattr("pmem.generate.mcp_enable.Path.home", staticmethod(lambda: home))
    monkeypatch.setenv("PMEM_SKIP_MCP_ENABLE", "0")

    msg = enable_codex_project_mcp(root)
    assert "trusted" in msg.lower() or "信任" in msg
    text = cfg.read_text(encoding="utf-8")
    assert "trust_level = \"trusted\"" in text
    assert "projects." in text


def test_plain_mcp_server_unchanged():
    assert PLAIN_MCP_SERVER["command"] == "pmem"
    assert PLAIN_MCP_SERVER["args"] == ["serve"]
