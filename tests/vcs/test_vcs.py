import os
import subprocess
from datetime import date

import pytest

from pmem.vcs.detect import detect_vcs


def run(cmd: list[str], cwd) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def test_plain_directory_is_none(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    vcs = detect_vcs(tmp_path)
    assert vcs.name == "none"
    assert vcs.revision() == "none"
    assert vcs.current_user() == "alice"
    assert vcs.is_uncommitted(tmp_path / "x.md") is True


def test_explicit_setting_wins(git_repo):
    assert detect_vcs(git_repo, "none").name == "none"


def test_unknown_setting_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="vcs"):
        detect_vcs(tmp_path, "hg")


def test_git_revision_user_and_uncommitted(git_repo):
    vcs = detect_vcs(git_repo)
    assert vcs.name == "git"
    assert vcs.revision().startswith("git:")
    assert len(vcs.revision()) > len("git:")
    assert vcs.current_user() == "tester"
    assert vcs.is_uncommitted(git_repo / "README.md") is False
    new_file = git_repo / "notes" / "a.md"
    new_file.parent.mkdir()
    new_file.write_text("x", encoding="utf-8")
    assert vcs.is_uncommitted(new_file) is True
    (git_repo / "README.md").write_text("changed\n", encoding="utf-8")
    assert vcs.is_uncommitted(git_repo / "README.md") is True


def test_git_counts_uncommitted_memories(git_repo):
    vcs = detect_vcs(git_repo)
    entries = git_repo / ".memory" / "entries"
    assert vcs.uncommitted_count(entries) == 0
    for name in ("a.md", "b.md", "c.txt"):
        path = entries / "infra.Common" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
    assert vcs.uncommitted_count(entries) == 2
    run(["git", "add", "-A"], git_repo)
    run(["git", "commit", "-q", "-m", "mem"], git_repo)
    assert vcs.uncommitted_count(entries) == 0


def test_git_detected_from_subdirectory(git_repo):
    sub = git_repo / "src" / "deep"
    sub.mkdir(parents=True)
    assert detect_vcs(sub).name == "git"


def test_svn_revision_add_and_uncommitted(svn_wc, monkeypatch):
    monkeypatch.setenv("PMEM_AUTHOR", "bob")
    vcs = detect_vcs(svn_wc)
    assert vcs.name == "svn"
    assert vcs.revision() == "svn:r1"
    assert vcs.current_user() == "bob"
    assert vcs.is_uncommitted(svn_wc / "README.md") is False
    new_file = svn_wc / ".memory" / "entries" / "infra.Common" / "a.md"
    new_file.parent.mkdir(parents=True)
    new_file.write_text("x", encoding="utf-8")
    assert vcs.is_uncommitted(new_file) is True
    vcs.add(new_file)
    assert vcs.status_code(new_file) == "A"
    assert vcs.is_uncommitted(new_file) is True


def test_svn_counts_uncommitted_memories(svn_wc):
    vcs = detect_vcs(svn_wc)
    entries = svn_wc / ".memory" / "entries"
    folder = entries / "infra.Common"
    folder.mkdir(parents=True)
    for name in ("a.md", "b.md"):
        (folder / name).write_text("x", encoding="utf-8")
    assert vcs.uncommitted_count(entries) == 2
    run(["svn", "add", "-q", "--parents", str(folder / "a.md")], svn_wc)
    assert vcs.uncommitted_count(entries) == 2


def test_plain_changed_after_uses_mtime(tmp_path):
    vcs = detect_vcs(tmp_path)
    (tmp_path / "a.ts").write_text("x", encoding="utf-8")
    (tmp_path / "old.ts").write_text("x", encoding="utf-8")
    os.utime(tmp_path / "old.ts", (946684800, 946684800))
    today = date.today().isoformat()
    assert vcs.changed_after(["a.ts", "old.ts", "gone.ts"], "2001-01-01") == {"a.ts": today}
    assert vcs.changed_after(["a.ts"], today) == {}


def test_git_changed_after_commits_and_local_edits(git_repo):
    vcs = detect_vcs(git_repo)
    (git_repo / "src").mkdir()
    (git_repo / "src" / "a.ts").write_text("x", encoding="utf-8")
    run(["git", "add", "-A"], git_repo)
    run(["git", "commit", "-q", "-m", "a"], git_repo)
    today = date.today().isoformat()
    assert vcs.changed_after(["src/a.ts", "README.md"], "2000-01-01") == {"src/a.ts": today, "README.md": today}
    assert vcs.changed_after(["src/a.ts"], today) == {}
    assert vcs.changed_after([], "2000-01-01") == {}
    (git_repo / "README.md").write_text("changed\n", encoding="utf-8")
    assert vcs.changed_after(["README.md"], "2000-01-01") == {"README.md": today}


def test_svn_lists_dirty_files_relative_to_root(svn_wc):
    vcs = detect_vcs(svn_wc)
    assert vcs.dirty_files() == []
    (svn_wc / "README.md").write_text("changed\n", encoding="utf-8")
    (svn_wc / "newdir" / "deep").mkdir(parents=True)
    (svn_wc / "newdir" / "deep" / "a.cs").write_text("x", encoding="utf-8")
    assert sorted(vcs.dirty_files()) == ["README.md", "newdir/deep/a.cs"]


def test_svn_changed_after_reads_commit_date_and_local_edits(svn_wc):
    vcs = detect_vcs(svn_wc)
    found = vcs.changed_after(["README.md", "missing.ts"], "2000-01-01")
    assert list(found) == ["README.md"]
    assert vcs.changed_after(["README.md"], "2999-01-01") == {}
    (svn_wc / "README.md").write_text("changed\n", encoding="utf-8")
    assert vcs.changed_after(["README.md"], "2000-01-01")["README.md"] == date.today().isoformat()
