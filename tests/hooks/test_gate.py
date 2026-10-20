import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import pytest

from pmem.core.config import Config
from pmem.hooks.gate import cli_args, handle, may_change_unseen, shell_write_targets
from pmem.hooks.state import SessionState
from pmem.metrics.events import read_events

CONFIG = "project: {{ name: demo }}\nvcs: none\ngate: {{ mode: {mode} }}\n"
MODULES = """
categories: { gameplay: {}, economy: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }
  economy.Shop: { paths: [src/Shop/**] }
"""
ENTRY = """---
id: {id}
module: {module}
entity: Reward
kind: conclusion
status: active
author: a
note_date: '2026-10-01'
---
旧结论
"""


@pytest.fixture
def make_project(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))

    def build(mode="warn", with_memory=True) -> Path:
        root = tmp_path / "proj"
        (root / ".memory").mkdir(parents=True, exist_ok=True)
        (root / ".memory" / "config.yaml").write_text(CONFIG.format(mode=mode), encoding="utf-8")
        (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
        if with_memory:
            folder = root / ".memory" / "entries" / "gameplay.Jigsaw"
            folder.mkdir(parents=True, exist_ok=True)
            entry_id = "01JA7K3M2X9F4Q8W6ZB1C2D3E4"
            (folder / f"{entry_id}.md").write_text(ENTRY.format(id=entry_id, module="gameplay.Jigsaw"), "utf-8")
        return root

    return build


def write_payload(root: Path, rel: str, conv="c1") -> dict:
    return {
        "conversation_id": conv,
        "hook_event_name": "preToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(root / rel), "content": "x"},
    }


def search_payload(conv="c1", **args) -> dict:
    return {"conversation_id": conv, "hook_event_name": "beforeMCPExecution", "tool_name": "search_memory",
            "tool_input": json.dumps(args)}


def record_output(module: str) -> str:
    """pmem record --brief 写入成功时的输出。"""
    return f"已写入 {module} / Price：01JA7K3M2X9F4Q8W6ZB1C2D3E9（再次写入同一条时用 --draft-id 01JA7K3M2X9F4Q8W6ZB1C2D3E9）\n"


def run_shell(root: Path, command: str, output: str | None = None, conv="c1") -> dict:
    """终端命令执行前后各触发一次 Hook；返回执行前的结果。"""
    shell = {"conversation_id": conv, "tool_name": "Shell", "tool_input": {"command": command, "cwd": ""}}
    before = handle("pre-tool", shell, root)
    handle("post-tool", shell if output is None else {**shell, "tool_output": output}, root)
    return before


def search_done(root: Path, conv="c1", module="gameplay.Jigsaw", items=()) -> dict:
    """MCP 检索返回了结果（afterMCPExecution）。"""
    after = {"conversation_id": conv, "tool_name": "MCP:search_memory",
             "result_json": json.dumps({"ok": True, "module": module, "items": list(items), "server": "pmem"})}
    return handle("after-mcp", after, root)


def foreign_search_done(root: Path, items=()) -> dict:
    """别家记忆服务的同名工具返回了结果：没有 pmem 的来源标记。"""
    after = {"conversation_id": "c1", "tool_name": "search_memory",
             "result_json": json.dumps({"ok": True, "module": "gameplay.Jigsaw", "items": list(items)})}
    return handle("after-mcp", after, root)


def test_unmapped_path_is_allowed(make_project):
    root = make_project()
    assert handle("pre-tool", write_payload(root, "tools/x.py"), root)["permission"] == "allow"


def test_module_without_memories_is_allowed(make_project):
    root = make_project()
    assert handle("pre-tool", write_payload(root, "src/Shop/Shop.cs"), root)["permission"] == "allow"


def test_warn_denies_once_then_allows(make_project):
    root = make_project("warn")
    first = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)
    assert first["permission"] == "deny"
    assert 'search_memory(module="gameplay.Jigsaw")' in first["agent_message"]
    second = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)
    assert second["permission"] == "allow"


def test_block_denies_until_searched(make_project):
    root = make_project("block")
    for _ in range(2):
        assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"
    search_done(root, module="gameplay.jigsaw")
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_block_is_the_default_mode(make_project):
    root = make_project()
    (root / ".memory" / "config.yaml").write_text("project: { name: demo }\nvcs: none\n", encoding="utf-8")
    for _ in range(2):
        assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"


def test_failed_or_unanswered_search_does_not_unlock_block(make_project):
    root = make_project("block")
    mcp = {"conversation_id": "c1", "tool_name": "MCP:search_memory", "tool_input": {"module": "gameplay.Jigsaw"}}
    handle("pre-tool", mcp, root)
    handle("before-mcp", search_payload(module="gameplay.Jigsaw"), root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"
    failed = {"conversation_id": "c1", "tool_name": "MCP:search_memory",
              "result_json": json.dumps({"ok": False, "error": "index unavailable"})}
    handle("after-mcp", failed, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"


def test_block_message_explains_fallbacks(make_project):
    root = make_project("block")
    message = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["agent_message"]
    assert "pmem search --module gameplay.Jigsaw" in message
    assert "| Out-Null" in message and "检索报错同样视为查过" not in message
    assert "跳过记忆" in message


def test_search_by_path_counts_once_answered(make_project):
    root = make_project("block")
    payload = {"conversation_id": "c1", "tool_name": "MCP:search_memory", "tool_input": {"path": "src/Jigsaw/Other.cs"}}
    handle("pre-tool", payload, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"
    after = {**payload, "result_json": json.dumps({"ok": True, "module": "gameplay.Jigsaw", "resolved_from": "path",
                                                   "items": [], "server": "pmem"})}
    handle("after-mcp", after, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_successful_search_result_counts_as_searched(make_project):
    root = make_project("block")
    after = {"conversation_id": "c1", "tool_name": "MCP:search_memory",
             "result_json": json.dumps({"ok": True, "module": "gameplay.Jigsaw", "items": [], "server": "pmem"})}
    handle("after-mcp", after, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_deny_message_shown_to_agent_is_actionable(make_project):
    root = make_project("warn")
    verdict = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)
    assert 'search_memory(module="gameplay.Jigsaw")' in verdict["user_message"]
    assert "重试" in verdict["user_message"]


def test_off_mode_allows(make_project):
    root = make_project("off")
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_conversations_do_not_share_state(make_project):
    root = make_project("block")
    search_done(root, conv="c1")
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/B.cs", conv="c2"), root)["permission"] == "deny"


def test_missing_conversation_id_never_blocks(make_project):
    root = make_project("block")
    payload = write_payload(root, "src/Jigsaw/Board.cs", conv="")
    assert handle("pre-tool", payload, root)["permission"] == "allow"


def test_skip_marker_in_prompt_disables_gate(make_project):
    root = make_project("block")
    handle("prompt", {"conversation_id": "c1", "prompt": "这次跳过记忆，直接改"}, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_compact_resets_searched(make_project):
    root = make_project("block")
    search_done(root)
    handle("compact", {"conversation_id": "c1"}, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"


def test_shell_write_is_gated(make_project):
    root = make_project("block")
    payload = {"conversation_id": "c1", "tool_name": "Shell",
               "tool_input": {"command": "echo hi > src/Jigsaw/Board.cs", "cwd": ""}}
    assert handle("pre-tool", payload, root)["permission"] == "deny"
    payload["tool_input"]["command"] = "git status"
    assert handle("pre-tool", payload, root)["permission"] == "allow"


@pytest.mark.parametrize(
    ("command", "targets"),
    [
        ("echo hi > a.txt", ["a.txt"]),
        ("cat x >> logs/b.log", ["logs/b.log"]),
        ("Set-Content -Path src/A.cs -Value 1", ["src/A.cs"]),
        ("'x' | Out-File src/B.cs", ["src/B.cs"]),
        ("sed -i 's/a/b/' src/C.cs", ["src/C.cs"]),
        ("ls | tee out.txt", ["out.txt"]),
        ("Remove-Item src/D.cs", ["src/D.cs"]),
        ("rm -f src/E.cs", ["src/E.cs"]),
        ("git status 2>&1", []),
        ("cmd > $null", []),
        ("cp -r tmp/a.cs src/F.cs", ["src/F.cs"]),
        ("Copy-Item -Path tmp/a.cs -Destination src/G.cs", ["src/G.cs"]),
        ("mv src/H.cs src/I.cs", ["src/H.cs", "src/I.cs"]),
        ("git checkout -- src/J.cs", ["src/J.cs"]),
        ("git restore --staged src/K.cs", ["src/K.cs"]),
        ("git checkout main", []),
        ("python -c \"import x; open('src/L.cs', 'w').write('1')\"", ["src/L.cs"]),
        ("python -c \"print(open('src/L.cs').read())\"", []),
        ("[IO.File]::WriteAllText('src/M.cs', 'x')", ["src/M.cs"]),
        ("uv run pytest tests/test_x.py", []),
        ("uv run pmem search --module a.B", []),
        ("powershell -NoProfile -Command \"Set-Content src/Q.cs 1; Remove-Item src/R.cs\"", ["src/Q.cs", "src/R.cs"]),
        ("pwsh -c 'Out-File -FilePath src/S.cs'", ["src/S.cs"]),
        ("cmd /c \"del src\\T.cs\"", ["src\\T.cs"]),
        ("bash -c 'rm -f src/U.cs'", ["src/U.cs"]),
        ("bash -lc 'rm -f src/U1.cs'", ["src/U1.cs"]),
        ("sh -ec 'rm -f src/U2.cs'", ["src/U2.cs"]),
        ("Get-Content a | Tee-Object -FilePath src/V.cs", ["src/V.cs"]),
        ("ni src/W.cs -ItemType File", ["src/W.cs"]),
        ("powershell -Command Get-ChildItem src", []),
        ("cd src/Jigsaw; echo x > Board.cs", [os.path.join("src", "Jigsaw", "Board.cs")]),
        ("Set-Location src && Set-Content Jigsaw/A.cs 1", [os.path.join("src", "Jigsaw/A.cs")]),
        ("perl -pi -e 's/a/b/' src/Y.cs", ["src/Y.cs"]),
        ("Get-Content a | Set-Content src/Z.cs\",", ["src/Z.cs"]),
        ("$code = @'\nSet-Content src/Q.cs 1\n'@\n$code | python -", []),
        ("cat > notes.txt <<'EOF'\nrm -f src/E.cs\nEOF", ["notes.txt"]),
        # 审查找到的绕过写法
        ("echo x 1> src/A1.cs", ["src/A1.cs"]),
        ("echo x &> src/A2.cs", ["src/A2.cs"]),
        ("echo x *> src/A3.cs", ["src/A3.cs"]),
        ("echo x > 'src/A4.cs'", ["src/A4.cs"]),
        ("echo x 2> err.log", ["err.log"]),
        ("python -c \"f = lambda a: a->b\"", []),
        ("/bin/rm src/B1.cs", ["src/B1.cs"]),
        ("rm.exe src/B2.cs", ["src/B2.cs"]),
        ("sed -i s/a/b/ src/C1.cs README.md", ["src/C1.cs", "README.md"]),
        ("sed -i -e s/a/b/ src/C2.cs src/C3.cs", ["src/C2.cs", "src/C3.cs"]),
        ("perl -pie 's/a/b/' src/C4.cs src/C5.cs", ["src/C4.cs", "src/C5.cs"]),
        ("Remove-Item README.md, src/D1.cs", ["README.md", "src/D1.cs"]),
        ("Remove-Item -Path a.md,src/D2.cs", ["a.md", "src/D2.cs"]),
        ("Remove-Item -Recurse src/D3", ["src/D3"]),
        ("Set-Content src/D4.cs 'value'", ["src/D4.cs"]),
        ("cp -t src/E1 tmp/a.cs", ["src/E1"]),
        ("env A=1 rm src/F1.cs", ["src/F1.cs"]),
        ("sudo -u root rm src/F2.cs", ["src/F2.cs"]),
        ("command rm src/F3.cs", ["src/F3.cs"]),
        ("nohup env -u X sed -i s/a/b/ src/F4.cs", ["src/F4.cs"]),
        ("echo hi >| src/F5.cs", ["src/F5.cs"]),
        ("env | grep PATH", []),
        ("command -v rm", []),
    ],
)
def test_shell_write_targets(command, targets):
    assert shell_write_targets(command) == targets


def test_git_checkout_without_dashes_restores_existing_files(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "A.cs").write_text("x", encoding="utf-8")
    assert shell_write_targets("git checkout src/A.cs", str(tmp_path)) == ["src/A.cs"]
    assert shell_write_targets("git checkout main", str(tmp_path)) == []


@pytest.mark.parametrize(
    ("command", "unseen"),
    [
        ("git status; rg foo src | Select-Object -First 3", False),
        ("uv run pmem search --module a.B", False),
        ("echo hi > a.txt", False),
        ("git checkout -- src/J.cs", False),
        ("git stash pop", True),
        ("git reset --hard HEAD~1", True),
        ("git checkout src/A.cs", True),
        ("uv run ruff format src", True),
        ("npx prettier --write src", True),
        ("patch -p1 < fix.diff", True),
        ("Get-ChildItem src -Recurse | Remove-Item", True),
        ("Get-ChildItem src | ForEach-Object { Set-Content $_.FullName 'x' }", True),
        ("find src -name '*.pyc' -delete", True),
        ("find src -name '*.py'", False),
        ("svn log -l 1; svn status --xml | Select-Object -First 5", False),
        ("svn diff TileMatch/Assets", False),
        ("svn update", True),
        ("svn revert -R src", True),
        ("/bin/rm src/B1.cs", False),
        ("C:\\Windows\\System32\\sed.exe -i s/a/b/ x.cs", False),
        ("env", False),
        ("env A=1 make", True),
        ("timeout 10 rm src/x.cs", True),
    ],
)
def test_commands_that_may_change_unparsed_files(command, unseen):
    assert may_change_unseen(command) is unseen


def test_shell_write_targets_reads_scripts_and_patches(tmp_path):
    (tmp_path / "fix.py").write_text("from pathlib import Path\nPath('src/N.cs').write_text('x')\n", encoding="utf-8")
    (tmp_path / "read.py").write_text("print(open('src/O.cs').read())\n", encoding="utf-8")
    (tmp_path / "c.patch").write_text("--- a/src/P.cs\n+++ b/src/P.cs\n@@ -1 +1 @@\n-a\n+b\n", encoding="utf-8")
    assert shell_write_targets("uv run python fix.py", str(tmp_path)) == ["src/N.cs"]
    assert shell_write_targets("python read.py", str(tmp_path)) == []
    assert shell_write_targets("git apply c.patch", str(tmp_path)) == ["src/P.cs"]
    (tmp_path / "fix.ps1").write_text("Set-Content src/X.cs 1\n", encoding="utf-8")
    assert shell_write_targets("& ./fix.ps1", str(tmp_path)) == ["src/X.cs"]
    assert shell_write_targets("powershell -ExecutionPolicy Bypass -File fix.ps1", str(tmp_path)) == ["src/X.cs"]


def test_multiline_command_registers_every_pmem_call(make_project):
    root = make_project("block")
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    command = ("$t = $env:TEMP\n"
               "uv run pmem search --root . --module gameplay.Jigsaw --brief\n"
               "uv run pmem record --root . --module economy.Shop --entity Price `\n"
               "  --kind risk --content-file $t\\a.txt\r\n")
    shell = {"conversation_id": "c1", "tool_name": "Shell", "tool_input": {"command": command, "cwd": ""}}
    assert handle("pre-tool", shell, root)["permission"] == "allow"
    handle("post-tool", {**shell, "tool_output": "gameplay.Jigsaw：1 条\n" + record_output("economy.Shop")}, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"
    assert handle("stop", stop_payload(), root) == {}
    assert cli_args(command, "record") == [{"module": "economy.Shop"}]


def test_search_in_same_command_only_unlocks_that_module(make_project):
    root = make_project("block")
    mixed = {"conversation_id": "c1", "tool_name": "Shell",
             "tool_input": {"command": "pmem search --module economy.Shop; Set-Content src/Jigsaw/Board.cs x",
                            "cwd": ""}}
    assert handle("pre-tool", mixed, root)["permission"] == "deny"
    mixed["tool_input"]["command"] = "pmem search --module gameplay.Jigsaw; Set-Content src/Jigsaw/Board.cs x"
    assert handle("pre-tool", mixed, root)["permission"] == "allow"


def test_write_before_search_in_same_command_is_still_blocked(make_project):
    root = make_project("block")
    payload = {"conversation_id": "c1", "tool_name": "Shell",
               "tool_input": {"command": "Set-Content src/Jigsaw/Board.cs x; pmem search --module gameplay.Jigsaw",
                              "cwd": ""}}
    assert handle("pre-tool", payload, root)["permission"] == "deny"


@pytest.mark.parametrize(
    ("command", "targets"),
    [
        ("echo a > src/a.py & echo b > src/b.py", ["src/a.py", "src/b.py"]),
        ("Set-Content src/a.py, src/b.py x", ["src/a.py", "src/b.py"]),
        ("Set-Content -Path:src/a.py -Value x", ["src/a.py"]),
        ("pushd src; popd; rm a.py", ["a.py"]),
        ('cmd /c "cd /d src & del a.py"', [os.path.join("src", "a.py")]),
        ('bash -c "cd src && rm a.py"', [os.path.join("src", "a.py")]),
        ("Copy-Item -Path a.py src/b.py", ["src/b.py"]),
        ("cp --target-directory=src a.py", [os.path.join("src", "a.py")]),
        ("sed --in-place -e s/a/b/ src/a.py", ["src/a.py"]),
        ("cat <<EOF > src/a.py\nEOF\nrm src/b.py\nEOF", ["src/a.py", "src/b.py"]),
        ("git -C src checkout -- a.py", [os.path.join("src", "a.py")]),
        ("python -c \"open('src/a.py', 'wt').write('x')\"", ["src/a.py"]),
        ("node -e \"require('fs').unlinkSync('src/a.js')\"", ["src/a.js"]),
    ],
)
def test_shell_write_targets_edge_cases(command, targets):
    assert shell_write_targets(command) == targets


@pytest.mark.parametrize(
    ("command", "targets", "unseen"),
    [
        # 管道下游的删除：开关值不是目标，要处理的文件来自上游，必须拍快照
        ("Get-ChildItem src | Remove-Item -Recurse -ErrorAction SilentlyContinue", [], True),
        ("echo hi &rm src/a.py", ["src/a.py"], False),
        ("echo hi& rm src/a.py", ["src/a.py"], False),
        ("find . -name x -fprint src/a.py", [], True),
        ("sort -o src/a.py src/a.py", ["src/a.py"], False),
        ("git diff --output=src/a.py", ["src/a.py"], False),
        ("cp -T src/a.py src/b.py", ["src/b.py"], False),
        ("mv --target-directory=lib a.py", ["a.py", "lib"], False),
        ("sed -i --expression=s/a/b/ src/a.py src/b.py", ["src/a.py", "src/b.py"], False),
        ("sed -i -es/a/b/ src/a.py README.md", ["src/a.py", "README.md"], False),
        ('bash -c "cd docs && ls" && rm src/a.py', ["src/a.py"], True),
        ("python -c \"x = np.linalg.norm(v); df.rename(c); print('src/a.py')\"", [], True),
        ("Rename-Item -Path src/a.py -NewName b.py", ["src/a.py", os.path.join("src", "b.py")], False),
        ("git --work-tree=src checkout -- a.py", [os.path.join("src", "a.py")], False),
        ("Get-Process | Tee-Object -Variable v", [], False),
        ("echo x | tee src/a.py", ["src/a.py"], False),
    ],
)
def test_shell_parsing_found_in_review(command, targets, unseen, tmp_path):
    assert shell_write_targets(command, str(tmp_path)) == targets
    assert may_change_unseen(command) is unseen


def test_writing_into_an_existing_directory_targets_the_file(tmp_path):
    (tmp_path / "src").mkdir()
    assert shell_write_targets("cp a.py src", str(tmp_path)) == [os.path.join("src", "a.py")]
    assert shell_write_targets("New-Item -Path src -Name a.py", str(tmp_path)) == [os.path.join("src", "a.py")]


def test_long_or_heredoc_heavy_commands_parse_fast():
    started = time.perf_counter()
    shell_write_targets("python - <<PY\n" + "x = 1<<20\n" * 5000)
    shell_write_targets("cat <<abcdefghijklmnop\n" * 3000)
    shell_write_targets('python -c "' + "open(" * 20000 + '"')
    assert may_change_unseen("x" * 70_000) is True
    assert time.perf_counter() - started < 3


def test_in_command_search_only_covers_its_own_module_and_later_writes(make_project):
    root = make_project("block")
    payload = {"conversation_id": "c1", "tool_name": "Shell", "tool_input": {"cwd": "", "command": (
        "pmem search --module economy.Shop; Set-Content src/Jigsaw/Board.cs x; pmem search --module gameplay.Jigsaw")}}
    assert handle("pre-tool", payload, root)["permission"] == "deny"
    payload["tool_input"]["command"] = "pmem search --module gameplay.Jigsaw || Set-Content src/Jigsaw/Board.cs x"
    assert handle("pre-tool", payload, root)["permission"] == "deny"
    payload["tool_input"]["command"] = "pmem search --module gameplay.Jigsaw && Set-Content src/Jigsaw/Board.cs x"
    assert handle("pre-tool", payload, root)["permission"] == "allow"


def test_failed_in_command_search_is_flagged_after_the_write(make_project):
    root = make_project("block")
    command = "pmem search --module gameplay.Jigsaw --bogus; Set-Content src/Jigsaw/Board.cs x"
    pre = {"conversation_id": "c1", "tool_name": "Shell", "tool_input": {"cwd": "", "command": command}}
    assert handle("pre-tool", pre, root)["permission"] == "allow"
    post = {**pre, "hook_event_name": "postToolUse", "tool_output": "error: unrecognized arguments: --bogus"}
    assert "检索没有成功" in handle("post-tool", post, root)["additional_context"]


def test_code_literal_of_the_working_directory_is_not_a_target(tmp_path):
    code = f"python -c \"ROOT = '{tmp_path.as_posix()}'; Path(ROOT, 'out.txt').write_text('x')\""
    assert shell_write_targets(code, str(tmp_path)) == ["out.txt"]
    assert shell_write_targets("git checkout src", str(tmp_path)) == []
    (tmp_path / "src").mkdir()
    assert shell_write_targets("git checkout src", str(tmp_path)) == ["src"]


def test_record_injection_adds_conversation_and_draft(make_project):
    root = make_project()
    payload = {"conversation_id": "c1", "tool_name": "MCP:record_memory",
               "tool_input": {"module": "gameplay.Jigsaw", "entity": "Reward", "kind": "conclusion", "content": "x"}}
    first = handle("pre-tool", payload, root)
    assert first["updated_input"]["source_conversation"] == "c1"
    assert "draft_id" not in first["updated_input"]
    response = {"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E9", "module": "gameplay.Jigsaw", "entity": "Reward"}
    after = {"conversation_id": "c1", "tool_name": "record_memory", "result_json": json.dumps(response)}
    handle("after-mcp", after, root)
    second = handle("pre-tool", payload, root)
    assert second["updated_input"]["draft_id"] == "01JA7K3M2X9F4Q8W6ZB1C2D3E9"
    other = {**payload, "tool_input": {**payload["tool_input"], "entity": "Config"}}
    assert "draft_id" not in handle("pre-tool", other, root)["updated_input"]
    same = {**payload, "tool_input": {**payload["tool_input"], "entity": "reward"}}
    assert handle("pre-tool", same, root)["updated_input"]["draft_id"] == "01JA7K3M2X9F4Q8W6ZB1C2D3E9"


def test_feature_record_does_not_overwrite_a_lesson_on_the_same_entity(make_project):
    """规则要求改了模块写一条功能记录、有教训另写；两者常用同一个议题名，互相覆盖就丢了教训。"""
    root = make_project()
    lesson = {"conversation_id": "c1", "tool_name": "MCP:record_memory",
              "tool_input": {"module": "gameplay.Jigsaw", "entity": "Reward", "kind": "conclusion", "content": "x"}}
    feature = {**lesson, "tool_input": {**lesson["tool_input"], "kind": "feature"}}
    for kind, entry_id in (("conclusion", "01JA7K3M2X9F4Q8W6ZB1C2D3E9"), ("feature", "01JA7K3M2X9F4Q8W6ZB1C2D3E8")):
        assert "draft_id" not in handle("pre-tool", lesson if kind == "conclusion" else feature, root)["updated_input"]
        response = {"ok": True, "id": entry_id, "module": "gameplay.Jigsaw", "entity": "Reward", "kind": kind}
        handle("after-mcp", {"conversation_id": "c1", "tool_name": "record_memory",
                             "result_json": json.dumps(response)}, root)
    assert handle("pre-tool", lesson, root)["updated_input"]["draft_id"] == "01JA7K3M2X9F4Q8W6ZB1C2D3E9"
    assert handle("pre-tool", feature, root)["updated_input"]["draft_id"] == "01JA7K3M2X9F4Q8W6ZB1C2D3E8"


def test_record_does_not_inject_committed_draft(make_project, monkeypatch):
    root = make_project()
    draft = "01JA7K3M2X9F4Q8W6ZB1C2D3E9"
    payload = {"conversation_id": "c1", "tool_name": "MCP:record_memory",
               "tool_input": {"module": "gameplay.Jigsaw", "entity": "Reward", "kind": "conclusion", "content": "x"}}
    response = {"ok": True, "id": draft, "module": "gameplay.Jigsaw", "entity": "Reward"}
    handle("after-mcp", {"conversation_id": "c1", "tool_name": "record_memory", "result_json": json.dumps(response)},
           root)
    folder = root / ".memory/entries/gameplay.Jigsaw"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{draft}.md").write_text("x", encoding="utf-8")
    assert handle("pre-tool", payload, root)["updated_input"]["draft_id"] == draft

    class Committed:
        def is_committed(self, path):
            return True

    monkeypatch.setattr("pmem.hooks.gate.Gate.vcs", lambda self: Committed())
    assert "draft_id" not in handle("pre-tool", payload, root)["updated_input"]


def test_record_overwriting_draft_keeps_its_anchors(make_project):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Jigsaw/Board.cs")}, root)
    payload = {"conversation_id": "c1", "tool_name": "MCP:record_memory",
               "tool_input": {"module": "gameplay.Jigsaw", "entity": "Reward", "kind": "conclusion", "content": "x"}}
    assert handle("pre-tool", payload, root)["updated_input"]["anchors"] == ["src/Jigsaw/Board.cs"]
    response = {"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E9", "module": "gameplay.Jigsaw", "entity": "Reward"}
    handle("after-mcp", {"conversation_id": "c1", "tool_name": "record_memory", "result_json": json.dumps(response)},
           root)
    second = handle("pre-tool", payload, root)["updated_input"]
    assert second["draft_id"] == "01JA7K3M2X9F4Q8W6ZB1C2D3E9"
    assert "anchors" not in second


def test_after_mcp_reads_module_from_nested_response_not_input(make_project):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    response = {"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E9", "module": "economy.Shop", "entity": "Price",
                "similar": [{"id": "01JA7K3M2X9F4Q8W6ZB1C2D3E4", "entity": "Price"}]}
    wrapped = json.dumps({"content": [{"type": "text", "text": json.dumps(response, ensure_ascii=False)}]})
    after = {"conversation_id": "c1", "tool_name": "record_memory",
             "tool_input": json.dumps({"module": "gameplay.Jigsaw", "entity": "Price"}), "result_json": wrapped}
    handle("after-mcp", after, root)
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}
    failed = {**after, "result_json": json.dumps({"ok": False, "error": "x", "module": "gameplay.Jigsaw"})}
    handle("after-mcp", {**failed, "conversation_id": "c2"}, root)
    handle("edited", {"conversation_id": "c2", "file_path": str(root / "src/Jigsaw/Board.cs")}, root)
    assert "gameplay.Jigsaw" in handle("stop", {"conversation_id": "c2", "status": "completed"}, root)["followup_message"]


def test_stop_reminds_once_for_edited_modules_without_record(make_project):
    root = make_project()
    edit = {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}
    handle("edited", edit, root)
    first = handle("stop", {"conversation_id": "c1", "status": "completed"}, root)
    assert "economy.Shop" in first["followup_message"]
    assert first["followup_message"].startswith("[pmem] 本轮修改了") and "自动发给 AI" not in first["followup_message"]
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}


def test_stop_is_quiet_when_module_was_recorded(make_project):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    after = {"conversation_id": "c1", "tool_name": "record_memory",
             "result_json": json.dumps({"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E9", "module": "economy.Shop"})}
    handle("after-mcp", after, root)
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}


def test_stop_is_quiet_when_aborted(make_project):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    assert handle("stop", {"conversation_id": "c1", "status": "aborted"}, root) == {}


@pytest.mark.parametrize(
    ("command", "args"),
    [
        ("pmem search --module gameplay.Jigsaw", [{"module": "gameplay.Jigsaw"}]),
        ("cd proj; uv run pmem search --path src/a.cs", [{"path": "src/a.cs"}]),
        (r"C:\bin\pmem.exe search 奖励", [{}]),
        ("pmem search --module a.B; pmem search --module c.D", [{"module": "a.B"}, {"module": "c.D"}]),
        ("uv run --extra embed pmem search --module a.B; git add -A", [{"module": "a.B"}]),
        ("python -m pmem search --path x.cs", [{"path": "x.cs"}]),
        ("pmem list", []),
        ("echo pmem search", []),
        ("pmem search --module a.B > $null", []),
        ("pmem search --module a.B *> out.txt", []),
        ("pmem search --module a.B | Out-Null; pmem search --module c.D", [{"module": "c.D"}]),
        ("pmem search --module a.B 2>&1 | Select-String x", [{"module": "a.B"}]),
        ("pmem search --module=a.B --path=src/x.cs", [{"module": "a.B", "path": "src/x.cs"}]),
        ("pmem search --module a.B 2> $null", [{"module": "a.B"}]),
        ("pmem search --module a.B 1> out.txt", []),
        ("& pmem search --module a.B", [{"module": "a.B"}]),
        ('& "C:\\Tools\\pmem.exe" search --module a.B', [{"module": "a.B"}]),
    ],
)
def test_cli_search_args(command, args):
    assert cli_args(command, "search") == args


@pytest.mark.parametrize("text", ["看下 ./src/Jigsaw/Board.cs 的问题", "看下 src/Jigsaw/Board.cs。", r"看下 .\src\Jigsaw\Board.cs"])
def test_paths_in_question_map_to_module(make_project, text):
    from pmem.hooks.gate import Gate

    root = make_project()
    assert Gate(root, {"conversation_id": "c1"}).modules_in_text(text) == ["gameplay.Jigsaw"]


def test_discarded_output_still_counts_for_record():
    assert cli_args("pmem record --module a.B --entity X --kind risk --content x > $null", "record") == [
        {"module": "a.B"}]


def test_cli_search_with_discarded_output_does_not_unlock(make_project):
    root = make_project("block")
    shell = {"conversation_id": "c1", "tool_name": "Shell",
             "tool_input": {"command": "pmem search --module gameplay.Jigsaw | Out-Null", "cwd": ""}}
    handle("pre-tool", shell, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"


CLI_RECORD = "pmem record --module economy.Shop --entity Price --kind risk --content-file note.txt"


def test_cli_record_in_shell_silences_stop_reminder(make_project):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    assert run_shell(root, CLI_RECORD, record_output("economy.Shop"))["permission"] == "allow"
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}


def test_failed_cli_record_does_not_count(make_project):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    shell = {"conversation_id": "c1", "tool_name": "Shell", "tool_input": {"command": CLI_RECORD, "cwd": ""}}
    handle("pre-tool", shell, root)
    # 执行前只挂起，写入失败或根本没执行都不算写过
    assert "economy.Shop" in handle("stop", {"conversation_id": "c1", "status": "completed"}, root)["followup_message"]
    handle("post-tool", {**shell, "tool_output": "失败：正文 12 字，少于下限 30 字"}, root)
    events = [e["type"] for e in read_events(Config.load(root).cache_dir)]
    assert "record_call_failed" in events and "record_call" not in events


def test_every_cli_record_in_one_command_counts(make_project):
    root = make_project()
    for path in ("src/Shop/Shop.cs", "src/Jigsaw/Board.cs"):
        handle("edited", {"conversation_id": "c1", "file_path": str(root / path)}, root)
    command = ("$t=$env:TEMP; uv run pmem record --module economy.Shop --entity A --kind risk --content-file a.md; "
               "uv run pmem record --module gameplay.Jigsaw --entity B --kind risk --content-file b.md")
    output = record_output("economy.Shop") + record_output("gameplay.Jigsaw")
    assert run_shell(root, command, output)["permission"] == "allow"
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}


def test_cli_record_is_logged_for_report(make_project):
    root = make_project()
    run_shell(root, CLI_RECORD, record_output("economy.Shop"))
    events = list(read_events(Config.load(root).cache_dir))
    assert [(e["type"], e["module"], e["conv"]) for e in events] == [("record_call", "economy.Shop", "c1")]


def test_parallel_command_does_not_take_pending_cli_search(make_project):
    root = make_project("block")
    search = {"conversation_id": "c1", "tool_name": "Shell",
              "tool_input": {"command": "pmem search --module gameplay.Jigsaw", "cwd": ""}}
    handle("pre-tool", search, root)
    ls = {"conversation_id": "c1", "tool_name": "Shell", "tool_input": {"command": "ls", "cwd": ""}}
    handle("pre-tool", ls, root)
    handle("post-tool", {**ls, "tool_output": "src"}, root)
    handle("post-tool", {**search, "tool_output": "gameplay.Jigsaw：1 条"}, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_cli_search_matched_by_module_when_command_text_changes(make_project):
    root = make_project("block")
    search = {"conversation_id": "c1", "tool_name": "Shell",
              "tool_input": {"command": "pmem search --module gameplay.Jigsaw 奖励", "cwd": ""}}
    handle("pre-tool", search, root)
    garbled = {**search, "tool_input": {"command": "pmem search --module gameplay.Jigsaw 濂栧姳", "cwd": ""}}
    handle("post-tool", {**garbled, "tool_output": "gameplay.Jigsaw：1 条"}, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_parallel_cli_searches_each_unlock_their_module(make_project):
    root = make_project("block")
    jigsaw = {"conversation_id": "c1", "tool_name": "Shell",
              "tool_input": {"command": "pmem search --module gameplay.Jigsaw 甲", "cwd": ""}}
    shop = {"conversation_id": "c1", "tool_name": "Shell",
            "tool_input": {"command": "pmem search --module economy.Shop 乙", "cwd": ""}}
    handle("pre-tool", jigsaw, root)
    handle("pre-tool", shop, root)
    handle("post-tool", {**shop, "tool_input": {"command": "pmem search --module economy.Shop ?", "cwd": ""},
                         "tool_output": "economy.Shop：1 条"}, root)
    handle("post-tool", {**jigsaw, "tool_input": {"command": "pmem search --module gameplay.Jigsaw ?", "cwd": ""},
                         "tool_output": "gameplay.Jigsaw：1 条"}, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"
    assert handle("pre-tool", write_payload(root, "src/Shop/Shop.cs"), root)["permission"] == "allow"


def test_record_injection_adds_files_edited_in_module(make_project):
    root = make_project()
    for path in ("src/Shop/Shop.cs", "src/Jigsaw/Board.cs", "src/Shop/Price.cs"):
        handle("edited", {"conversation_id": "c1", "file_path": str(root / path)}, root)
    payload = {"conversation_id": "c1", "tool_name": "MCP:record_memory",
               "tool_input": {"module": "economy.Shop", "entity": "Price", "kind": "risk", "content": "x"}}
    assert handle("pre-tool", payload, root)["updated_input"]["anchors"] == ["src/Shop/Shop.cs", "src/Shop/Price.cs"]
    payload["tool_input"]["anchors"] = ["src/Shop/Shop.cs#Buy"]
    assert "anchors" not in handle("pre-tool", payload, root)["updated_input"]


def test_record_injection_skips_anchors_when_payload_was_only_partly_parsed(make_project):
    from pmem.hooks.payload import parse_payload

    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    raw = ('{"conversation_id": "c1", "tool_name": "record_memory", "tool_input": {"module": "economy.Shop", '
           '"entity": "Price", "anchors": ["src/Shop/Shop.cs#Buy"], "content": "broken \\q escape"}}')
    payload = parse_payload(raw.encode("utf-8"))
    assert payload["_partial"] and "anchors" not in payload["tool_input"]
    updated = handle("pre-tool", payload, root)["updated_input"]
    assert "anchors" not in updated


def test_partly_parsed_feature_record_does_not_take_the_lessons_draft(make_project):
    from pmem.hooks.payload import parse_payload

    root = make_project()
    response = {"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E9", "module": "gameplay.Jigsaw", "entity": "Reward",
                "kind": "conclusion"}
    handle("after-mcp", {"conversation_id": "c1", "tool_name": "record_memory", "result_json": json.dumps(response)},
           root)
    raw = ('{"conversation_id": "c1", "tool_name": "record_memory", "tool_input": {"module": "gameplay.Jigsaw", '
           '"entity": "Reward", "kind": "feature", "content": "broken \\q escape"}}')
    payload = parse_payload(raw.encode("utf-8"))
    assert payload["_partial"]
    assert "draft_id" not in handle("pre-tool", payload, root)["updated_input"]


def test_cursor_injection_returns_only_added_fields(make_project):
    """Cursor 按字段合并 updated_input；回传 Hook 读到的参数会把转码损坏的中文写回去，服务就拿乱码检索、写入。"""
    root = make_project()
    garbled = "缁撴潫鎻愰啋"
    search = {"conversation_id": "c1", "tool_name": "search_memory",
              "tool_input": {"module": "economy.Shop", "query": garbled}}
    assert handle("pre-tool", search, root)["updated_input"] == {"source_conversation": "c1"}
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    record = {"conversation_id": "c1", "tool_name": "record_memory",
              "tool_input": {"module": "economy.Shop", "entity": "Price", "kind": "risk", "content": garbled}}
    assert handle("pre-tool", record, root)["updated_input"] == {"source_conversation": "c1",
                                                                 "anchors": ["src/Shop/Shop.cs"]}


def _analysis_turn(root: Path, prompt: str, conv="c1") -> dict:
    handle("prompt", {"conversation_id": conv, "prompt": prompt}, root)
    search_done(root, conv=conv)
    return handle("stop", {"conversation_id": conv, "status": "completed"}, root)


def _last_stop(root: Path) -> dict:
    return [e for e in read_events(Config.load(root).cache_dir) if e["type"] == "stop"][-1]


def test_consulted_only_conversation_is_reminded_once(make_project):
    root = make_project()
    first = _analysis_turn(root, "拼图奖励为什么会重复发放？")
    assert "查了 gameplay.Jigsaw 的记忆" in first["followup_message"]
    assert "不要询问用户" in first["followup_message"]
    assert "无需记录" not in first["followup_message"]
    assert _last_stop(root)["analyzed"] == ["gameplay.Jigsaw"]
    assert _analysis_turn(root, "再看看") == {}


def test_consulted_reminder_does_not_need_analysis_wording(make_project):
    root = make_project()
    assert "gameplay.Jigsaw" in _analysis_turn(root, "给拼图加一个新关卡")["followup_message"]


def test_lookups_during_coding_are_not_reminded(make_project):
    root = make_project()
    search_done(root)
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    after = {"conversation_id": "c1", "tool_name": "record_memory",
             "result_json": json.dumps({"ok": True, "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E9", "module": "economy.Shop"})}
    handle("after-mcp", after, root)
    assert handle("stop", {"conversation_id": "c1", "status": "completed"}, root) == {}


def test_consulted_reminder_can_be_disabled(make_project):
    root = make_project()
    config = root / ".memory" / "config.yaml"
    text = config.read_text(encoding="utf-8").replace("mode: warn", "mode: warn, analysis_reminder: false")
    config.write_text(text, encoding="utf-8")
    assert _analysis_turn(root, "Why does the reward get granted twice?") == {}
    assert _last_stop(root)["analyzed"] == ["gameplay.Jigsaw"]


def test_non_analysis_or_recorded_conversations_are_not_counted(make_project):
    root = make_project()
    _analysis_turn(root, "给拼图加一个新关卡", conv="plain")
    assert "analyzed" not in _last_stop(root)
    handle("prompt", {"conversation_id": "rec", "prompt": "排查一下拼图报错"}, root)
    search_done(root, conv="rec")
    run_shell(root, "pmem record --module gameplay.Jigsaw --entity A --kind risk --content-file a.md",
              record_output("gameplay.Jigsaw"), conv="rec")
    handle("stop", {"conversation_id": "rec", "status": "completed"}, root)
    assert "analyzed" not in _last_stop(root)


def test_cli_search_in_shell_counts_as_searched(make_project):
    root = make_project("block")
    shell = {"conversation_id": "c1", "tool_name": "Shell",
             "tool_input": {"command": "pmem search --module gameplay.Jigsaw", "cwd": ""}}
    assert handle("pre-tool", shell, root)["permission"] == "allow"
    # 执行前只挂起，命令跑完才算查过
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"
    handle("post-tool", {**shell, "tool_output": "gameplay.Jigsaw：2 条\n- 结论｜Reward｜..."}, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_cli_search_without_visible_result_does_not_count(make_project):
    root = make_project("block")
    shell = {"conversation_id": "c1", "tool_name": "Shell",
             "tool_input": {"command": "pmem search --module gameplay.Jigsaw", "cwd": ""}}
    handle("pre-tool", shell, root)
    handle("post-tool", {**shell, "tool_output": "pmem : 无法将“pmem”项识别为 cmdlet"}, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"


def test_cli_search_after_or_is_not_counted():
    assert cli_args("true || pmem search --module gameplay.Jigsaw", "search") == []
    assert cli_args("false && pmem search --module a.B; pmem search --module c.D", "search") == [
        {"module": "a.B"}, {"module": "c.D"}]
    assert cli_args("x || y; pmem graph --module a.B", "graph") == [{"module": "a.B"}]


def test_hook_error_is_reported_once(make_project):
    root = make_project()
    cache = Config.load(root).cache_dir
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "hook-errors.log").write_text("2026-10-19 ERROR pre-tool@cursor\nNameError: boom\n", encoding="utf-8")
    read = {"conversation_id": "c1", "tool_name": "Read", "tool_input": {"path": str(root / "tools/x.py")}}
    context = handle("post-tool", read, root)["additional_context"]
    assert "NameError: boom" in context and "pmem doctor" in context
    assert "additional_context" not in handle("post-tool", read, root)


def test_hook_error_is_reported_at_stop(make_project):
    root = make_project()
    cache = Config.load(root).cache_dir
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "hook-errors.log").write_text("ValueError: bad\n", encoding="utf-8")
    assert "ValueError: bad" in handle("stop", stop_payload(), root)["followup_message"]
    assert handle("stop", stop_payload(), root) == {}


def test_search_injection_adds_conversation(make_project):
    root = make_project()
    payload = {"conversation_id": "c1", "tool_name": "MCP:search_memory", "tool_input": {"module": "gameplay.Jigsaw"}}
    assert handle("pre-tool", payload, root)["updated_input"]["source_conversation"] == "c1"


@pytest.mark.parametrize("tool_input", [{"module": "system.AdChase", "query": "插屏"}, {"query": "插屏"}])
def test_search_injection_skips_other_memory_servers(make_project, tool_input):
    root = make_project()
    payload = {"conversation_id": "c1", "tool_name": "MCP:search_memory", "tool_input": tool_input}
    assert "updated_input" not in handle("pre-tool", payload, root)


@pytest.mark.parametrize("server", [{"tool_name": "mcp__tilematch__search_memory"},
                                    {"tool_name": "search_memory", "command": "python tilematch_server.py"}])
def test_same_named_tool_of_other_server_is_ignored(make_project, server):
    root = make_project("block")
    pre = {"conversation_id": "c1", "tool_input": {"module": "gameplay.Jigsaw"}, **server}
    assert "updated_input" not in handle("pre-tool", pre, root)
    after = {**pre, "result_json": json.dumps({"ok": True, "module": "gameplay.Jigsaw", "items": []})}
    handle("after-mcp", after, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"


@pytest.mark.parametrize("items", [
    [],
    [{"id": "01JA7K3M2X9F4Q8W6ZB1C2D3ZZ", "kind": "conclusion"}],
    # 实测：别家记忆服务的同名工具返回 UUID 形式的 id
    [{"id": "518b8eb4-2846-4dc3-8413-a8ec81c47427", "module": "gameplay.Jigsaw"}],
])
def test_unmarked_search_result_does_not_count(make_project, items):
    root = make_project("block")
    foreign_search_done(root, items)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"


def test_unmarked_result_with_local_memories_counts(make_project):
    """没有来源标记的旧版 pmem 服务：返回了本仓库的记忆仍算查过。"""
    root = make_project("block")
    foreign_search_done(root, [{"id": "01JA7K3M2X9F4Q8W6ZB1C2D3E4", "kind": "conclusion"}])
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"


def test_events_are_logged_for_report(make_project):
    root = make_project("warn")
    handle("prompt", {"conversation_id": "c1", "prompt": "修一下", "composer_mode": "agent"}, root)
    handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)
    handle("before-mcp", search_payload(module="gameplay.Jigsaw"), root)
    after = {"conversation_id": "c1", "tool_name": "MCP:search_memory",
             "result_json": json.dumps({"ok": True, "module": "gameplay.Jigsaw",
                                        "items": [{"id": "01JA7K3M2X9F4Q8W6ZB1C2D3E4", "kind": "conclusion"}]})}
    handle("after-mcp", after, root)
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Jigsaw/Board.cs")}, root)
    handle("stop", {"conversation_id": "c1", "status": "completed", "input_tokens": 1000, "output_tokens": 50,
                    "transcript_path": "t.jsonl"}, root)
    events = list(read_events(Config.load(root).cache_dir))
    assert [e["type"] for e in events] == ["prompt", "gate", "mcp_search", "edit", "stop"]
    assert all(e["conv"] == "c1" for e in events)
    assert events[2]["ids"] == ["01JA7K3M2X9F4Q8W6ZB1C2D3E4"]
    stop = events[-1]
    assert stop["input_tokens"] == 1000 and stop["returned"] == ["01JA7K3M2X9F4Q8W6ZB1C2D3E4"]
    assert stop["nudged"] == ["gameplay.Jigsaw"]


# ---- 提问审查 ----

def read_payload(root: Path, rel: str, conv="c1") -> dict:
    return {"conversation_id": conv, "hook_event_name": "postToolUse", "tool_name": "Read",
            "tool_input": {"file_path": str(root / rel)}}


def add_entry(root: Path, entry_id: str, kind: str, content: str, day: str, entity="Reward", supersedes="",
              module="gameplay.Jigsaw", anchors=""):
    folder = root / ".memory" / "entries" / module
    folder.mkdir(parents=True, exist_ok=True)
    extra = f"supersedes: [{supersedes}]\n" if supersedes else ""
    extra += f"anchors: [{anchors}]\n" if anchors else ""
    text = (f"---\nid: {entry_id}\nmodule: {module}\nentity: {entity}\nkind: {kind}\nstatus: active\n"
            f"author: a\nnote_date: '{day}'\n{extra}---\n{content}\n")
    (folder / f"{entry_id}.md").write_text(text, encoding="utf-8")


def transcript(tmp_path: Path, *user_texts: str) -> str:
    path = tmp_path / "t.jsonl"
    lines = []
    for text in user_texts:
        lines.append({"role": "user", "message": {"content": [{"type": "text", "text": text}]}})
        lines.append({"role": "assistant", "message": {"content": [{"type": "text", "text": "好的"}]}})
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in lines), encoding="utf-8")
    return str(path)


def stop_payload(path: str | None = None, conv="c1", **extra) -> dict:
    return {"conversation_id": conv, "status": "completed", "transcript_path": path, **extra}


def test_reading_module_code_attaches_digest_once(make_project):
    root = make_project("block")
    first = handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)
    assert "src/Jigsaw/Board.cs 属于 gameplay.Jigsaw" in first["additional_context"]
    assert "旧结论" in first["additional_context"]
    assert handle("post-tool", read_payload(root, "src/Jigsaw/Other.cs"), root) == {}
    # 摘要不等于检索：改代码仍要先查
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"


def test_searching_inside_a_module_attaches_digest(make_project):
    root = make_project("block")
    whole = {"conversation_id": "c1", "tool_name": "Grep", "tool_input": {"pattern": "Reward"}}
    assert handle("post-tool", whole, root) == {}
    scoped = {"conversation_id": "c1", "tool_name": "Grep",
              "tool_input": {"pattern": "Reward", "path": str(root / "src/Jigsaw")}}
    context = handle("post-tool", scoped, root)["additional_context"]
    assert "你正在搜索的 src/Jigsaw 属于 gameplay.Jigsaw" in context and "旧结论" in context
    semantic = {"conversation_id": "c1", "tool_name": "SemanticSearch",
                "tool_input": {"query": "奖励", "target_directories": [str(root / "src/Jigsaw/Board.cs")]}}
    assert handle("post-tool", semantic, root) == {}


def test_stop_reviews_modules_whose_code_was_viewed_this_turn(make_project, tmp_path):
    root = make_project()
    path = tmp_path / "t.jsonl"
    lines = [
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>之前的问题</user_query>"}]}},
        {"role": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"path": str(root / "src/Shop/Shop.cs")}}]}},
        {"role": "user", "message": {"content": [{"type": "text", "text": "<user_query>奖励为什么会发两次</user_query>"}]}},
        {"role": "assistant", "message": {"content": [
            {"type": "text", "text": "我搜一下"},
            {"type": "tool_use", "name": "Grep", "input": {"pattern": "Claim", "path": str(root / "src/Jigsaw")}}]}},
    ]
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in lines), encoding="utf-8")
    message = handle("stop", stop_payload(str(path)), root)["followup_message"]
    assert "本轮看过 gameplay.Jigsaw 的代码" in message and "你的问题涉及" not in message
    assert handle("stop", stop_payload(str(path)), root) == {}


@pytest.mark.parametrize("rel", ["src/Shop/Shop.cs", "src/Jigsaw/README.md", "tools/x.py"])
def test_no_digest_without_memories_or_for_ignored_files(make_project, rel):
    root = make_project()
    assert handle("post-tool", read_payload(root, rel), root) == {}


def test_digest_marks_memories_whose_code_is_gone(make_project):
    root = make_project(with_memory=False)
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A1", "risk", "旧的奖励缓存会重复发放", "2026-09-01",
              anchors="src/Jigsaw/Gone.cs")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A2", "decision", "奖励统一由服务端发放", "2026-09-02", entity="Server")
    context = handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)["additional_context"]
    stale_line = next(line for line in context.splitlines() if "旧的奖励缓存" in line)
    assert "（⚠ 需核实）" in stale_line and "Gone.cs" not in stale_line
    assert "需核实" not in next(line for line in context.splitlines() if "服务端发放" in line)
    assert "confirm_memory" in context
    # 处理说明每个对话只给一次，上下文压缩后再给
    handle("compact", {"conversation_id": "c1"}, root)
    again = handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)["additional_context"]
    assert "confirm_memory" in again
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A3", "risk", "商店缓存会重复发放", "2026-09-03",
              anchors="src/Shop/Gone.cs", module="economy.Shop")
    shop = handle("post-tool", read_payload(root, "src/Shop/Shop.cs"), root)["additional_context"]
    assert "（⚠ 需核实）" in shop and "confirm_memory" not in shop


def test_stale_check_runs_after_session_lock_is_released(make_project, monkeypatch):
    from pmem.hooks import state as state_mod
    from pmem.hooks.gate import Gate

    root = make_project(with_memory=False)
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A2", "decision", "奖励统一由服务端发放", "2026-09-02", entity="Server")
    real = Gate.stale_problems
    free: list[bool] = []

    def probe(self, entries):
        with open(self.state.path.with_suffix(".lock"), "a+b") as fh:
            held = state_mod._try_lock(fh)
            free.append(held)
            if held:
                state_mod._unlock(fh)
        return real(self, entries)

    monkeypatch.setattr(Gate, "stale_problems", probe)
    context = handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)["additional_context"]
    assert free == [True]
    assert "服务端发放" in context and "\x00" not in context and "confirm_memory" not in context


def test_block_message_lists_pitfalls_of_the_module(make_project):
    root = make_project("block", with_memory=False)
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A1", "exclusion", "不要在客户端去重", "2026-09-01")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A2", "risk", "断线重连会重复领取", "2026-09-02", entity="Reconnect")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A3", "conclusion", "普通结论不进拦截提示", "2026-09-03", entity="Misc")
    message = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["user_message"]
    assert "已知的排除项、风险和更正" in message
    assert "排除项｜Reward｜2026-09-01：不要在客户端去重" in message
    assert "风险｜Reconnect" in message
    assert "普通结论" not in message


def test_block_message_includes_corrections_after_exclusions(make_project):
    root = make_project("block", with_memory=False)
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A1", "correction", "更正：奖励不是客户端重复发的", "2026-09-05")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A2", "exclusion", "不要在客户端去重", "2026-09-01", entity="Dedup")
    message = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["user_message"]
    assert message.index("排除项｜Dedup") < message.index("更正｜Reward")


def test_skip_is_announced_once_with_its_trigger_and_can_be_resumed(make_project):
    root = make_project("block")
    handle("prompt", {"conversation_id": "c1", "prompt": "这次跳过记忆，直接改按钮颜色"}, root)
    notice = handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)["additional_context"]
    assert "已按“跳过记忆”关闭记忆检查" in notice and "这次跳过记忆，直接改按钮颜色" in notice
    assert "“恢复记忆”" in notice
    assert handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root) == {}
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"
    handle("prompt", {"conversation_id": "c1", "prompt": "恢复记忆"}, root)
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "deny"
    assert "additional_context" in handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)


def test_block_message_has_no_pitfall_section_without_them(make_project):
    root = make_project("block")
    message = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["user_message"]
    assert "排除项和风险" not in message


def test_digest_puts_exclusions_first_and_hides_superseded(make_project):
    root = make_project(with_memory=False)
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A1", "conclusion", "最新的普通结论", "2026-10-05")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A2", "exclusion", "不要在客户端去重", "2026-09-01", entity="Dedup")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A3", "conclusion", "已被推翻的旧说法", "2026-08-01", entity="Old")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A4", "correction", "更正后的说法", "2026-09-02", entity="Old",
              supersedes="01JA7K3M2X9F4Q8W6ZB1C2D3A3")
    text = handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)["additional_context"]
    assert "现行记忆 3 条" in text
    assert text.index("排除项｜Dedup") < text.index("更正｜Old") < text.index("结论｜Reward")
    assert "已被推翻" not in text


def test_question_about_module_is_reviewed_at_stop(make_project, tmp_path):
    root = make_project()
    path = transcript(tmp_path, "<timestamp>x</timestamp>\n<user_query>\nJigsaw 的奖励为什么会重复发？\n</user_query>")
    result = handle("stop", stop_payload(path), root)
    assert "你的问题涉及 gameplay.Jigsaw" in result["followup_message"]
    assert "已核对记忆" in result["followup_message"]
    assert _last_stop(root)["review"] == ["gameplay.Jigsaw"]
    # 同一模块一个对话只追问一次
    assert handle("stop", stop_payload(path), root) == {}


def test_question_review_uses_paths_aliases_and_ignores_attachments(make_project, tmp_path):
    root = make_project()
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3S1", "risk", "商店价格缓存的风险", "2026-10-01", module="economy.Shop")
    text = "<attached_files>economy.Shop 的代码</attached_files>\n<user_query>看下 src/Jigsaw/Board.cs</user_query>"
    result = handle("stop", stop_payload(transcript(tmp_path, text)), root)
    assert "gameplay.Jigsaw" in result["followup_message"]
    assert "economy.Shop" not in result["followup_message"]


def test_no_review_when_memories_were_seen(make_project, tmp_path):
    root = make_project()
    path = transcript(tmp_path, "<user_query>Jigsaw 奖励为什么重复</user_query>")
    handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)
    assert handle("stop", stop_payload(path), root) == {}
    search_done(root, conv="c2")
    result = handle("stop", stop_payload(path, conv="c2"), root)
    assert "你的问题涉及" not in result.get("followup_message", "")


def test_global_search_results_count_as_reviewed(make_project, tmp_path):
    root = make_project()
    after = {"conversation_id": "c1", "tool_name": "MCP:search_memory",
             "result_json": json.dumps({"ok": True, "module": None, "items": [
                 {"id": "01JA7K3M2X9F4Q8W6ZB1C2D3E4", "module": "gameplay.Jigsaw", "kind": "conclusion"}]})}
    handle("after-mcp", after, root)
    path = transcript(tmp_path, "<user_query>Jigsaw 奖励为什么重复</user_query>")
    assert "你的问题涉及" not in handle("stop", stop_payload(path), root).get("followup_message", "")


@pytest.mark.parametrize("extra", [{"loop_count": 1}, {"stop_hook_active": True}])
def test_followup_turns_do_not_trigger_more_followups(make_project, tmp_path, extra):
    root = make_project()
    path = transcript(tmp_path, "<user_query>Jigsaw 奖励为什么重复</user_query>")
    assert handle("stop", stop_payload(path, **extra), root) == {}
    assert "gameplay.Jigsaw" in handle("stop", stop_payload(path), root)["followup_message"]


def test_pmem_followup_message_is_not_treated_as_a_question(make_project, tmp_path):
    root = make_project()
    path = transcript(tmp_path, "<user_query>[pmem] 本轮修改了 gameplay.Jigsaw，但还没有写研发记忆</user_query>")
    assert handle("stop", stop_payload(path), root) == {}


def test_review_falls_back_to_prompt_without_transcript(make_project):
    root = make_project()
    handle("prompt", {"conversation_id": "c1", "prompt": "check src/Jigsaw/Board.cs please"}, root)
    assert "gameplay.Jigsaw" in handle("stop", stop_payload(None), root)["followup_message"]


def test_review_combines_with_write_reminder(make_project, tmp_path):
    root = make_project()
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    path = transcript(tmp_path, "<user_query>Jigsaw 奖励为什么重复，顺便改下商店</user_query>")
    message = handle("stop", stop_payload(path), root)["followup_message"]
    assert "你的问题涉及 gameplay.Jigsaw" in message and "本轮修改了 economy.Shop" in message


def test_no_write_reminder_for_deprecated_modules(make_project):
    root = make_project()
    modules = root / ".memory" / "modules.yaml"
    modules.write_text(modules.read_text(encoding="utf-8").replace(
        "economy.Shop: { paths: [src/Shop/**] }", "economy.Shop: { paths: [src/Shop/**], status: deprecated }"),
        encoding="utf-8")
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src/Shop/Shop.cs")}, root)
    assert "本轮修改了" not in handle("stop", stop_payload(None), root).get("followup_message", "")


def test_review_can_be_disabled_and_respects_skip(make_project, tmp_path):
    root = make_project()
    path = transcript(tmp_path, "<user_query>Jigsaw 奖励为什么重复</user_query>")
    handle("prompt", {"conversation_id": "skip", "prompt": "跳过记忆，看下 Jigsaw"}, root)
    assert handle("stop", stop_payload(path, conv="skip"), root) == {}
    notice = handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs", conv="skip"), root)
    assert "跳过记忆" in notice["additional_context"]
    assert handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs", conv="skip"), root) == {}
    config = root / ".memory" / "config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace(
        "mode: warn", "mode: warn, question_review: false, read_digest: false"), encoding="utf-8")
    assert handle("stop", stop_payload(path), root) == {}
    assert handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root) == {}


def test_compaction_forgets_seen_memories(make_project):
    root = make_project()
    assert handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)
    handle("compact", {"conversation_id": "c1"}, root)
    assert handle("post-tool", read_payload(root, "src/Jigsaw/Board.cs"), root)


def test_compaction_is_logged_so_reports_can_split_repeats(make_project):
    """压缩后重新给全文是设计行为；不记下压缩，报告会把它算成去重失效。"""
    from pmem.metrics.events import read_events

    root = make_project()
    handle("compact", {"conversation_id": "c1", "trigger": "auto"}, root)
    compacts = [e for e in read_events(Config.load(root).cache_dir, 0) if e["type"] == "compact"]
    assert [(e["conv"], e.get("trigger")) for e in compacts] == [("c1", "auto")]


def test_prompt_context_agents_get_digest_at_prompt_time(make_project):
    root = make_project()
    payload = {"conversation_id": "c1", "prompt": "拼图 Jigsaw 的奖励怎么发", "prompt_context": True}
    result = handle("prompt", payload, root)
    assert result["continue"] is True and "你的问题提到了 gameplay.Jigsaw" in result["additional_context"]
    assert "additional_context" not in handle("prompt", {"conversation_id": "c2", "prompt": "Jigsaw"}, root)


# ---- 并发、现行记忆计数、终端命令的事后核对 ----

def test_parallel_hooks_do_not_lose_state_updates(tmp_path):
    cache = tmp_path / "cache"
    modules = [f"m{i}" for i in range(6)]

    def worker(module: str) -> None:
        state = SessionState(cache, "c1")
        with state.locked():
            time.sleep(0.05)
            state.add("reviewed", module)
            state.save()

    threads = [threading.Thread(target=worker, args=(m,)) for m in modules]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(SessionState(cache, "c1").data["reviewed"]) == modules


def test_only_current_memories_count(make_project):
    root = make_project("block", with_memory=False)
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A1", "conclusion", "旧说法", "2026-09-01")
    old = root / ".memory" / "entries" / "gameplay.Jigsaw" / "01JA7K3M2X9F4Q8W6ZB1C2D3A1.md"
    old.write_text(old.read_text(encoding="utf-8").replace("status: active", "status: archived"), encoding="utf-8")
    assert handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["permission"] == "allow"
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A2", "conclusion", "被替代的", "2026-09-02", entity="X")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A3", "correction", "新说法", "2026-09-03", entity="X",
              supersedes="01JA7K3M2X9F4Q8W6ZB1C2D3A2")
    message = handle("pre-tool", write_payload(root, "src/Jigsaw/Board.cs"), root)["user_message"]
    assert "已有 1 条研发记忆" in message


@pytest.fixture
def git_project(make_project):
    if shutil.which("git") is None:
        pytest.skip("需要 git")
    root = make_project("block")
    config = root / ".memory" / "config.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("vcs: none", "vcs: git"), encoding="utf-8")
    (root / "src" / "Jigsaw").mkdir(parents=True)
    (root / "src" / "Jigsaw" / "Board.cs").write_text("class Board {}\n", encoding="utf-8")
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    return root


def shell(command: str, conv="c1") -> dict:
    return {"conversation_id": conv, "tool_name": "Shell", "tool_input": {"command": command, "cwd": ""}}


def test_script_writes_with_built_paths_are_caught_after_the_fact(git_project):
    root = git_project
    (root / "gen.py").write_text("import pathlib\npathlib.Path('src', 'Jig' + 'saw', 'Board.cs').write_text('x')\n",
                                 encoding="utf-8")
    assert handle("pre-tool", shell("python gen.py"), root)["permission"] == "allow"
    (root / "src" / "Jigsaw" / "Board.cs").write_text("class Board { int x; }\n", encoding="utf-8")
    context = handle("post-tool", shell("python gen.py"), root)["additional_context"]
    assert "src/Jigsaw/Board.cs" in context and 'search_memory(module="gameplay.Jigsaw")' in context
    assert handle("post-tool", shell("python gen.py"), root) == {}
    assert "gameplay.Jigsaw" in handle("stop", stop_payload(), root)["followup_message"]


def test_after_the_fact_check_is_quiet_when_searched_or_nothing_changed(git_project):
    root = git_project
    handle("pre-tool", shell("python gen.py"), root)
    assert handle("post-tool", shell("python gen.py"), root) == {}
    search_done(root)
    handle("pre-tool", shell("python gen.py"), root)
    (root / "src" / "Jigsaw" / "Board.cs").write_text("class Board { int y; }\n", encoding="utf-8")
    assert handle("post-tool", shell("python gen.py"), root) == {}
    assert "gameplay.Jigsaw" in handle("stop", stop_payload(), root)["followup_message"]


def test_unknown_tools_that_rewrite_files_are_caught_after_the_fact(git_project):
    root = git_project
    assert handle("pre-tool", shell("uv run ruff format src"), root)["permission"] == "allow"
    (root / "src" / "Jigsaw" / "Board.cs").write_text("class Board {  }\n", encoding="utf-8")
    assert "src/Jigsaw/Board.cs" in handle("post-tool", shell("uv run ruff format src"), root)["additional_context"]


def test_committing_dirty_files_is_not_counted_as_editing_them(git_project):
    root = git_project
    (root / "src" / "Jigsaw" / "Board.cs").write_text("class Board { int c; }\n", encoding="utf-8")
    handle("pre-tool", shell("python commit.py"), root)
    for args in (["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    assert handle("post-tool", shell("python commit.py"), root) == {}
    assert handle("stop", stop_payload(), root) == {}


def test_parallel_shell_commands_keep_their_own_snapshots(git_project):
    root = git_project
    handle("pre-tool", shell("python gen.py"), root)
    handle("pre-tool", shell("uv run ruff format src"), root)
    (root / "src" / "Jigsaw" / "Board.cs").write_text("class Board { int z; }\n", encoding="utf-8")
    assert "src/Jigsaw/Board.cs" in handle("post-tool", shell("python gen.py"), root)["additional_context"]
    assert handle("post-tool", shell("uv run ruff format src"), root) == {}
    assert SessionState(Config.load(root).cache_dir, "c1").data["shell_before"] == {}


def test_read_only_command_finishing_first_does_not_take_another_commands_snapshot(git_project):
    root = git_project
    handle("pre-tool", shell("python gen.py"), root)
    assert handle("post-tool", shell("ls src"), root) == {}
    (root / "src" / "Jigsaw" / "Board.cs").write_text("class Board { int p; }\n", encoding="utf-8")
    assert "src/Jigsaw/Board.cs" in handle("post-tool", shell("python gen.py"), root)["additional_context"]


def test_deleting_a_folder_checks_the_modules_registered_under_it(make_project):
    root = make_project("block", with_memory=False)
    modules = root / ".memory" / "modules.yaml"
    modules.write_text(MODULES + "  infra.Common: { paths: [src/**] }\n", encoding="utf-8")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3B1", "conclusion", "拼图的结论", "2026-09-01")
    (root / "src" / "Jigsaw").mkdir(parents=True)
    (root / "src" / "Jigsaw" / "Board.cs").write_text("x", encoding="utf-8")
    denied = handle("pre-tool", shell("rm -rf src"), root)
    assert denied["permission"] == "deny" and "gameplay.Jigsaw" in denied["user_message"]


@pytest.mark.parametrize("command", ["rm -rf src/*", "Remove-Item src\\* -Recurse -Force", "rm -rf .", "rm -rf ./"])
def test_deleting_by_wildcard_or_project_root_checks_modules_inside(make_project, command):
    root = make_project("block")
    (root / "src" / "Jigsaw").mkdir(parents=True)
    (root / "src" / "Jigsaw" / "Board.cs").write_text("x", encoding="utf-8")
    denied = handle("pre-tool", shell(command), root)
    assert denied["permission"] == "deny" and "gameplay.Jigsaw" in denied["user_message"]


def test_wildcard_matching_no_module_file_is_allowed(make_project):
    root = make_project("block")
    (root / "a.log").write_text("x", encoding="utf-8")
    assert handle("pre-tool", shell("rm *.log"), root)["permission"] == "allow"


def test_editing_a_file_with_brackets_in_its_path_is_guarded(make_project):
    root = make_project("block")
    denied = handle("pre-tool", write_payload(root, "src/Jigsaw/[id]/page.tsx"), root)
    assert denied["permission"] == "deny" and "gameplay.Jigsaw" in denied["user_message"]


@pytest.mark.parametrize("exists", [True, False])
def test_shell_target_with_literal_brackets_is_guarded(make_project, exists):
    root = make_project("block")
    if exists:
        (root / "src" / "Jigsaw" / "[id]").mkdir(parents=True)
        (root / "src" / "Jigsaw" / "[id]" / "page.tsx").write_text("x", encoding="utf-8")
    denied = handle("pre-tool", shell('rm "src/Jigsaw/[id]/page.tsx"'), root)
    assert denied["permission"] == "deny" and "gameplay.Jigsaw" in denied["user_message"]


def test_deleting_dot_folder_checks_modules_registered_under_it(make_project):
    root = make_project("block", with_memory=False)
    modules = root / ".memory" / "modules.yaml"
    modules.write_text(MODULES + "  gameplay.Ci: { paths: [./.github/workflows/**] }\n", encoding="utf-8")
    add_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3B2", "conclusion", "CI 的结论", "2026-09-01", module="gameplay.Ci")
    (root / ".github" / "workflows").mkdir(parents=True)
    denied = handle("pre-tool", shell("rm -rf .github"), root)
    assert denied["permission"] == "deny" and "gameplay.Ci" in denied["user_message"]


def test_searching_a_folder_digests_the_module_inside_not_the_umbrella(make_project):
    root = make_project("block")
    modules = root / ".memory" / "modules.yaml"
    modules.write_text(MODULES + "  infra.Common: { paths: [src/**] }\n", encoding="utf-8")
    (root / "src" / "Jigsaw").mkdir(parents=True)
    grep = {"conversation_id": "c1", "tool_name": "Grep", "tool_input": {"pattern": "x", "path": str(root / "src/Jigsaw")}}
    assert "gameplay.Jigsaw" in handle("post-tool", grep, root)["additional_context"]


def test_corrupt_session_state_is_repaired_field_by_field(tmp_path):
    state = SessionState(tmp_path, "c1")
    state.path.parent.mkdir(parents=True, exist_ok=True)
    state.path.write_text(json.dumps({"written": [], "searched": ["a.B"], "skip": "yes"}), encoding="utf-8")
    data = SessionState(tmp_path, "c1").data
    assert data["written"] == {} and data["searched"] == ["a.B"] and data["skip"] is False
    state.path.write_text("null", encoding="utf-8")
    assert SessionState(tmp_path, "c1").data["searched"] == []


def test_cd_then_relative_write_is_gated(git_project):
    command = "cd src/Jigsaw; echo x > Board.cs"
    assert handle("pre-tool", shell(command), git_project)["permission"] == "deny"


def test_files_edited_by_tools_are_not_blamed_on_parallel_commands(git_project):
    root = git_project
    handle("pre-tool", shell("python gen.py"), root)
    (root / "src" / "Jigsaw" / "Board.cs").write_text("class Board { int t; }\n", encoding="utf-8")
    handle("edited", {"conversation_id": "c1", "file_path": str(root / "src" / "Jigsaw" / "Board.cs")}, root)
    assert handle("post-tool", shell("python gen.py"), root) == {}


def test_missing_after_snapshot_does_not_blame_every_dirty_file(git_project, monkeypatch):
    root = git_project
    (root / "src" / "Jigsaw" / "Board.cs").write_text("class Board { int d; }\n", encoding="utf-8")
    handle("pre-tool", shell("python gen.py"), root)
    from pmem.vcs.git import GitVCS
    monkeypatch.setattr(GitVCS, "dirty_files", lambda self: None)
    assert handle("post-tool", shell("python gen.py"), root) == {}


def test_slow_snapshots_pause_for_a_day(git_project, monkeypatch):
    root = git_project
    import pmem.hooks.snapshot as snapshot_module
    monkeypatch.setattr(snapshot_module, "SLOW_SNAPSHOT_SECONDS", -1)
    handle("pre-tool", shell("python gen.py"), root)
    assert (Config.load(root).cache_dir / snapshot_module.SLOW_SNAPSHOT_MARK).exists()
    # 执行前就慢的那次也不留快照，执行后不用再等一遍
    assert SessionState(Config.load(root).cache_dir, "c1").data["shell_before"] == {}
    handle("post-tool", shell("python gen.py"), root)
    handle("pre-tool", shell("python other.py"), root)
    assert SessionState(Config.load(root).cache_dir, "c1").data["shell_before"] == {}


def test_denied_command_leaves_no_snapshot(git_project):
    root = git_project
    assert handle("pre-tool", shell("uv run fmt; echo x > src/Jigsaw/Board.cs"), root)["permission"] == "deny"
    assert SessionState(Config.load(root).cache_dir, "c1").data["shell_before"] == {}
