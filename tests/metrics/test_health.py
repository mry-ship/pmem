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
    assert reject_reason("措辞随便改了", "module_deprecated") == "模块已废弃（只读）"
    assert reject_reason("正文长度需在 20–1200 字之间", "unknown_code") == "其他"


def test_every_record_rejection_carries_a_known_code(project):
    from pmem.metrics.health import REJECT_CODES

    service = MemoryService(project)
    try:
        cases = [
            service.record("gameplay.Jigsaw", "Reward", "conclusion", "太短"),
            service.record("gameplay.Jigsaw", "Reward", "guess", TEXT),
            service.record("gameplay.Jigsaw", "", "conclusion", TEXT),
            service.record("nope.Jigsaw", "Reward", "conclusion", TEXT),
            service.record("Unknown", "Reward", "conclusion", TEXT),
            service.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT, status="archived"),
            service.record("gameplay.Jigsaw", "Reward", "conclusion", TEXT, draft_id="01ARZ3NDEKTSV4RRFFQ69G5FAV"),
        ]
    finally:
        service.close()
    assert [c["code"] for c in cases] == ["content_length", "kind_invalid", "entity_missing", "category_unknown",
                                          "module_invalid", "status_invalid", "draft_forbidden"]
    assert all(c["code"] in REJECT_CODES for c in cases)
    h = build_health(project)
    assert ("草稿覆盖不被允许", 1) in h["rejected"]["by_reason"] and ("其他", 1) not in h["rejected"]["by_reason"]


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


def test_health_names_unregistered_paths_that_missed(project):
    service = MemoryService(project)
    try:
        service.search(path=str(project / "tools" / "build.py"))
        service.search(path="tools/build.py")
    finally:
        service.close()
    assert ("（全局）", "路径 tools/build.py（未登记到模块）", 2) in build_health(project)["misses"]


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


def test_health_flags_conflicting_memories_until_confirmed(project):
    decided = "决定：奖励发放改为服务端校验，客户端只负责展示结果，配置缺字段时直接报错而不是回退默认奖励。"
    excluded = "排除：奖励发放改为服务端校验行不通，客户端只负责展示结果会让离线模式没法发奖励，配置缺字段时仍回退默认奖励。"
    service = MemoryService(project)
    try:
        old = service.record("gameplay.Jigsaw", "Reward", "decision", decided)["id"]
        new = service.record("gameplay.Jigsaw", "Reward", "exclusion", excluded)["id"]
        assert service.record("gameplay.Jigsaw", "Reward", "risk", excluded + "风险。")["ok"]
        assert service.record("gameplay.Jigsaw", "Flow", "exclusion", excluded)["ok"]
        assert service.record("gameplay.Jigsaw", "Reward", "conclusion", "拼图块吸附阈值过小导致拖动时频繁误判吸附，已调到半格并验证通过。")["ok"]
    finally:
        service.close()

    pairs = build_health(project)["contradictions"]
    assert [(p["old"], p["new"]) for p in pairs] == [(old, new)]
    assert "疑似互相矛盾的记忆" in render(build_health(project))

    service = MemoryService(project)
    try:
        service.confirm([old])
    finally:
        service.close()
    assert build_health(project)["contradictions"] == []


def test_health_skips_pairs_already_resolved_by_supersedes(project):
    text = "决定：奖励发放改为服务端校验，客户端只负责展示结果，配置缺字段时直接报错。"
    service = MemoryService(project)
    try:
        old = service.record("gameplay.Jigsaw", "Reward", "decision", text)["id"]
        assert service.record("gameplay.Jigsaw", "Reward", "correction", "更正：" + text + "离线时仍回退。",
                              supersedes=[old])["ok"]
    finally:
        service.close()
    assert build_health(project)["contradictions"] == []


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


def test_unity_generated_dirs_are_skipped_only_at_the_unity_project_root(tmp_path):
    from pmem.scan.lite import iter_code_files

    for rel in ("client/Assets/Scripts/Logs/Logger.cs", "client/ProjectSettings/x.cs",
                "client/Library/PackageCache/a.cs", "client/Temp/b.cs", "src/Library/Book.ts"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x", encoding="utf-8")
    assert sorted(iter_code_files(tmp_path)) == [
        "client/Assets/Scripts/Logs/Logger.cs", "client/ProjectSettings/x.cs", "src/Library/Book.ts"]


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

    # 合并冲突后新旧目录各留一份同名文件：报告照常生成，单列一节
    stray = project / ".memory" / "entries" / "gameplay.Old" / f"{rid}.md"
    stray.parent.mkdir(parents=True)
    stray.write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
    file.write_text(file.read_text(encoding="utf-8").replace("module: gameplay.Old", "module: gameplay.Jigsaw"),
                    encoding="utf-8")
    h = build_health(project)
    assert h["strays"] == [] and "已存在" in h["stray_problem"]
    assert "【记忆文件重复】" in render(h)
