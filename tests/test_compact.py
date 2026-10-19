from pathlib import Path

import pytest

from pmem.cli.main import main
from pmem.service import MemoryService

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwrite: { max_per_day_per_entity: 3 }\n"
MODULES = """
categories: { gameplay: {}, economy: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }
  economy.Shop: { paths: [src/Shop/**] }
"""


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    return root


@pytest.fixture
def svc(project):
    service = MemoryService(project)
    yield service
    service.close()


def fill(svc, module: str, entity: str, n: int) -> list[str]:
    ids = []
    for i in range(n):
        name = entity if i % 2 == 0 else entity.lower()
        result = svc.record(module, name, "conclusion", f"第 {i} 次迭代的结论：因为配置缺字段导致奖励重复发放。",
                            anchors=[f"src/Jigsaw/F{i % 2}.cs"], draft_id=None)
        assert result["ok"], result
        ids.append(result["id"])
    return ids


def test_groups_are_listed_by_size_with_case_insensitive_entity(svc):
    ids = fill(svc, "gameplay.Jigsaw", "Reward", 3)
    fill(svc, "economy.Shop", "Price", 2)
    result = svc.compact_groups(min_size=2)
    assert [(g["module"], g["count"]) for g in result["groups"]] == [("gameplay.Jigsaw", 3), ("economy.Shop", 2)]
    assert result["memories"] == 5
    assert svc.compact_groups(module="gameplay.Jigsaw", min_size=2)["memories"] == 3
    group = svc.compact_group("gameplay.Jigsaw", "reward")
    assert [i["id"] for i in group["items"]] == ids


def test_merge_hides_fragments_skips_daily_cap_and_inherits_anchors(svc):
    ids = fill(svc, "gameplay.Jigsaw", "Reward", 3)
    merged = svc.record("gameplay.Jigsaw", "Reward", "conclusion",
                        "奖励重复发放的根因：配置缺字段时回退到默认奖励，合并自 3 条记忆。", supersedes=ids)
    assert merged["ok"], merged
    assert "warnings" not in merged
    entry = svc.index.find(merged["id"])
    assert entry.supersedes == ids and entry.anchors == ["src/Jigsaw/F0.cs", "src/Jigsaw/F1.cs"]
    assert svc.compact_groups(min_size=2)["groups"] == []
    found = svc.search(module="gameplay.Jigsaw", query="奖励重复")
    assert [i["id"] for i in found["items"]] == [merged["id"]]


def test_long_merge_is_not_hinted_as_too_long(svc):
    ids = fill(svc, "gameplay.Jigsaw", "Reward", 2)
    long_text = "奖励重复发放的根因是配置缺字段，" + "细节" * 400
    assert "hints" not in svc.record("gameplay.Jigsaw", "Reward", "conclusion", long_text, supersedes=ids,
                                     aliases=["领奖"], summary="奖励重复发放的根因是配置缺字段",
                                     verify="配置删掉 reward 字段后领奖只发一次")
    assert "超过建议" in "".join(svc.record("economy.Shop", "Price", "conclusion", long_text)["hints"])


def test_daily_cap_still_applies_without_supersedes(svc):
    fill(svc, "gameplay.Jigsaw", "Reward", 3)
    assert svc.record("gameplay.Jigsaw", "Reward", "conclusion", "第四条结论：因为缓存未清理导致重复发放。")["ok"] is False


def test_compact_cli_lists_groups_and_prints_merge_command(svc, project, capsys):
    ids = fill(svc, "gameplay.Jigsaw", "Reward", 3)
    capsys.readouterr()
    assert main(["compact", "--root", str(project), "--min", "3"]) == 0
    assert "gameplay.Jigsaw / Reward：3 条" in capsys.readouterr().out
    assert main(["compact", "--root", str(project), "--module", "Jigsaw", "--entity", "reward"]) == 0
    out = capsys.readouterr().out
    assert all(f"--supersedes {i}" in out for i in ids)
    assert out.index(ids[0]) < out.index(ids[2])
    assert main(["compact", "--root", str(project), "--module", "economy.Shop", "--entity", "Price"]) == 1


def test_doctor_suggests_compacting_until_merged(project, capsys):
    config = project / ".memory" / "config.yaml"
    config.write_text(CONFIG.replace("max_per_day_per_entity: 3", "max_per_day_per_entity: 10"), encoding="utf-8")
    service = MemoryService(project)
    try:
        ids = fill(service, "gameplay.Jigsaw", "Reward", 5)
    finally:
        service.close()
    capsys.readouterr()
    main(["doctor", "--root", str(project)])
    assert "1 个议题各积累了 5 条以上记忆（共 5 条）" in capsys.readouterr().out

    service = MemoryService(project)
    try:
        assert service.record("gameplay.Jigsaw", "Reward", "conclusion",
                              "奖励重复发放的根因：配置缺字段，合并自 5 条记忆。", supersedes=ids)["ok"]
    finally:
        service.close()
    main(["doctor", "--root", str(project)])
    assert "个议题各积累了" not in capsys.readouterr().out
