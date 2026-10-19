import pytest

from pmem.cli.main import main


def test_version_flag_prints_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "pmem 0.1.0" in capsys.readouterr().out


def test_record_content_from_stdin_is_utf8_even_when_console_is_gbk(monkeypatch):
    import io
    from types import SimpleNamespace

    from pmem.cli.main import _record_content

    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO("闪退崩溃".encode()), encoding="gbk"))
    assert _record_content(SimpleNamespace(content_file=None, content="-")) == "闪退崩溃"
