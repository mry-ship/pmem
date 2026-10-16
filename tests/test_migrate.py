from pathlib import Path

import pytest
import yaml

from pmem.cli.main import main
from pmem.service import MemoryService

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n"
MODULES = """\
# 模块目录头注释
#   gameplay.Demo: { paths: [...] }
categories: { gameplay: {}, economy: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**], aliases: [Puzzle], entities: [Reward] }
  economy.Shop: { paths: [src/Shop/**] }
  economy.Store: { paths: [src/Store/**], entities: [Price] }
candidates:
  economy.Coupon: { paths: [src/Coupon/**] }
"""
TEXT = "奖励重复发放的根因：配置缺字段时回退到默认奖励，导致重复发放。"


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    return root


def record(root: Path, module: str, text: str = TEXT) -> str:
    service = MemoryService(root)
    try:
        result = service.record(module, "Reward", "conclusion", text)
    finally:
        service.close()
    assert result["ok"], result
    return result["id"]


def search(root: Path, module: str) -> dict:
    service = MemoryService(root)
    try:
        return service.search(module=module, query="奖励")
    finally:
        service.close()


def modules_yaml(root: Path) -> tuple[str, dict]:
    text = (root / ".memory" / "modules.yaml").read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def test_rename_previews_then_moves_memories_and_keeps_old_name_as_alias(project, capsys):
    rid = record(project, "gameplay.Jigsaw")
    assert main(["migrate", "rename", "gameplay.Jigsaw", "gameplay.Puzzle2", "--root", str(project)]) == 0
    out = capsys.readouterr().out
    assert "要搬动的记忆文件 1 个" in out and "预览" in out
    assert modules_yaml(project)[0] == MODULES

    assert main(["migrate", "rename", "gameplay.Jigsaw", "gameplay.Puzzle2", "--root", str(project), "--apply"]) == 0
    text, data = modules_yaml(project)
    assert text.startswith("# 模块目录头注释\n#   gameplay.Demo")
    assert list(data["modules"]) == ["gameplay.Puzzle2", "economy.Shop", "economy.Store"]
    assert data["modules"]["gameplay.Puzzle2"]["aliases"] == ["Puzzle", "gameplay.Jigsaw", "Jigsaw"]
    assert (project / ".memory" / "entries" / "gameplay.Puzzle2" / f"{rid}.md").exists()
    assert not (project / ".memory" / "entries" / "gameplay.Jigsaw").exists()

    found = search(project, "gameplay.Jigsaw")
    assert found["module"] == "gameplay.Puzzle2" and [i["id"] for i in found["items"]] == [rid]
    new = record(project, "Jigsaw", TEXT + "又一条。")
    assert (project / ".memory" / "entries" / "gameplay.Puzzle2" / f"{new}.md").exists()


def test_rename_refuses_existing_names(project, capsys):
    assert main(["migrate", "rename", "economy.Shop", "economy.Store", "--root", str(project)]) == 1
    assert main(["migrate", "rename", "economy.Shop", "gameplay.Puzzle", "--root", str(project)]) == 1
    assert main(["migrate", "rename", "economy.Shop", "nope.Shop", "--root", str(project)]) == 1
    assert "无法迁移" in capsys.readouterr().out
    assert main(["migrate", "rename", "economy.Shop", "economy.Coupon", "--root", str(project)]) == 1
    assert "冷候选" in capsys.readouterr().out


def test_rename_updates_parent_and_merged_pointers(project):
    path = project / ".memory" / "modules.yaml"
    path.write_text(MODULES.replace("economy.Store: { paths: [src/Store/**], entities: [Price] }",
                                    "economy.Store: { paths: [src/Store/**], parent: economy.Shop }\n"
                                    "  economy.Mall: { status: 'merged_into:economy.Shop' }"), encoding="utf-8")
    assert main(["migrate", "rename", "economy.Shop", "economy.Market", "--root", str(project), "--apply"]) == 0
    data = modules_yaml(project)[1]["modules"]
    assert data["economy.Store"]["parent"] == "economy.Market"
    assert data["economy.Mall"]["status"] == "merged_into:economy.Market"


def test_tidy_refuses_to_overwrite_a_file_with_the_same_id(project, capsys):
    rid = record(project, "gameplay.Jigsaw")
    folder = project / ".memory" / "entries"
    (folder / "gameplay.Puzzle").mkdir()
    text = (folder / "gameplay.Jigsaw" / f"{rid}.md").read_text(encoding="utf-8")
    (folder / "gameplay.Puzzle" / f"{rid}.md").write_text(text.replace("module: gameplay.Jigsaw", "module: Puzzle"),
                                                          encoding="utf-8")
    assert main(["migrate", "tidy", "--root", str(project), "--apply"]) == 1
    assert "已存在" in capsys.readouterr().out
    assert "module: Puzzle" in (folder / "gameplay.Puzzle" / f"{rid}.md").read_text(encoding="utf-8")


def test_merge_moves_paths_and_memories_into_target(project):
    rid = record(project, "economy.Shop")
    assert main(["migrate", "merge", "economy.Shop", "economy.Store", "--root", str(project), "--apply"]) == 0
    data = modules_yaml(project)[1]["modules"]
    assert data["economy.Shop"] == {"status": "merged_into:economy.Store"}
    assert data["economy.Store"]["paths"] == ["src/Store/**", "src/Shop/**"]
    assert [i["id"] for i in search(project, "economy.Store")["items"]] == [rid]
    assert [i["id"] for i in search(project, "economy.Shop")["items"]] == [rid]
    assert main(["migrate", "merge", "economy.Shop", "economy.Store", "--root", str(project)]) == 1


def test_merge_unregistered_and_candidate_modules(project):
    typo = record(project, "economy.Shopp")
    record(project, "economy.Coupon")
    assert main(["migrate", "merge", "economy.Shopp", "economy.Shop", "--root", str(project), "--apply"]) == 0
    assert main(["migrate", "merge", "economy.Coupon", "economy.Shop", "--root", str(project), "--apply"]) == 0
    data = modules_yaml(project)[1]
    assert data["modules"]["economy.Shop"]["aliases"] == ["economy.Shopp", "economy.Coupon"]
    assert data["modules"]["economy.Shop"]["paths"] == ["src/Shop/**", "src/Coupon/**"]
    assert data["candidates"] == {}
    assert typo in [i["id"] for i in search(project, "economy.Shop")["items"]]
    assert len(search(project, "economy.Shop")["items"]) == 2


def test_tidy_moves_memories_left_under_an_alias(project, capsys):
    assert main(["migrate", "tidy", "--root", str(project)]) == 0
    assert "没有需要搬动" in capsys.readouterr().out
    rid = record(project, "gameplay.Jigsaw")
    folder = project / ".memory" / "entries"
    (folder / "gameplay.Puzzle").mkdir()
    (folder / "gameplay.Jigsaw" / f"{rid}.md").replace(folder / "gameplay.Puzzle" / f"{rid}.md")
    text = (folder / "gameplay.Puzzle" / f"{rid}.md").read_text(encoding="utf-8")
    (folder / "gameplay.Puzzle" / f"{rid}.md").write_text(text.replace("module: gameplay.Jigsaw", "module: Puzzle"),
                                                          encoding="utf-8")
    assert main(["migrate", "tidy", "--root", str(project), "--apply"]) == 0
    assert "Puzzle → gameplay.Jigsaw" in capsys.readouterr().out
    assert (folder / "gameplay.Jigsaw" / f"{rid}.md").exists()
    assert "module: gameplay.Jigsaw" in (folder / "gameplay.Jigsaw" / f"{rid}.md").read_text(encoding="utf-8")
