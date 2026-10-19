from collections import Counter
from pathlib import Path

import pytest
import yaml

from pmem.cli.main import main
from pmem.cli.sync_cmd import apply_plan, pascal_name, plan_sync
from pmem.core.registry import ModuleRegistry

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n"
MODULES = """\
# 模块目录（文件头注释要保留）
categories: { gameplay: {}, economy: {}, infra: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Game/Jigsaw/**] }
  economy.Season: { paths: [src/Season/Spring/**, src/Season/Summer/**] }
  economy.Shop: { paths: [src/Shop/**] }
candidates:
  gameplay.Old: { paths: [src/Game/Old/**] }
third_party: [src/Plugins/Known]
"""
FILES = [
    "src/Game/Jigsaw/Board.cs", "src/Game/Old/Legacy.cs", "src/Shop/Shop.cs",
    "src/Season/Spring/S.cs", "src/Season/Summer/S.cs", "src/Season/Autumn/S.cs",
    "src/Game/Match/A.cs", "src/Game/Match/B.cs", "src/Game/Match/C.cs",
    "src/Game/Tiny/X.cs",
    "src/UI/Shop/ShopPanel.cs", "src/UI/Mail/MailPanel.cs",
    "src/Plugins/Known/K.cs", "src/Plugins/NewSdk/N.cs",
]


@pytest.fixture
def project(tmp_path) -> Path:
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    for rel in FILES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("class X {}\n", encoding="utf-8")
    return root


def registry(root: Path) -> ModuleRegistry:
    return ModuleRegistry.load(root / ".memory" / "modules.yaml")


def test_pascal_name():
    assert pascal_name("daily-reward") == "DailyReward"
    assert pascal_name("Shop") == "Shop"
    assert pascal_name("2048") is None and pascal_name("中文") is None


def test_plan_lists_new_units_variants_third_party_and_promotions(project):
    heat = Counter({"src/Game/Match/A.cs": 3})
    plan = plan_sync(project, registry(project), Counter({"gameplay.Old": 2}), heat, Counter())
    assert plan.new_modules == {"gameplay.Match": {"paths": ["src/Game/Match/**"], "origin": "sync"}}
    assert set(plan.new_candidates) == {"gameplay.Tiny", "economy.Mail"}
    assert plan.append_paths == {"economy.Season": ["src/Season/Autumn/**"], "economy.Shop": ["src/UI/Shop/**"]}
    assert plan.third_party == ["src/Plugins"]
    assert plan.promote == [("gameplay.Old", "已有 2 条记忆")]
    assert plan.idle == ["economy.Season", "economy.Shop", "gameplay.Jigsaw"]


def test_recent_changes_keep_modules_off_the_idle_list(project):
    recent = Counter({"src/Shop/Shop.cs": 1, "src/Season/Spring/S.cs": 1, "src/Game/Jigsaw/Board.cs": 1})
    plan = plan_sync(project, registry(project), Counter(), Counter(), recent)
    assert plan.idle == [] and plan.promote == []
    assert "gameplay.Match" in plan.new_candidates


def test_apply_only_appends_and_new_registry_covers_files(project):
    reg = registry(project)
    plan = plan_sync(project, reg, Counter({"gameplay.Old": 1}), Counter({"src/Game/Match/A.cs": 1}), Counter())
    data = yaml.safe_load(MODULES)
    out = apply_plan(data, plan)
    assert data == yaml.safe_load(MODULES)
    assert out["modules"]["gameplay.Jigsaw"] == data["modules"]["gameplay.Jigsaw"]
    assert out["modules"]["economy.Season"]["paths"][-1] == "src/Season/Autumn/**"
    assert "gameplay.Old" in out["modules"] and "gameplay.Old" not in out["candidates"]
    assert out["third_party"] == ["src/Plugins/Known", "src/Plugins"]
    new = ModuleRegistry(out)
    assert new.module_for_path("src/UI/Shop/ShopPanel.cs").module_id == "economy.Shop"
    assert new.module_for_path("src/Game/Tiny/X.cs").candidate
    assert new.is_excluded("src/Plugins/NewSdk/N.cs")


def test_cli_preview_then_apply(project, capsys):
    path = project / ".memory" / "modules.yaml"
    assert main(["sync", "--root", str(project)]) == 0
    out = capsys.readouterr().out
    assert "economy.Season += src/Season/Autumn/**" in out and "以上为预览" in out
    assert path.read_text(encoding="utf-8") == MODULES

    assert main(["sync", "--root", str(project), "--apply"]) == 0
    capsys.readouterr()
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# 模块目录（文件头注释要保留）")
    assert "src/Season/Autumn/**" in text and "gameplay.Tiny" in text

    assert main(["sync", "--root", str(project)]) == 0
    again = capsys.readouterr().out
    assert "新模块" not in again and "新冷候选" not in again and "追加路径" not in again
