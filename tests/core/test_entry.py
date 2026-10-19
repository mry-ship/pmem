import pytest

from pmem.core.entry import Entry


def make_entry(**overrides):
    fields = {
        "id": "01JA7K3M2X9F4Q8W6ZB1C2D3E4",
        "module": "gameplay.Jigsaw",
        "entity": "Reward",
        "kind": "exclusion",
        "content": "排除：奖励重复发放不是网络重试导致的，日志中重试次数为 0。",
        "note_date": "2026-10-14",
        "author": "zhangsan",
        "revision": "git:3f2a9c1",
        "supersedes": ["01J9ZZ0000000000000000000A"],
        "anchors": ["Assets/Game/Jigsaw/JigsawReward.cs#Grant"],
        "source_conversation": "conv-1",
    }
    fields.update(overrides)
    return Entry(**fields)


def test_markdown_round_trip_keeps_all_fields():
    entry = make_entry()
    parsed = Entry.from_markdown(entry.to_markdown())
    assert parsed == entry


def test_unknown_front_matter_fields_survive_rewrite():
    text = make_entry().to_markdown().replace(
        "note_date:", "reviewed: {by: lisi, at: '2026-11-01'}\npriority: 2\nnote_date:", 1)
    entry = Entry.from_markdown(text)
    entry.status, entry.verified = "archived", "2026-10-20"
    again = Entry.from_markdown(entry.to_markdown())
    assert again.extra == {"reviewed": {"by": "lisi", "at": "2026-11-01"}, "priority": 2}
    assert again.status == "archived" and again.verified == "2026-10-20"


def test_markdown_starts_with_front_matter_and_ends_with_content():
    text = make_entry().to_markdown()
    assert text.startswith("---\n")
    assert text.rstrip().endswith("日志中重试次数为 0。")


def test_optional_fields_default_to_empty():
    entry = make_entry(supersedes=[], anchors=[], source_conversation=None)
    parsed = Entry.from_markdown(entry.to_markdown())
    assert parsed.supersedes == []
    assert parsed.anchors == []
    assert parsed.source_conversation is None


def test_invalid_kind_is_rejected():
    with pytest.raises(ValueError, match="kind"):
        make_entry(kind="note")


def test_invalid_status_is_rejected():
    with pytest.raises(ValueError, match="status"):
        make_entry(status="deleted")


def test_text_without_front_matter_is_rejected():
    with pytest.raises(ValueError, match="YAML 头"):
        Entry.from_markdown("只有正文")


def test_crlf_line_endings_are_accepted():
    text = make_entry().to_markdown().replace("\n", "\r\n")
    assert Entry.from_markdown(text).entity == "Reward"
