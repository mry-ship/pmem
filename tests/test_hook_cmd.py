import io
import json

from pmem.cli import hook_cmd


def test_a_failing_log_after_the_answer_does_not_print_a_second_answer(tmp_path, monkeypatch, capsys):
    """两份 JSON 拼在一起 Cursor 解析不了，已给出的拦截结果会作废。"""
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text("vcs: none\n", encoding="utf-8")
    monkeypatch.chdir(root)
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b'{"conversation_id": "c1"}')))
    monkeypatch.setattr("pmem.hooks.gate.handle", lambda event, payload, root: {"permission": "deny",
                                                                                "user_message": "x"})

    def broken_log(*args, **kwargs):
        raise PermissionError("hooks.log 被占用")

    monkeypatch.setattr(hook_cmd, "_log", broken_log)
    assert hook_cmd.run_hook("pre-tool") == 0
    out = capsys.readouterr().out
    assert json.loads(out)["permission"] == "deny"
