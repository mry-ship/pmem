from pathlib import Path

import pytest

from pmem.cli.main import main
from pmem.cli.wiki_cmd import MARKER

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\n"
MODULES = """
categories: { gameplay: {}, economy: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**], aliases: [Puzzle] }
  economy.Shop: { paths: [src/Shop/**] }
"""


def write_entry(root: Path, entry_id: str, module: str, entity: str, kind: str, content: str, day: str, extra=""):
    folder = root / ".memory" / "entries" / module
    folder.mkdir(parents=True, exist_ok=True)
    text = (f"---\nid: {entry_id}\nmodule: {module}\nentity: {entity}\nkind: {kind}\nstatus: active\nauthor: a\n"
            f"note_date: '{day}'\n{extra}---\n{content}\n")
    (folder / f"{entry_id}.md").write_text(text, encoding="utf-8")


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    write_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A1", "gameplay.Jigsaw", "Reward", "conclusion", "关卡结束发奖励",
                "2026-09-01")
    write_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3A2", "gameplay.Jigsaw", "Reward", "exclusion",
                "不要在客户端去重，根因在服务端", "2026-10-01",
                "supersedes: [01JA7K3M2X9F4Q8W6ZB1C2D3A1]\nanchors: ['src/Jigsaw/Reward.cs#Claim']\n")
    write_entry(root, "01JA7K3M2X9F4Q8W6ZB1C2D3B1", "economy.Shop", "Price", "risk", "商店价格与 Jigsaw 奖励共用缓存",
                "2026-10-02", "anchors: [src/Jigsaw/Reward.cs]\n")
    return root


def test_wiki_writes_index_and_module_pages(root):
    assert main(["wiki", "--root", str(root)]) == 0
    wiki = root / ".memory" / "wiki"
    assert sorted(p.name for p in wiki.glob("*.md")) == ["economy.Shop.md", "gameplay.Jigsaw.md", "index.md"]
    index = (wiki / "index.md").read_text(encoding="utf-8")
    assert index.startswith(MARKER)
    assert "[gameplay.Jigsaw](gameplay.Jigsaw.md) | 1 | 1 | 2026-10-01" in index
    page = (wiki / "gameplay.Jigsaw.md").read_text(encoding="utf-8")
    assert "别名：Puzzle" in page and "## Reward" in page
    assert "### 排除项 · 2026-10-01 · a" in page and "不要在客户端去重" in page
    assert "[src/Jigsaw/Reward.cs](../../src/Jigsaw/Reward.cs) `Claim`" in page
    assert "历史：1 条已被替代" in page and "被 `01JA7K3M2X9F4Q8W6ZB1C2D3A2` 替代" in page
    assert "[economy.Shop](economy.Shop.md)：共享代码" in page


def test_wiki_rerun_removes_stale_generated_pages_only(root):
    wiki = root / ".memory" / "wiki"
    main(["wiki", "--root", str(root)])
    (wiki / "gameplay.Old.md").write_text(MARKER + "\n# old\n", encoding="utf-8")
    (wiki / "notes.md").write_text("手写的笔记\n", encoding="utf-8")
    main(["wiki", "--root", str(root)])
    assert not (wiki / "gameplay.Old.md").exists()
    assert (wiki / "notes.md").exists()
