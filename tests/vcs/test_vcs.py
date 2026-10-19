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


def test_svn_history_decodes_relative_url(tmp_path, monkeypatch):
    """svn info 的 relative-url 是 URL 编码的，svn log 的路径不是；不解码时中文、空格目录下的提交全部对不上。"""
    from pmem.vcs import svn

    info = "<info><entry><relative-url>^/trunk/%E6%B8%B8%E6%88%8F%20Client</relative-url></entry></info>"
    log = ("<log><logentry><date>2026-10-18T01:02:03Z</date><paths>"
           "<path kind=\"file\">/trunk/游戏 Client/src/Reward.cs</path>"
           "<path kind=\"file\">/branches/x/Other.cs</path></paths></logentry></log>")

    def fake(args, cwd, timeout=30):
        out = info if args[1] == "info" else log
        return subprocess.CompletedProcess(args, 0, out.encode("utf-8"), b"")

    monkeypatch.setattr(svn, "run_tool", fake)
    assert svn.SvnVCS(tmp_path).commits_since("2026-10-01") == [("2026-10-18", ["src/Reward.cs"])]


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


def test_svn_move_keeps_history_for_versioned_files_only(svn_wc):
    vcs = detect_vcs(svn_wc)
    old = svn_wc / ".memory" / "entries" / "gameplay.A" / "x.md"
    old.parent.mkdir(parents=True)
    old.write_text("x", encoding="utf-8")
    vcs.add(old)
    subprocess.run(["svn", "commit", "-q", "-m", "m", "--username", "t", str(svn_wc)], check=True, capture_output=True)
    new = svn_wc / ".memory" / "entries" / "gameplay.B" / "x.md"
    vcs.move(old, new)
    assert new.exists() and not old.exists() and vcs.status_code(new) == "A"

    loose = svn_wc / "loose.md"
    loose.write_text("y", encoding="utf-8")
    vcs.move(loose, svn_wc / "sub" / "loose.md")
    assert vcs.status_code(svn_wc / "sub" / "loose.md") == "?"


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


def test_git_changed_after_splits_long_path_lists(git_repo):
    """Windows 命令行约 32K 字符上限：记忆多了一次传完所有路径会失败，被当成“都没改过”。"""
    vcs = detect_vcs(git_repo)
    (git_repo / "src").mkdir()
    (git_repo / "src" / "a.ts").write_text("x", encoding="utf-8")
    run(["git", "add", "-A"], git_repo)
    run(["git", "commit", "-q", "-m", "a"], git_repo)
    padding = [f"src/{'deep/' * 20}missing{i}.ts" for i in range(400)]
    assert sum(len(p) for p in padding) > 40000
    found = vcs.changed_after([*padding, "src/a.ts"], "2000-01-01")
    assert found == {"src/a.ts": date.today().isoformat()}


def test_path_batches_respect_the_length_limit():
    from pmem.vcs.base import path_batches

    batches = path_batches(["aaaa", "bbbb", "cccc"], limit=10)
    assert batches == [["aaaa", "bbbb"], ["cccc"]]
    assert path_batches([]) == []


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
