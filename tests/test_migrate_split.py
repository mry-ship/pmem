from pathlib import Path

import pytest
import yaml

from pmem.cli.main import main
from pmem.service import MemoryService

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n"
MODULES = """\
# 头注释
categories: { gameplay: {}, activity: {}, economy: {} }
modules:
  gameplay.Merge: { paths: [src/Merge/**], entities: [Board, Event] }
  economy.Shop: { paths: [src/Shop/**] }
"""
TEXT = "合成棋盘的根因结论：格子回收时没有清理引用，导致下一局复用到旧的棋子数据，需要在回收时清空。"
CODE = ["src/Merge/Core/Board.cs", "src/Merge/Event/Season.cs", "src/Shop/Shop.cs"]


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    for rel in CODE:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("class X { void Run() {} }\n", encoding="utf-8")
    return root


def record(root: Path, entity: str, anchors: list[str] | None, suffix: str = "") -> str:
    service = MemoryService(root)
    try:
        result = service.record("gameplay.Merge", entity, "conclusion", TEXT + suffix, anchors=anchors)
    finally:
        service.close()
    assert result["ok"], result
    return result["id"]


def module_of(root: Path, entry_id: str) -> str:
    return next(p.parent.name for p in (root / ".memory" / "entries").rglob(f"{entry_id}.md"))


def split(root: Path, *args: str) -> int:
    return main(["migrate", "split", "gameplay.Merge", *args, "--root", str(root)])


def test_split_by_path_moves_memories_by_anchor_and_entity(project, capsys):
    event = record(project, "Event", ["src/Merge/Event/Season.cs#Run"])
    board = record(project, "Board", ["src/Merge/Core/Board.cs#Run"])
    loose = record(project, "Event", None, "补充")
    both = record(project, "Board", ["src/Merge/Core/Board.cs", "src/Merge/Event/Season.cs"], "跨两边")

    assert split(project, "--to", "activity.MergeEvent=src/Merge/Event/**") == 0
    out = capsys.readouterr().out
    assert "分给 activity.MergeEvent 2 条" in out and "以上为预览" in out
    assert both in out and module_of(project, event) == "gameplay.Merge"

    assert split(project, "--to", "activity.MergeEvent=src/Merge/Event/**", "--apply") == 0
    assert module_of(project, event) == "activity.MergeEvent"
    assert module_of(project, loose) == "activity.MergeEvent"
    assert module_of(project, board) == "gameplay.Merge"
    assert module_of(project, both) == "gameplay.Merge"
    text = (project / ".memory" / "modules.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert text.startswith("# 头注释")
    assert data["modules"]["activity.MergeEvent"] == {"paths": ["src/Merge/Event/**"]}
    assert data["modules"]["gameplay.Merge"]["paths"] == ["src/Merge/**"]

    service = MemoryService(project)
    try:
        assert [i["id"] for i in service.search(path="src/Merge/Event/Season.cs", query="棋盘")["items"]][:1] \
            in ([event], [loose])
    finally:
        service.close()


def test_assign_overrides_and_exact_path_leaves_source(project):
    both = record(project, "Board", ["src/Merge/Core/Board.cs", "src/Merge/Event/Season.cs"])
    assert split(project, "--to", "gameplay.MergeCore=src/Merge/**", "--assign", f"{both}=gameplay.MergeCore",
                 "--apply") == 0
    data = yaml.safe_load((project / ".memory" / "modules.yaml").read_text(encoding="utf-8"))
    assert "paths" not in data["modules"]["gameplay.Merge"]
    assert module_of(project, both) == "gameplay.MergeCore"


def test_split_by_entity(project):
    event = record(project, "Event", None)
    board = record(project, "Board", None)
    assert split(project, "--by", "entity", "--to", "activity.MergeEvent=Event", "--apply") == 0
    data = yaml.safe_load((project / ".memory" / "modules.yaml").read_text(encoding="utf-8"))
    assert data["modules"]["gameplay.Merge"]["entities"] == ["Board"]
    assert data["modules"]["activity.MergeEvent"] == {"entities": ["Event"]}
    assert module_of(project, event) == "activity.MergeEvent" and module_of(project, board) == "gameplay.Merge"


@pytest.mark.parametrize(("args", "message"), [
    (["--to", "activity.MergeEvent=src/Nowhere/**"], "没有 gameplay.Merge 的代码文件"),
    (["--to", "economy.Shop=src/Shop/**"], "没有 gameplay.Merge 的代码文件"),
    (["--to", "activity.Steal=src/Shop/**"], "同时映射到"),
    (["--to", "activity.Steal=src/Merge/Event/**,src/Shop/Shop.cs"], "原本属于 economy.Shop"),
    (["--to", "activity.X=src/Merge/Event/**", "--to", "activity.Y=src/Merge/Event/**"], "同时分给了"),
    (["--to", "bad.Name=src/Merge/Event/**"], "大类"),
    (["--to", "activity.MergeEvent"], "格式不对"),
    (["--by", "entity", "--to", "activity.MergeEvent=Evnet"], "没有议题 evnet"),
    (["--to", "activity.MergeEvent=src/Merge/Event/**", "--assign", "01ABC=economy.Shop"], "--assign"),
])
def test_split_rejects_bad_requests(project, capsys, args, message):
    assert split(project, *args) == 1
    assert message in capsys.readouterr().out
    assert (project / ".memory" / "modules.yaml").read_text(encoding="utf-8") == MODULES
