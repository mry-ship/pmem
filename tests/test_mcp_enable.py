import json
import sqlite3
import sys
from pathlib import Path

from pmem.generate.mcp_enable import (
    _claude_project_keys,
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
    monkeypatch.setattr("pmem.generate.mcp_enable.cursor_running", lambda: False)
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


def test_enable_cursor_keeps_other_hash_for_same_folder_name(tmp_path, monkeypatch):
    # 同名文件夹的另一份配置哈希必须留下；没有哈希的旧记录仍换成这次的哈希。
    root = tmp_path / "MyApp"
    root.mkdir()
    db = tmp_path / "state.vscdb"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
    old = "project-0-MyApp-pmem:deadbeef"
    con.execute(
        "INSERT INTO ItemTable(key,value) VALUES (?,?)",
        ("cursor/approvedProjectMcpServers", json.dumps([
            old, "project-0-MyApp-pmem", "project-0-Other-x:1",
        ])),
    )
    con.commit()
    con.close()
    monkeypatch.setattr("pmem.generate.mcp_enable.cursor_state_db", lambda: db)
    monkeypatch.setattr("pmem.generate.mcp_enable.cursor_running", lambda: False)
    monkeypatch.setenv("PMEM_SKIP_MCP_ENABLE", "0")

    enable_cursor_project_mcp(root, MCP_SERVER)
    enable_cursor_project_mcp(root, MCP_SERVER)
    con = sqlite3.connect(db)
    approved = json.loads(con.execute(
        "SELECT value FROM ItemTable WHERE key=?", ("cursor/approvedProjectMcpServers",)
    ).fetchone()[0])
    con.close()
    assert old in approved
    assert "project-0-MyApp-pmem" not in approved
    assert approved.count("project-0-MyApp-pmem:66633844") == 1
    assert "project-0-Other-x:1" in approved


def test_enable_cursor_skips_write_while_cursor_running(tmp_path, monkeypatch):
    # Cursor 运行时写的批准会被它覆盖：不写库，返回“退出后重跑 / 手动开”的提示
    root = tmp_path / "DemoProj"
    root.mkdir()
    db = tmp_path / "state.vscdb"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")
    con.commit()
    con.close()
    monkeypatch.setattr("pmem.generate.mcp_enable.cursor_state_db", lambda: db)
    monkeypatch.setattr("pmem.generate.mcp_enable.cursor_running", lambda: True)
    monkeypatch.setenv("PMEM_SKIP_MCP_ENABLE", "0")

    msg = enable_cursor_project_mcp(root, MCP_SERVER)
    assert "正在运行" in msg and "退出" in msg
    assert "已项目级批准" not in msg
    # 没有写入任何批准
    con = sqlite3.connect(db)
    row = con.execute(
        "SELECT value FROM ItemTable WHERE key=?", ("cursor/approvedProjectMcpServers",)
    ).fetchone()
    con.close()
    assert row is None


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


def test_enable_claude_does_not_touch_same_name_other_path(tmp_path, monkeypatch):
    # 两个同名不同路径的项目：只应启用当前这个，另一个（~/other/MyApp）不能被一起写入+标信任
    root = (tmp_path / "here" / "MyApp")
    root.mkdir(parents=True)
    other = (tmp_path / "other" / "MyApp")
    other.mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    claude = home / ".claude.json"
    other_key = str(other.resolve()).replace("\\", "/")
    claude.write_text(json.dumps({"projects": {other_key: {"enabledMcpjsonServers": []}}}), encoding="utf-8")
    monkeypatch.setattr("pmem.generate.mcp_enable.Path.home", staticmethod(lambda: home))
    monkeypatch.setenv("PMEM_SKIP_MCP_ENABLE", "0")

    enable_claude_project_mcp(root)
    data = json.loads(claude.read_text(encoding="utf-8"))
    # 另一个同名项目原样未动：没被加 pmem、没被标信任
    assert data["projects"][other_key]["enabledMcpjsonServers"] == []
    assert "hasTrustDialogAccepted" not in data["projects"][other_key]
    # 当前项目新建了自己的条目并启用
    here_key = str(root.resolve()).replace("\\", "/")
    assert "pmem" in data["projects"][here_key]["enabledMcpjsonServers"]


def test_claude_match_does_not_resolve_unc_or_other_drives(tmp_path, monkeypatch):
    root = tmp_path / "MyApp"
    root.mkdir()
    resolved = root.resolve()
    unc = "\\\\dead-server\\share\\MyApp"
    other_drive = "Z:" if resolved.drive.upper() != "Z:" else "Y:"
    other = f"{other_drive}\\offline\\MyApp"
    projects = {unc: {}, other: {}, str(resolved): {}}
    original = Path.resolve

    def guarded(self, *args, **kwargs):
        text = str(self)
        if text.startswith("\\\\") or text.startswith("//") or text[:2].upper() == other_drive.upper():
            raise AssertionError(f"不应 resolve：{self}")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", guarded)
    keys = _claude_project_keys(root, projects)
    assert unc not in keys
    assert other not in keys
    assert str(resolved) in keys


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


def test_enable_codex_quotes_apostrophe_without_duplicating(tmp_path, monkeypatch):
    root = tmp_path / "O'Brien"
    root.mkdir()
    home = tmp_path / "home"
    cfg = home / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("# keep\n", encoding="utf-8")
    monkeypatch.setattr("pmem.generate.mcp_enable.Path.home", staticmethod(lambda: home))
    monkeypatch.setenv("PMEM_SKIP_MCP_ENABLE", "0")

    enable_codex_project_mcp(root)
    text = cfg.read_text(encoding="utf-8")
    again = enable_codex_project_mcp(root)
    assert "已信任" in again
    assert cfg.read_text(encoding="utf-8") == text
    header = next(line for line in text.splitlines() if line.startswith("[projects."))
    assert header.startswith('[projects."') and header.endswith('"]')
    assert "'" in header
    try:
        import tomllib
    except ModuleNotFoundError:
        tomllib = None
    if tomllib is not None:
        loaded = tomllib.loads(text)
        assert any(item.get("trust_level") == "trusted" for item in loaded["projects"].values())


def test_plain_mcp_server_unchanged():
    assert PLAIN_MCP_SERVER["command"] == "pmem"
    assert PLAIN_MCP_SERVER["args"] == ["serve"]
