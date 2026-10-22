import shutil
import subprocess
from pathlib import Path

import pytest


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path_factory.mktemp("pmem-cache")))
    # Hook 改到没登记的目录会拉起后台扫描进程；需要时用例自己 delenv
    monkeypatch.setenv("PMEM_NO_AUTOSYNC", "1")


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    if not shutil.which("git"):
        pytest.skip("本机没有 git")
    run(["git", "init", "-q"], tmp_path)
    run(["git", "config", "user.name", "tester"], tmp_path)
    run(["git", "config", "user.email", "tester@example.com"], tmp_path)
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    run(["git", "add", "-A"], tmp_path)
    run(["git", "commit", "-q", "-m", "init"], tmp_path)
    return tmp_path


@pytest.fixture
def svn_wc(tmp_path: Path) -> Path:
    if not (shutil.which("svn") and shutil.which("svnadmin")):
        pytest.skip("本机没有 svn")
    repo = tmp_path / "repo"
    wc = tmp_path / "wc"
    run(["svnadmin", "create", str(repo)], tmp_path)
    run(["svn", "checkout", "-q", repo.resolve().as_uri(), str(wc)], tmp_path)
    (wc / "README.md").write_text("demo\n", encoding="utf-8")
    run(["svn", "add", "-q", "README.md"], wc)
    run(["svn", "commit", "-q", "-m", "init", "--username", "tester"], wc)
    run(["svn", "update", "-q"], wc)
    return wc
