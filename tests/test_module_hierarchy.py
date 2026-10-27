"""多段模块名（父子模块）：命名解析、迁移、检索继承、闸门、健康检查与同步。"""
from pathlib import Path

import pytest
import yaml

from pmem.cli.main import main
from pmem.core.registry import (
    ModuleRegistry,
    RegistryError,
    ancestor_modules,
    is_lineage,
    is_module_id,
    parent_module,
)
from pmem.service import MemoryService

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n"
MODULES = """\
categories: { system: {}, infra: {} }
modules:
  system.Ads: { paths: [src/Ads/**] }
  system.Ads.AdMob: { paths: [src/Ads/AdMob/**], entities: [Pangle] }
  system.Ads.Max: { paths: [src/Ads/Max/**] }
  system.Ads.AdMob.Android: { paths: [src/Ads/AdMob/Android/**] }
  system.Ads.Max.Android: { paths: [src/Ads/Max/Android/**] }
  system.Login: { paths: [src/Login/**] }
  infra.Build:
    paths: [build/**]
    related:
      - { module: system.Ads, reason: 不同平台打入的广告 SDK 不同 }
"""
ADS_PITFALL = "所有广告 SDK 初始化都必须等隐私弹窗关闭之后，否则欧盟地区审核被拒，iOS 与 Android 都是。"
ADMOB_PITFALL = "AdMob 激励视频回调在子线程触发，直接改 UI 会崩溃，要切回主线程再发奖励。"


@pytest.fixture
def registry() -> ModuleRegistry:
    return ModuleRegistry(yaml.safe_load(MODULES))


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    for rel in ("src/Ads/AdManager.cs", "src/Ads/AdMob/AdMobAdapter.cs", "src/Ads/Max/MaxAdapter.cs",
                "src/Ads/AdMob/Android/Bridge.cs", "src/Login/Login.cs", "build/Build.cs"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("class X { void Run() {} }\n", encoding="utf-8")
    return root


def service(root: Path) -> MemoryService:
    return MemoryService(root)


def record(root: Path, module: str, text: str, entity: str = "Init", kind: str = "risk", **kw) -> dict:
    svc = service(root)
    try:
        return svc.record(module, entity, kind, text, **kw)
    finally:
        svc.close()


# ---- 命名 ----

def test_module_id_allows_up_to_four_segments():
    assert is_module_id("system.Ads")
    assert is_module_id("system.Ads.AdMob.Android")
    assert not is_module_id("system.Ads.AdMob.Android.Arm64")
    assert not is_module_id("system.Ads..AdMob")


def test_parent_and_ancestors_come_from_the_name():
    assert parent_module("system.Ads") is None
    assert parent_module("system.Ads.AdMob") == "system.Ads"
    assert ancestor_modules("system.Ads.AdMob.Android") == ["system.Ads.AdMob", "system.Ads"]
    assert is_lineage("system.Ads", "system.ads.admob.android")
    assert not is_lineage("system.Ads", "system.AdsX")
    assert not is_lineage("system.Ads.AdMob", "system.Ads.Max")


def test_short_names_resolve_by_last_segment_or_relative_name(registry):
    assert registry.resolve_module("AdMob").id == "system.Ads.AdMob"
    assert registry.resolve_module("Ads.AdMob").id == "system.Ads.AdMob"
    assert registry.resolve_module("system.ads.admob").id == "system.Ads.AdMob"
    with pytest.raises(RegistryError, match="歧义"):
        registry.resolve_module("Android")
    assert registry.resolve_module("AdMob.Android").id == "system.Ads.AdMob.Android"


def test_registry_lists_children_and_registered_ancestors(registry):
    assert registry.children("system.Ads") == ["system.Ads.AdMob", "system.Ads.Max"]
    assert registry.registered_ancestors("system.Ads.AdMob.Android") == ["system.Ads.AdMob", "system.Ads"]
    assert registry.modules["system.Ads.AdMob"].name == "AdMob"
    assert registry.modules["infra.Build"].related == [{"module": "system.Ads", "reason": "不同平台打入的广告 SDK 不同"}]


def test_unregistered_child_needs_a_registered_parent(registry):
    resolved = registry.resolve_module("system.ads.Yandex")
    assert resolved.id == "system.Ads.Yandex" and resolved.known is False
    with pytest.raises(RegistryError, match="父模块"):
        registry.resolve_module("system.Pay.Alipay")
    with pytest.raises(RegistryError, match="4 段"):
        registry.resolve_module("system.Ads.AdMob.Android.Arm64")


def test_ambiguous_last_segment_is_not_used_for_mentions(registry):
    patterns = registry.name_patterns()
    assert "system.Ads.AdMob.Android" not in patterns
    assert patterns["system.Ads.AdMob"].search("AdMob 回调")


# ---- 迁移 ----

def test_rename_parent_cascades_to_children_and_moves_memories(project, capsys):
    rid = record(project, "system.Ads.AdMob", ADMOB_PITFALL)["id"]
    assert main(["migrate", "rename", "system.Ads", "system.Advert", "--root", str(project), "--apply"]) == 0
    out = capsys.readouterr().out
    assert "子模块跟着改名" in out
    data = yaml.safe_load((project / ".memory" / "modules.yaml").read_text(encoding="utf-8"))["modules"]
    assert {"system.Advert", "system.Advert.AdMob", "system.Advert.AdMob.Android"} <= set(data)
    assert "system.Ads.AdMob" in data["system.Advert.AdMob"]["aliases"]
    assert data["infra.Build"]["related"][0]["module"] == "system.Advert"
    assert (project / ".memory" / "entries" / "system.Advert.AdMob" / f"{rid}.md").exists()


def test_rename_refuses_to_exceed_depth_or_nest_under_itself(project, capsys):
    assert main(["migrate", "rename", "system.Ads", "system.Login.Ads", "--root", str(project)]) == 1
    assert "超过 4 段" in capsys.readouterr().out
    assert main(["migrate", "rename", "system.Ads", "system.Ads.Core", "--root", str(project)]) == 1


def test_split_creates_child_module_under_parent(project):
    (project / "src/Ads/Yandex").mkdir(parents=True)
    (project / "src/Ads/Yandex/YandexAdapter.cs").write_text("class Y {}\n", encoding="utf-8")
    assert main(["migrate", "split", "system.Ads", "--to", "system.Ads.Yandex=src/Ads/Yandex/**",
                 "--root", str(project), "--apply"]) == 0
    data = yaml.safe_load((project / ".memory" / "modules.yaml").read_text(encoding="utf-8"))["modules"]
    assert data["system.Ads.Yandex"]["paths"] == ["src/Ads/Yandex/**"]


def test_new_child_name_requires_registered_parent(project, capsys):
    assert main(["migrate", "rename", "system.Login", "system.Pay.Login", "--root", str(project)]) == 1
    assert "父模块" in capsys.readouterr().out


# ---- 检索继承 ----

def search(root: Path, **kw) -> dict:
    svc = service(root)
    try:
        return svc.search(**kw)
    finally:
        svc.close()


def test_child_search_inherits_ancestor_lessons_but_not_features(project):
    ads = record(project, "system.Ads", ADS_PITFALL)["id"]
    feature = record(project, "system.Ads", "用户要求：广告管理器按优先级瀑布流依次请求各 SDK，失败才换下一个。",
                     entity="Waterfall", kind="feature")["id"]
    own = record(project, "system.Ads.AdMob", ADMOB_PITFALL, entity="Reward")["id"]
    result = search(project, module="system.Ads.AdMob.Android")
    rows = {i["id"]: i for i in result["items"]}
    assert set(rows) == {ads, own}
    assert rows[ads]["inherited"] is True and rows[ads]["module"] == "system.Ads"
    assert rows[own]["module"] == "system.Ads.AdMob"
    assert feature not in {f["id"] for f in result.get("features", [])}
    assert "inherited_hint" in result


def test_ancestor_lessons_come_on_top_of_a_full_own_limit(project):
    for n in range(4):
        record(project, "system.Ads", f"{ADS_PITFALL}第 {n} 条变体说明，内容各不相同。", entity=f"Topic{n}")
    own = [record(project, "system.Ads.AdMob", f"{ADMOB_PITFALL}第 {n} 条。", entity=f"Own{n}")["id"]
           for n in range(6)]
    items = search(project, module="system.Ads.AdMob", limit=5)["items"]
    assert len(items) == 7
    assert sum(1 for i in items if i.get("inherited")) == 2
    assert sum(1 for i in items if i["id"] in own) == 5


def test_spare_own_slots_go_to_ancestors(project):
    for n in range(4):
        record(project, "system.Ads", f"{ADS_PITFALL}第 {n} 条变体说明，内容各不相同。", entity=f"Topic{n}")
    record(project, "system.Ads.AdMob", ADMOB_PITFALL)
    items = search(project, module="system.Ads.AdMob", limit=5)["items"]
    assert len(items) == 5 and sum(1 for i in items if i.get("inherited")) == 4
    assert len(search(project, module="system.Ads.AdMob", limit=1)["items"]) == 3


def test_parent_search_lists_children_and_entity_filter_only_applies_to_own(project):
    own = record(project, "system.Ads.AdMob", ADMOB_PITFALL, entity="Reward")["id"]
    deep = record(project, "system.Ads.AdMob.Android", "Android 渠道包必须带 AdMob 的 App ID 元数据，否则启动即崩溃。",
                  entity="Manifest")["id"]
    feature = record(project, "system.Ads.AdMob", "用户要求：激励视频必须完整看完才发奖励，中途关闭不发，避免被刷奖励。",
                     entity="Flow", kind="feature")
    assert feature["ok"], feature
    result = search(project, module="system.Ads")
    assert {c["module"] for c in result["children"]} == {"system.Ads.AdMob", "system.Ads.Max"}
    admob = next(c for c in result["children"] if c["module"] == "system.Ads.AdMob")
    assert admob["count"] == 2
    assert [row["id"] for row in admob["latest"]] == [feature["id"], deep, own]
    assert admob["latest"][0]["kind"] == "feature"
    assert admob["latest"][1]["module"] == "system.Ads.AdMob.Android" and "module" not in admob["latest"][2]
    assert "latest" not in next(c for c in result["children"] if c["module"] == "system.Ads.Max")
    ads = record(project, "system.Ads", ADS_PITFALL)["id"]
    result = search(project, module="system.Ads.AdMob", entity="Reward")
    assert ads in {i["id"] for i in result["items"]}


def test_empty_unregistered_child_still_gets_parent_lessons(project):
    ads = record(project, "system.Ads", ADS_PITFALL)["id"]
    result = search(project, module="system.Ads.Yandex")
    assert [i["id"] for i in result["items"]] == [ads]


def test_manual_related_is_listed_both_ways_and_lineage_is_not_related(project):
    record(project, "system.Ads", ADS_PITFALL)
    record(project, "infra.Build", "打包脚本按平台选择广告 SDK 列表，Android 包不含 Max 的 iOS 适配器。", entity="Ads")
    ads = search(project, module="system.Ads")
    assert any(r.startswith("infra.Build（手工登记") for r in ads["related"])
    assert not any(r.startswith("system.Ads.") for r in ads["related"])
    build = search(project, module="infra.Build")
    assert any(r.startswith("system.Ads（手工登记") for r in build["related"])


def test_list_modules_and_graph_show_hierarchy(project):
    record(project, "system.Ads", ADS_PITFALL)
    record(project, "system.Ads.AdMob", ADMOB_PITFALL)
    svc = service(project)
    try:
        rows = {r["module"]: r for r in svc.list_modules()["modules"]}
        graph = svc.graph("system.Ads.AdMob")
    finally:
        svc.close()
    assert rows["system.Ads"]["children"] == ["system.Ads.AdMob", "system.Ads.Max"]
    assert rows["system.Ads.AdMob"]["parent"] == "system.Ads"
    assert graph["lineage"] == ["system.Ads"]


# ---- 写入 ----

def test_parent_may_supersede_child_lessons_but_child_may_not_supersede_parent(project):
    child = record(project, "system.Ads.AdMob", ADS_PITFALL)["id"]
    lifted = record(project, "system.Ads", ADS_PITFALL + "（提升到上级）", supersedes=[child])
    assert lifted["ok"], lifted
    parent = lifted["id"]
    refused = record(project, "system.Ads.Max", ADS_PITFALL + "（Max 版）", supersedes=[parent])
    assert refused["ok"] is False and refused["code"] == "supersede_cross_module"


def test_sibling_lesson_on_same_entity_suggests_writing_to_parent(project):
    first = record(project, "system.Ads.AdMob", ADS_PITFALL)["id"]
    result = record(project, "system.Ads.Max", ADS_PITFALL + "Max 也一样。")
    assert [r["id"] for r in result["sibling_similar"]] == [first]
    assert any("system.Ads" in h for h in result["hints"])
    other = record(project, "system.Ads.Max", ADMOB_PITFALL, entity="Reward")
    assert "sibling_similar" not in other


# ---- 闸门 ----

def write_payload(root: Path, rel: str) -> dict:
    return {"conversation_id": "c1", "hook_event_name": "preToolUse", "tool_name": "Write",
            "tool_input": {"file_path": str(root / rel), "content": "x"}}


def test_digest_and_gate_hide_child_lesson_superseded_by_parent(project):
    from pmem.hooks.gate import handle

    child = record(project, "system.Ads.AdMob", ADS_PITFALL)["id"]
    lifted = record(project, "system.Ads", ADS_PITFALL + "（提升到上级）",
                    summary="广告初始化规则已提升到上级", supersedes=[child])
    assert lifted["ok"], lifted
    payload = {"conversation_id": "c1", "tool_name": "Read",
               "tool_input": {"file_path": str(project / "src/Ads/AdMob/AdMobAdapter.cs")}}
    text = handle("post-tool", payload, project)["additional_context"]
    assert "现行记忆 0 条" in text and "广告初始化规则已提升到上级" in text
    denied = handle("pre-tool", {"conversation_id": "c1", "tool_name": "Write",
                                 "tool_input": {"file_path": str(project / "src/Ads/AdMob/AdMobAdapter.cs"),
                                                "content": "x"}}, project)
    assert denied["permission"] == "deny"
    assert "已有 0 条研发记忆" in denied["user_message"] and "上级模块另有 1 条教训" in denied["user_message"]
    assert "广告初始化规则已提升到上级" in denied["user_message"]


def test_gate_blocks_child_without_own_memories_when_parent_has_lessons(project):
    from pmem.hooks.gate import handle

    config = project / ".memory" / "config.yaml"
    config.write_text(CONFIG + "gate: { mode: block }\n", encoding="utf-8")
    record(project, "system.Ads", ADS_PITFALL)
    denied = handle("pre-tool", write_payload(project, "src/Ads/AdMob/AdMobAdapter.cs"), project)
    assert denied["permission"] == "deny"
    message = denied["user_message"]
    assert "system.Ads.AdMob" in message and "上级模块另有 1 条教训" in message
    assert "上级 system.Ads/" in message
    assert handle("pre-tool", write_payload(project, "src/Login/Login.cs"), project)["permission"] == "allow"


def test_ancestor_pitfalls_tolerate_entries_filed_under_another_name(project):
    from pmem.hooks.gate import Gate

    rid = record(project, "system.Ads", ADS_PITFALL)["id"]
    path = project / ".memory" / "entries" / "system.Ads" / f"{rid}.md"
    path.write_text(path.read_text(encoding="utf-8").replace("module: system.Ads", "module: system.Advert"),
                    encoding="utf-8")
    pitfalls, count = Gate(project, {"conversation_id": "c1"}).ancestor_pitfalls("system.Ads.AdMob")
    assert [e.id for e in pitfalls] == [rid] and count == 1


def test_mentions_match_whole_module_names(project):
    from pmem.hooks.gate import Gate

    gate = Gate(project, {"conversation_id": "c1"})
    assert gate.modules_in_text("看一下 system.Ads.AdMob 的回调") == ["system.Ads.AdMob"]
    assert "system.Ads" in gate.modules_in_text("system.Ads 的初始化")


# ---- 健康检查、自检、同步 ----

def write_modules(root: Path, data: dict) -> None:
    (root / ".memory" / "modules.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_health_does_not_report_hierarchy_as_duplicates():
    from pmem.metrics.health import _duplicate_modules

    ids = ["system.Ads", "system.Ads.AdMob", "system.Ads.AdMob.Android", "system.Ads.Max.Android", "infra.Ads"]
    assert _duplicate_modules(ids) == [["infra.Ads", "system.Ads"]]


def test_health_lists_hierarchy_issues(project):
    from pmem.metrics.health import build_health, render

    data = yaml.safe_load(MODULES)
    data["modules"]["system.Pay"] = {}
    data["modules"]["system.Pay.Alipay"] = {"paths": ["src/Pay/**"]}
    data["modules"]["system.Login"]["parent"] = "system.Ads"
    data["modules"]["infra.Build"]["related"].append({"module": "system.Gone", "reason": "已删除"})
    write_modules(project, data)
    record(project, "system.Ads.AdMob", ADS_PITFALL)
    record(project, "system.Ads.Max", ADS_PITFALL + "Max 也一样。")
    health = build_health(project)
    text = "\n".join(health["hierarchy"])
    assert "system.Pay：只有一个下级 system.Pay.Alipay" in text
    assert "pmem migrate rename system.Login system.Ads.Login" in text
    assert "related 里的 system.Gone" in text
    assert "system.Ads 的下级 system.Ads.AdMob、system.Ads.Max 都有议题 init" in text
    assert "父子模块结构" in render(health)


def test_doctor_does_not_call_grouping_parent_a_shell(project, capsys):
    data = yaml.safe_load(MODULES)
    data["modules"]["system.Ads"]["paths"] = ["src/Ads/AdMob/**"]
    data["modules"]["system.Login"]["paths"] = ["src/Gone/**"]
    write_modules(project, data)
    main(["doctor", "--root", str(project)])
    out = capsys.readouterr().out
    line = next(line for line in out.splitlines() if "空壳模块" in line)
    shells = line.rsplit("：", 1)[-1].split(", ")
    assert "system.Login" in shells and "system.Ads" not in shells
    assert "个子模块" in out


def test_sync_proposes_child_modules_for_big_module_directories(project, capsys):
    for folder, count in (("Sdk", 40), ("Ui", 25)):
        for n in range(count):
            path = project / "src/Login" / folder / f"{folder}{n}.cs"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("class S {}\n", encoding="utf-8")
    assert main(["sync", "--root", str(project)]) == 0
    out = capsys.readouterr().out
    assert "system.Login.Sdk：src/Login/Sdk/**（40 个代码文件" in out
    assert "pmem migrate split system.Login --to system.Login.Sdk=src/Login/Sdk/**" in out
    assert "system.Login.Ui" not in out
    data = yaml.safe_load((project / ".memory" / "modules.yaml").read_text(encoding="utf-8"))["modules"]
    assert "system.Login.Sdk" not in data


def test_wiki_indents_children_and_links_parent(project):
    record(project, "system.Ads", ADS_PITFALL)
    record(project, "system.Ads.AdMob", ADMOB_PITFALL)
    record(project, "infra.Build", "打包脚本按平台选择广告 SDK 列表，Android 包不含 Max 的 iOS 适配器。", entity="Ads")
    out = project / "wiki"
    assert main(["wiki", "--root", str(project), "--out", str(out)]) == 0
    index = (out / "index.md").read_text(encoding="utf-8")
    assert index.index("[system.Ads]") < index.index("└ [system.Ads.AdMob]")
    child = (out / "system.Ads.AdMob.md").read_text(encoding="utf-8")
    assert "上级模块：[system.Ads]" in child
    parent = (out / "system.Ads.md").read_text(encoding="utf-8")
    assert "下级模块：[system.Ads.AdMob]" in parent and "`system.Ads.Max`" in parent
    assert "手工登记：不同平台打入的广告 SDK 不同" in parent
