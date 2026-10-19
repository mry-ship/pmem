from pathlib import Path

import pytest

from pmem.cli.main import main
from pmem.metrics.health import build_health, reject_reason, render
from pmem.service import MemoryService

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n"
MODULES = """
categories: { gameplay: {}, economy: {} }
modules:
  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }
  gameplay.Shop: { paths: [src/GShop/**] }
  economy.Shop: { paths: [src/Shop/**] }
"""
TEXT = "奖励重复发放的根因：配置缺字段时回退到默认奖励，导致重复发放。"


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    monkeypatch.delenv("PMEM_NO_EVENTS", raising=False)
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    (root / "src" / "Jigsaw").mkdir(parents=True)
    (root / "src" / "Jigsaw" / "Reward.cs").write_text("class Reward { void Grant() {} }\n", encoding="utf-8")
    return root


def test_reject_reasons_are_classified():
    assert reject_reason("正文长度需在 20–1200 字之间") == "字数不在允许范围"
    assert reject_reason("gameplay.Jigsaw/Reward 今天已有 5 条记忆，达到上限 5；请……带 draft_id 覆盖") == "当天同议题条数达到上限"
    assert reject_reason("未知大类 'x'") == "大类不存在"
    assert reject_reason("莫名其妙") == "其他"
    assert reject_reason("模块 economy.Shop 已废弃（只读），不再接受新记忆") == "模块已废弃（只读）"
    assert reject_reason("记忆 X 已提交到版本库，不能覆盖；请新建一条") == "草稿覆盖不被允许"


def test_health_lists_problems_for_owners(project, capsys):
    service = MemoryService(project)
    try:
        assert service.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT,
                              anchors=["src/Jigsaw/Gone.cs#Grant"])["ok"]
        assert service.record("gameplay.Jigsawx", "Reward", "conclusion", TEXT)["new_module"]
        assert service.record("gameplay.Jigsaw", "Flow", "decision", TEXT + "流程。", status="seed")["ok"]
        assert service.record("gameplay.Jigsaw", "Reward", "conclusion", "太短")["ok"] is False
        service.search(module="economy.Shop", query="价格")
        service.search(module="gameplay.Jigsaw", entity="Price", query="价格")
    finally:
        service.close()

    h = build_health(project)
    assert [u["module"] for u in h["unregistered"]] == ["gameplay.Jigsawx"]
    assert h["unregistered"][0]["similar"][0] == "gameplay.Jigsaw"
    assert ["economy.Shop", "gameplay.Shop"] in h["duplicates"]
    assert ("economy.Shop", "价格", 1) in h["misses"]
    assert ("gameplay.Jigsaw", "议题 Price（退回整模块）", 1) in h["misses"]
    assert h["stale"]["total"] == 1
    assert h["rejected"]["total"] == 1 and h["rejected"]["by_reason"] == [("字数不在允许范围", 1)]
    assert h["seeds"] == [("gameplay.Jigsaw", 1)]
    assert h["idle_modules"] is None
    assert h["duplicates"].count(["economy.Shop", "gameplay.Shop"]) == 1
    assert h["unmapped_dirs"] == []

    text = render(h)
    for title in ("未登记模块", "疑似重复模块", "检索落空热点", "可能过时的记忆", "被拒绝的写入", "待确认的种子记忆"):
        assert title in text
    assert main(["health", "--root", str(project)]) == 0
    assert "pmem 健康报告" in capsys.readouterr().out


def test_health_counts_watchdog_restarts_but_not_reloads(project):
    from pmem.core.config import Config
    from pmem.metrics.events import log_event

    cache_dir = Config.load(project).cache_dir
    log_event(cache_dir, "server_restart", kind="crash", reason="意外退出（返回码 1）")
    log_event(cache_dir, "server_restart", kind="crash", reason="意外退出（返回码 1）")
    log_event(cache_dir, "server_restart", kind="reload", reason="代码已更新")
    h = build_health(project)
    assert h["server_restarts"] == [("意外退出（返回码 1）", 2)]
    assert "MCP 服务被看门狗重启（2 次）" in render(h)


def test_health_is_quiet_when_nothing_to_do(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(
        "categories: { gameplay: {} }\nmodules:\n  gameplay.Jigsaw: { paths: [src/**] }\n", encoding="utf-8")
    assert "没有需要处理的问题" in render(build_health(root))


def test_dependency_and_build_dirs_are_not_code(tmp_path):
    from pmem.scan.lite import iter_code_files

    for rel in ("vendor/x/a.go", "Pods/A/a.m", "pkg.egg-info/a.py", "TestResults/a.cs", "src/a.go"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x", encoding="utf-8")
    assert list(iter_code_files(tmp_path)) == ["src/a.go"]


def test_memories_under_a_dotted_alias_are_strays_not_unregistered(project):
    path = project / ".memory" / "modules.yaml"
    path.write_text(MODULES.replace("gameplay.Jigsaw: { paths: [src/Jigsaw/**] }",
                                    "gameplay.Jigsaw: { paths: [src/Jigsaw/**], aliases: [gameplay.Old] }"),
                    encoding="utf-8")
    service = MemoryService(project)
    try:
        rid = service.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT)["id"]
    finally:
        service.close()
    file = project / ".memory" / "entries" / "gameplay.Jigsaw" / f"{rid}.md"
    file.write_text(file.read_text(encoding="utf-8").replace("module: gameplay.Jigsaw", "module: gameplay.Old"),
                    encoding="utf-8")
    (project / "src" / "Tools").mkdir()
    (project / "src" / "Tools" / "Build.cs").write_text("class Build {}\n", encoding="utf-8")

    h = build_health(project)
    assert h["unregistered"] == []
    assert h["strays"] == [{"id": rid, "from": "gameplay.Old", "to": "gameplay.Jigsaw"}]
    assert h["unmapped_dirs"] == [("src/Tools/Build.cs", 1)]
    assert "没有归属模块的代码目录" in render(h)
