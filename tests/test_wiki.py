import os
from datetime import datetime
from pathlib import Path

import pytest

from pmem.cli.main import main
from pmem.cli.wiki_cmd import MARKER
from pmem.service import MemoryService

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
    assert "[gameplay.Jigsaw](gameplay.Jigsaw.md) | 1 | 1 | 1 | 2026-10-01" in index
    assert (wiki / ".gitignore").read_text(encoding="utf-8") == "*\n"
    page = (wiki / "gameplay.Jigsaw.md").read_text(encoding="utf-8")
    assert "别名：Puzzle" in page and "## Reward" in page
    assert "### 排除项 · 2026-10-01 · a：不要在客户端去重，根因在服务端 · ⚠ 需核实" in page
    assert "> ⚠ 需核实：src/Jigsaw/Reward.cs 已不存在" in page
    assert "[src/Jigsaw/Reward.cs](../../src/Jigsaw/Reward.cs) `Claim`" in page
    assert "历史：1 条已被替代" in page and "被 `01JA7K3M2X9F4Q8W6ZB1C2D3A2` 替代" in page
    assert "[economy.Shop](economy.Shop.md)：共享代码" in page


def test_wiki_marks_only_memories_whose_code_changed(root):
    code = root / "src" / "Jigsaw" / "Reward.cs"
    code.parent.mkdir(parents=True)
    code.write_text("class Reward { void Claim() {} }", encoding="utf-8")
    old = datetime(2026, 9, 1).timestamp()
    os.utime(code, (old, old))
    main(["wiki", "--root", str(root)])
    page = (root / ".memory" / "wiki" / "gameplay.Jigsaw.md").read_text(encoding="utf-8")
    assert "需核实" not in page


def test_record_regenerates_wiki(root):
    service = MemoryService(root)
    try:
        result = service.record("economy.Shop", "Price", "decision", "价格统一走服务端下发，客户端只做展示，不在本地缓存价格")
    finally:
        service.close()
    assert result["ok"] and "warnings" not in result
    page = (root / ".memory" / "wiki" / "economy.Shop.md").read_text(encoding="utf-8")
    assert "价格统一走服务端下发" in page


def test_wiki_auto_off_skips_regeneration(root):
    (root / ".memory" / "config.yaml").write_text(CONFIG + "wiki: { auto: false }\n", encoding="utf-8")
    service = MemoryService(root)
    try:
        service.record("economy.Shop", "Price", "decision", "价格统一走服务端下发，客户端只做展示，不在本地缓存价格")
    finally:
        service.close()
    assert not (root / ".memory" / "wiki").exists()


def test_wiki_rerun_removes_stale_generated_pages_only(root):
    wiki = root / ".memory" / "wiki"
    main(["wiki", "--root", str(root)])
    (wiki / "gameplay.Old.md").write_text(MARKER + "\n# old\n", encoding="utf-8")
    (wiki / "notes.md").write_text("手写的笔记\n", encoding="utf-8")
    main(["wiki", "--root", str(root)])
    assert not (wiki / "gameplay.Old.md").exists()
    assert (wiki / "notes.md").exists()


def test_wiki_module_name_cannot_escape_directory(root, capsys):
    sentinel = root / "AGENTS.md"
    sentinel.write_text("keep\n", encoding="utf-8")
    folder = root / ".memory" / "entries" / "gameplay.Jigsaw"
    (folder / "01JA7K3M2X9F4Q8W6ZB1C2D3C1.md").write_text(
        "---\nid: 01JA7K3M2X9F4Q8W6ZB1C2D3C1\nmodule: ../../AGENTS\nentity: X\nkind: risk\n"
        "status: active\nauthor: a\nnote_date: '2026-10-03'\n---\n不要把这条写到仓库外。\n",
        encoding="utf-8",
    )
    assert main(["wiki", "--root", str(root)]) == 0
    assert sentinel.read_text(encoding="utf-8") == "keep\n"
    wiki = root / ".memory" / "wiki"
    assert not any(p.name == "AGENTS.md" for p in root.rglob("AGENTS.md") if p != sentinel)
    index = (wiki / "index.md").read_text(encoding="utf-8")
    assert "`../../AGENTS`" in index
    assert "](../../AGENTS.md)" not in index
    assert "../../AGENTS" in capsys.readouterr().err


def test_wiki_does_not_follow_page_symlink(root):
    wiki = root / ".memory" / "wiki"
    wiki.mkdir()
    sentinel = root / "AGENTS.md"
    sentinel.write_text("keep\n", encoding="utf-8")
    link = wiki / "gameplay.Jigsaw.md"
    try:
        link.symlink_to(sentinel)
    except OSError:
        pytest.skip("当前环境不能创建符号链接")
    assert main(["wiki", "--root", str(root)]) == 0
    assert sentinel.read_text(encoding="utf-8") == "keep\n"
    assert link.is_symlink()


def test_wiki_dir_outside_project_is_refused(root):
    (root / ".memory" / "config.yaml").write_text(CONFIG + "wiki: { dir: ../outside-wiki }\n", encoding="utf-8")
    assert main(["wiki", "--root", str(root)]) == 2
    assert not (root.parent / "outside-wiki").exists()


def test_wiki_never_overwrites_hand_written_pages(root, capsys):
    docs = root / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# 项目主页\n", encoding="utf-8")
    assert main(["wiki", "--root", str(root), "--out", "docs"]) == 1
    assert (docs / "index.md").read_text(encoding="utf-8") == "# 项目主页\n"
    assert "index.md" in capsys.readouterr().out
