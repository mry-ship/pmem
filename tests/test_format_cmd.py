import json

from pmem.cli.main import main

LONG = ("登录后偶发崩溃，原因是回调不在主线程执行，界面对象被后台线程访问。" * 3
        + "处理：1) 回调切回主线程；2) 界面关闭后丢弃回调。回归：反复登录退出不再崩溃。")


def _project(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    main(["init", "--root", str(tmp_path), "--type", "generic"])
    (tmp_path / ".memory" / "config.yaml").write_text("vcs: none\nembedding: { backend: none }\n", encoding="utf-8")


def _body(path) -> str:
    return path.read_text(encoding="utf-8").split("\n---\n", 1)[1]


def test_record_writes_long_content_as_readable_lines(tmp_path, capsys, monkeypatch):
    _project(tmp_path, monkeypatch)
    capsys.readouterr()
    main(["record", "--root", str(tmp_path), "--module", "feature.Login", "--entity", "Crash", "--kind",
          "conclusion", "--content", LONG])
    written = json.loads(capsys.readouterr().out)
    path = next((tmp_path / ".memory" / "entries").rglob(f"{written['id']}.md"))
    assert "\n  1) 回调切回主线程；\n" in _body(path)
    assert max(len(line) for line in _body(path).splitlines()) <= 120


def test_format_command_previews_then_applies(tmp_path, capsys, monkeypatch):
    _project(tmp_path, monkeypatch)
    capsys.readouterr()
    main(["record", "--root", str(tmp_path), "--module", "feature.Login", "--entity", "Crash", "--kind",
          "conclusion", "--content", "短结论：回调要切回主线程，避免界面对象被后台线程访问。"])
    written = json.loads(capsys.readouterr().out)
    path = next((tmp_path / ".memory" / "entries").rglob(f"{written['id']}.md"))
    head = path.read_text(encoding="utf-8").split("\n---\n", 1)[0]
    path.write_text(f"{head}\n---\n{LONG}\n", encoding="utf-8")

    assert main(["format", "--root", str(tmp_path)]) == 0
    assert "1 条有过长的行" in capsys.readouterr().out
    assert _body(path).strip() == LONG
    main(["format", "--root", str(tmp_path), "--apply"])
    assert "\n  2) 界面关闭后丢弃回调。\n" in _body(path)
    assert path.read_text(encoding="utf-8").startswith(head)
    capsys.readouterr()
    main(["format", "--root", str(tmp_path)])
    assert "0 条有过长的行" in capsys.readouterr().out
