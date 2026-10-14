import pytest

from pmem.cli.main import main


def test_version_flag_prints_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "pmem 0.1.0" in capsys.readouterr().out
