import io
import json
import sys
import time

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
    assert "pmem compact" in (cursor / "skills" / "pmem-compact" / "SKILL.md").read_text(encoding="utf-8")


def test_init_wires_claude_and_codex_without_touching_their_other_settings(tmp_path, capsys):
    (tmp_path / "CLAUDE.md").write_text("# 项目说明\n团队约定 A\n", encoding="utf-8")
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "settings.json").write_text(json.dumps({
        "permissions": {"allow": ["Bash(ls)"]},
        "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "notify.sh"},
                                      {"type": "command", "command": "pmem hook stop --agent claude"}]}]},
    }), encoding="utf-8")
    codex = tmp_path / ".codex"
    codex.mkdir()
    (codex / "config.toml").write_text('model = "gpt-5"\n', encoding="utf-8")

    for _ in range(2):
        assert main(["init", "--root", str(tmp_path), "--agents", "auto"]) == 0

    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert claude_md.startswith("# 项目说明\n团队约定 A\n") and claude_md.count("<!-- pmem:begin -->") == 1
    assert "confirm_memory" in claude_md
    settings = json.loads((claude / "settings.json").read_text(encoding="utf-8"))
    assert settings["permissions"] == {"allow": ["Bash(ls)"]}
    stop = [h["command"] for g in settings["hooks"]["Stop"] for h in g["hooks"]]
    assert stop == ["notify.sh", "pmem hook stop --agent claude"]
    assert settings["hooks"]["PreToolUse"][0]["matcher"].startswith("^(Write|Edit")
    assert json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["pmem"]["args"] == ["serve"]
    assert (claude / "skills" / "pmem-normalize" / "SKILL.md").exists()

    toml = (codex / "config.toml").read_text(encoding="utf-8")
    assert toml.startswith('model = "gpt-5"\n') and toml.count("[mcp_servers.pmem]") == 1
    codex_hooks = json.loads((codex / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert [h["command"] for g in codex_hooks["PreToolUse"] for h in g["hooks"]] == ["pmem hook pre-tool --agent codex"]
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8").count("<!-- pmem:end -->") == 1
    out = capsys.readouterr().out
    assert "Claude Code" in out and "/hooks" in out


def test_init_only_wires_cursor_when_no_other_agent_is_present(tmp_path):
    main(["init", "--root", str(tmp_path)])
    assert not (tmp_path / "CLAUDE.md").exists() and not (tmp_path / ".codex").exists()
    main(["init", "--root", str(tmp_path), "--agents", "codex"])
    assert (tmp_path / ".codex" / "hooks.json").exists() and not (tmp_path / ".claude").exists()


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
    assert "Hooks 是旧版" not in out
    hooks = tmp_path / ".cursor" / "hooks.json"
    hooks.write_text(hooks.read_text(encoding="utf-8").replace("Read|Grep|Glob|SemanticSearch|codebase_search", "Read"),
                     encoding="utf-8")
    main(["doctor", "--root", str(tmp_path)])
    assert "Hooks 是旧版" in capsys.readouterr().out


def test_doctor_flags_uncommitted_and_scattered_entities(git_repo, capsys, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(git_repo / ".." / "cache"))
    main(["init", "--root", str(git_repo), "--type", "generic"])
    config = git_repo / ".memory" / "config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("backend: auto", "backend: none"), encoding="utf-8")
    folder = git_repo / ".memory" / "entries" / "feature.Login"
    folder.mkdir(parents=True)
    for i, entity in enumerate(["AutoPop", "AutoPopup", "Captcha"]):
        entry_id = f"01JA7K3M2X9F4Q8W6ZB1C2D{i:03d}"
        (folder / f"{entry_id}.md").write_text(
            f"---\nid: {entry_id}\nmodule: feature.Login\nentity: {entity}\nkind: conclusion\n"
            "author: a\nnote_date: '2026-10-01'\n---\n登录令牌过期后要静默刷新\n", encoding="utf-8")
    capsys.readouterr()
    main(["doctor", "--root", str(git_repo)])
    out = capsys.readouterr().out
    assert "本机有 3 条记忆未提交" in out
    assert "现行记忆 3 条（记忆文件共 3 个" in out
    assert "1 组实体名字相近" in out and "feature.Login：AutoPop / AutoPopup" in out


def test_record_takes_several_aliases_and_brief_output(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    main(["init", "--root", str(tmp_path), "--type", "generic"])
    config = tmp_path / ".memory" / "config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("backend: auto", "backend: none"), encoding="utf-8")
    capsys.readouterr()
    code = main(["record", "--root", str(tmp_path), "--module", "feature.Login", "--entity", "Token",
                 "--kind", "risk", "--content", "登录令牌过期后要静默刷新，否则会被踢回登录页",
                 "--alias", "掉登录", "被踢", "--anchor", "src/Login.ts", "--brief"])
    out = capsys.readouterr().out
    assert code == 0 and out.startswith("已写入 feature.Login / Token：")
    assert "只写了文件" in out
    entry = next((tmp_path / ".memory" / "entries" / "feature.Login").glob("*.md")).read_text(encoding="utf-8")
    assert "- 掉登录\n- 被踢" in entry
    main(["search", "--root", str(tmp_path), "--module", "feature.Login", "令牌", "--brief"])
    out = capsys.readouterr().out
    assert out.startswith("feature.Login：1 条")
    assert "- 风险｜Token｜" in out and "⚠ 需核实：src/Login.ts 已不存在" in out


def test_brief_accepts_both_related_shapes():
    from pmem.cli.brief import render_brief
    search = render_brief("search", {"ok": True, "module": "a.B", "items": [], "related": ["c.D（共同路径）"]})
    graph = render_brief("graph", {"ok": True, "module": "a.B", "topics": [],
                                   "related": [{"module": "c.D", "via": "共同路径", "entities": []}]})
    assert search.endswith("相关模块：c.D（共同路径）") and graph.endswith("相关模块：c.D（共同路径）")


def test_doctor_shows_only_recent_hook_errors(tmp_path):
    from pmem.cli.doctor_cmd import _recent_errors

    log = tmp_path / "hook-errors.log"
    log.write_text("2026-10-14 10:00:00 ERROR stop@cursor\nTraceback\nNameError: old\n"
                   "2026-10-16 09:00:00 ERROR pre-tool@cursor\nTraceback\nValueError: new\n", encoding="utf-8")
    now = time.mktime(time.strptime("2026-10-16 12:00:00", "%Y-%m-%d %H:%M:%S"))
    recent = _recent_errors(log, now)
    assert len(recent) == 1 and recent[0].endswith("ValueError: new")
    assert _recent_errors(log, now + 2 * 86400) == []


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
    main(["record", "--root", str(tmp_path), "--module", "feature.Login", "--entity", "Token", "--kind", "conclusion",
          "--content", "登录令牌过期后由拦截器静默刷新，原因是避免用户中途被踢回登录页。", "--draft-id", written["id"]])
    again = json.loads(capsys.readouterr().out)
    assert again["id"] == written["id"] and again["overwritten"] is True


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
