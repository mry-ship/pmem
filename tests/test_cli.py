import pytest

from pmem.cli.main import main


def test_version_flag_prints_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    from pmem import __version__

    assert f"pmem {__version__}" in capsys.readouterr().out


def test_record_content_from_stdin_is_utf8_even_when_console_is_gbk(monkeypatch):
    import io
    from types import SimpleNamespace

    from pmem.cli.main import _record_content

    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO("闪退崩溃".encode()), encoding="gbk"))
    assert _record_content(SimpleNamespace(content_file=None, content="-")) == "闪退崩溃"


def test_record_content_file_accepts_utf16_and_reports_unreadable(tmp_path):
    from types import SimpleNamespace

    from pmem.cli.main import _InputError, _record_content

    utf16 = tmp_path / "a.md"
    utf16.write_bytes("闪退崩溃".encode("utf-16"))
    assert _record_content(SimpleNamespace(content_file=str(utf16))) == "闪退崩溃"
    gbk = tmp_path / "b.md"
    gbk.write_bytes("闪退崩溃".encode("gbk"))
    for path in (gbk, tmp_path / "missing.md"):
        with pytest.raises(_InputError):
            _record_content(SimpleNamespace(content_file=str(path)))
