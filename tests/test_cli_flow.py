import io
import json
import sys

import yaml

from pmem.cli.main import main


def test_init_creates_project_files_and_merges_existing_cursor_config(tmp_path, capsys):
    cursor = tmp_path / ".cursor"
    cursor.mkdir()
    (cursor / "hooks.json").write_text(json.dumps({
        "version": 1, "hooks": {"stop": [{"command": "my-own-hook"}, {"command": "pmem hook stop"}]}
    }), encoding="utf-8")
    (cursor / "mcp.json").write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}), encoding="utf-8")
    (tmp_path / "Assets").mkdir()
    (tmp_path / "ProjectSettings").mkdir()

    assert main(["init", "--root", str(tmp_path)]) == 0

    config = yaml.safe_load((tmp_path / ".memory" / "config.yaml").read_text(encoding="utf-8"))
    assert config["project"]["type"] == "game"
    modules = yaml.safe_load((tmp_path / ".memory" / "modules.yaml").read_text(encoding="utf-8"))
    assert "activity" in modules["categories"]
    hooks = json.loads((cursor / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert [h["command"] for h in hooks["stop"]] == ["my-own-hook", "pmem hook stop"]
    assert "preToolUse" in hooks
    servers = json.loads((cursor / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    assert set(servers) == {"other", "pmem"}
    assert (cursor / "rules" / "pmem.mdc").exists()
    assert (cursor / "skills" / "pmem-bootstrap" / "SKILL.md").exists()


def test_init_keeps_existing_memory_config(tmp_path):
    (tmp_path / ".memory").mkdir()
    (tmp_path / ".memory" / "config.yaml").write_text("gate: { mode: block }\n", encoding="utf-8")
    main(["init", "--root", str(tmp_path)])
    assert "block" in (tmp_path / ".memory" / "config.yaml").read_text(encoding="utf-8")


def test_scan_lists_directories_and_third_party(tmp_path, capsys):
    for rel in ["Assets/Game/Jigsaw/A.cs", "Assets/Game/Jigsaw/B.cs", "Assets/Game/Jigsaw/C.cs",
                "Assets/Plugins/Sdk/X.cs", "README.md"]:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
    main(["scan", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Assets/Plugins" in out
    assert "[Assets/Game/Jigsaw]" in out


def test_doctor_reports_coverage(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    main(["init", "--root", str(tmp_path), "--type", "generic"])
    config = tmp_path / ".memory" / "config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("backend: auto", "backend: none"), encoding="utf-8")
    src = tmp_path / "src" / "Login"
    src.mkdir(parents=True)
    (src / "Login.ts").write_text("x", encoding="utf-8")
    modules = tmp_path / ".memory" / "modules.yaml"
    modules.write_text(modules.read_text(encoding="utf-8").replace(
        "modules: {}", "modules:\n  feature.Login:\n    paths: [src/Login/**]\n  feature.Ghost:\n    paths: [src/Ghost/**]"
    ), encoding="utf-8")
    capsys.readouterr()
    main(["doctor", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "模块覆盖率 100.0%" in out
    assert "feature.Ghost" in out


def test_hook_command_reads_bom_stdin_and_writes_ascii(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    main(["init", "--root", str(tmp_path), "--type", "generic", "--gate", "block"])
    modules = tmp_path / ".memory" / "modules.yaml"
    modules.write_text(modules.read_text(encoding="utf-8").replace(
        "modules: {}", "modules:\n  feature.Login:\n    paths: [src/Login/**]"
    ), encoding="utf-8")
    entries = tmp_path / ".memory" / "entries" / "feature.Login"
    entries.mkdir(parents=True)
    (entries / "01JA7K3M2X9F4Q8W6ZB1C2D3E4.md").write_text(
        "---\nid: 01JA7K3M2X9F4Q8W6ZB1C2D3E4\nmodule: feature.Login\nentity: Token\nkind: conclusion\n"
        "author: a\nnote_date: '2026-10-01'\n---\n登录令牌过期后要静默刷新\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    payload = {"conversation_id": "c1", "tool_name": "Write",
               "tool_input": {"file_path": str(tmp_path / "src/Login/Login.ts"), "content": "中文"}}
    raw = ("\ufeff" + json.dumps(payload, ensure_ascii=False)).encode("utf-8")
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(raw)))
    capsys.readouterr()
    main(["hook", "pre-tool"])
    out = capsys.readouterr().out
    assert out.isascii()
    assert json.loads(out)["permission"] == "deny"


def test_record_and_search_from_cli(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    main(["init", "--root", str(tmp_path), "--type", "generic"])
    (tmp_path / ".memory" / "config.yaml").write_text("vcs: none\nembedding: { backend: none }\n", encoding="utf-8")
    capsys.readouterr()
    code = main(["record", "--root", str(tmp_path), "--module", "feature.Login", "--entity", "Token",
                 "--kind", "conclusion", "--content", "登录令牌过期后由拦截器静默刷新，失败才跳登录页。"])
    assert code == 0
    written = json.loads(capsys.readouterr().out)
    main(["search", "令牌刷新", "--root", str(tmp_path)])
    assert json.loads(capsys.readouterr().out)["items"][0]["id"] == written["id"]


def test_reindex_rebuilds_cache_and_reports_bad_files(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    main(["init", "--root", str(tmp_path), "--type", "generic"])
    (tmp_path / ".memory" / "config.yaml").write_text("vcs: none\nembedding: { backend: none }\n", encoding="utf-8")
    main(["record", "--root", str(tmp_path), "--module", "feature.Login", "--entity", "Token",
          "--kind", "conclusion", "--content", "登录令牌过期后由拦截器静默刷新，失败才跳登录页。"])
    from pmem.core.config import Config

    cache = Config.load(tmp_path).cache_dir
    (cache / "cites.json").write_text("{}", encoding="utf-8")
    capsys.readouterr()
    assert main(["reindex", "--root", str(tmp_path)]) == 0
    assert "记忆 1 条" in capsys.readouterr().out
    assert not (cache / "cites.json").exists()

    (tmp_path / ".memory" / "entries" / "feature.Login" / "broken.md").write_text("不是记忆", encoding="utf-8")
    assert main(["reindex", "--root", str(tmp_path)]) == 1
    assert "broken.md" in capsys.readouterr().out


def test_hook_outside_project_allows(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"{}")))
    main(["hook", "pre-tool"])
    assert json.loads(capsys.readouterr().out) == {"permission": "allow"}
