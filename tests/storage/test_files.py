import pytest

from pmem.core.entry import Entry
from pmem.storage.files import FilesStorage, StorageError
from pmem.vcs.detect import detect_vcs


def make_entry(entry_id="01JA7K3M2X9F4Q8W6ZB1C2D3E4", author="alice", content="结论正文", **kw):
    fields = {
        "id": entry_id,
        "module": "gameplay.Jigsaw",
        "entity": "Reward",
        "kind": "conclusion",
        "content": content,
        "note_date": "2026-10-14",
        "author": author,
    }
    fields.update(kw)
    return Entry(**fields)


@pytest.fixture
def storage(tmp_path):
    return FilesStorage(tmp_path, detect_vcs(tmp_path, "none"))


def test_write_creates_module_folder_and_file(storage, tmp_path):
    result = storage.write(make_entry())
    expected = tmp_path / ".memory" / "entries" / "gameplay.Jigsaw" / "01JA7K3M2X9F4Q8W6ZB1C2D3E4.md"
    assert result.path == expected
    assert result.overwritten is False
    assert expected.read_bytes().startswith(b"---\n")
    assert b"\r\n" not in expected.read_bytes()


def test_iter_all_and_get_read_back(storage):
    storage.write(make_entry())
    storage.write(make_entry(entry_id="01JA7K3M2X9F4Q8W6ZB1C2D3E5", module="economy.Shop"))
    ids = sorted(e.id for _, e in storage.iter_all())
    assert ids == ["01JA7K3M2X9F4Q8W6ZB1C2D3E4", "01JA7K3M2X9F4Q8W6ZB1C2D3E5"]
    assert storage.get("01JA7K3M2X9F4Q8W6ZB1C2D3E5").module == "economy.Shop"
    assert storage.get("NOPE") is None


def test_corrupt_file_is_skipped_with_warning(storage, tmp_path):
    storage.write(make_entry())
    bad = tmp_path / ".memory" / "entries" / "gameplay.Jigsaw" / "BROKEN.md"
    bad.write_text("没有头", encoding="utf-8")
    entries = list(storage.iter_all())
    assert len(entries) == 1
    assert any("BROKEN.md" in w for w in storage.warnings)


def test_draft_overwrite_by_same_author_when_uncommitted(storage):
    storage.write(make_entry())
    result = storage.write(make_entry(content="更新后的结论"), draft_id="01JA7K3M2X9F4Q8W6ZB1C2D3E4")
    assert result.overwritten is True
    assert storage.get("01JA7K3M2X9F4Q8W6ZB1C2D3E4").content == "更新后的结论"


def test_draft_overwrite_by_other_author_is_rejected(storage):
    storage.write(make_entry())
    with pytest.raises(StorageError, match="supersedes"):
        storage.write(make_entry(author="bob"), draft_id="01JA7K3M2X9F4Q8W6ZB1C2D3E4")


def test_draft_overwrite_of_missing_entry_is_rejected(storage):
    with pytest.raises(StorageError, match="不存在"):
        storage.write(make_entry(), draft_id="01JA7K3M2X9F4Q8W6ZB1C2D3E9")


def test_draft_overwrite_of_committed_file_is_rejected(git_repo):
    storage = FilesStorage(git_repo, detect_vcs(git_repo))
    result = storage.write(make_entry(author="tester"))
    import subprocess

    subprocess.run(["git", "add", "-A"], cwd=git_repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "m"], cwd=git_repo, check=True)
    assert result.path.exists()
    with pytest.raises(StorageError, match="已提交"):
        storage.write(make_entry(author="tester"), draft_id="01JA7K3M2X9F4Q8W6ZB1C2D3E4")


def test_svn_auto_add_on_write(svn_wc, monkeypatch):
    monkeypatch.setenv("PMEM_AUTHOR", "bob")
    vcs = detect_vcs(svn_wc)
    storage = FilesStorage(svn_wc, vcs, svn_auto_add=True)
    result = storage.write(make_entry(author="bob"))
    assert vcs.status_code(result.path) == "A"
