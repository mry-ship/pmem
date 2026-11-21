"""v0.7 类型安全与规则化：大量场景论证（设计稿 §3.1–3.6 + 复核修复）。

每条用例写清：场景 → 期望 → 实测断言。失败时断言信息可直接当证据缺口。
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from pmem.cli.main import _parse_when_arg
from pmem.core.config import Config, ConfigError
from pmem.core.entry import Entry
from pmem.core.facets import FacetError, conflicts, normalize_when, parse_facets, parse_when_loose
from pmem.core.schema import unknown_key_warnings
from pmem.hooks.payload import parse_payload, validate_hook_payload
from pmem.metrics.health import build_health
from pmem.service import MemoryService
from pmem.service.contracts import (
    check_graph,
    check_list_modules,
    check_record,
    check_search,
)


TEXT = "排除：Android 上不要用旧发放接口，改走服务端幂等领取。"
TEXT_IOS = "排除：iOS 上不要用旧发放接口，改走服务端幂等领取。"
TEXT_ANY = "风险：发放接口缺字段时会回退默认奖励，导致重复发放。"


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_AUTHOR", "evidence")
    root = tmp_path / "proj"
    mem = root / ".memory"
    mem.mkdir(parents=True)
    (mem / "config.yaml").write_text(
        textwrap.dedent(
            """
            project: { name: evidence }
            vcs: none
            embedding: { backend: none }
            wiki: { auto: false }
            gate: { mode: warn }
            facets:
              platform: [ios, android]
              model: str
            """
        ),
        encoding="utf-8",
    )
    (mem / "modules.yaml").write_text(
        textwrap.dedent(
            """
            categories: { gameplay: {} }
            modules:
              gameplay.Jigsaw: { paths: [src/**] }
              gameplay.Jigsaw.Reward: { paths: [src/Reward/**] }
            """
        ),
        encoding="utf-8",
    )
    (root / "src" / "Reward").mkdir(parents=True)
    (root / "rules" / "reward.py").parent.mkdir(parents=True, exist_ok=True)
    (root / "rules" / "reward.py").write_text("def no_default_grant():\n    pass\n", encoding="utf-8")
    return root


@pytest.fixture
def service(project):
    svc = MemoryService(project)
    yield svc
    svc.close()


# ---- §3.3 facets / when 原子语义 -------------------------------------------------

def test_evidence_facets_enum_and_free_str():
    """场景：声明枚举维 + str 维。期望：枚举只认列表取值；str 认任意非空。"""
    facets = parse_facets({"platform": ["ios", "android"], "model": "str"})
    assert facets["platform"].free is False
    assert facets["model"].free is True
    assert normalize_when({"platform": "Android", "model": " Flux-1 "}, facets) == {
        "platform": ["android"],
        "model": ["Flux-1"],
    }


def test_evidence_when_rejects_unknown_dimension_and_bad_value():
    """场景：未声明维 / 非法枚举值 / 未启用 facets。期望：FacetError。"""
    facets = parse_facets({"platform": ["ios", "android"]})
    with pytest.raises(FacetError, match="未声明"):
        normalize_when({"os": "ios"}, facets)
    with pytest.raises(FacetError, match="不在声明"):
        normalize_when({"platform": "web"}, facets)
    with pytest.raises(FacetError, match="未在 config"):
        normalize_when({"platform": "ios"}, {})


def test_evidence_conflicts_only_same_dimension_no_intersection():
    """场景：冲突语义。期望：同维无交集才冲突；缺维/无 when 不冲突（设计：明确冲突才排除）。"""
    assert conflicts({}, {"platform": ["android"]}) is False
    assert conflicts({"model": ["flux"]}, {"platform": ["android"]}) is False
    assert conflicts({"platform": ["ios"]}, {"platform": ["android"]}) is True
    assert conflicts({"platform": ["ios", "android"]}, {"platform": ["android"]}) is False
    # free 维大小写不敏感
    assert conflicts({"model": ["Flux-1"]}, {"model": ["flux-1"]}) is False
    assert conflicts({"model": ["Flux-1"]}, {"model": ["sdxl"]}) is True


def test_evidence_parse_when_loose_skips_bad_keeps_good():
    """场景：读盘时一个维度结构坏了。期望：跳过坏维，保留合法维（复核修复）。"""
    assert parse_when_loose({"platform": ["ios"], "bad": {"nested": 1}}) == {"platform": ["ios"]}
    text = (
        "---\nid: 01JA7K3M2X9F4Q8W6ZB1C2D3E4\nmodule: gameplay.Jigsaw\nentity: Reward\n"
        "kind: exclusion\nnote_date: '2026-11-20'\nauthor: a\n"
        "when:\n  platform: [ios]\n  bad:\n    nested: 1\n"
        f"---\n{TEXT}\n"
    )
    assert Entry.from_markdown(text).when == {"platform": ["ios"]}


def test_evidence_when_non_object_raises():
    """场景：YAML when 写成列表。期望：读盘报错（非对象）。"""
    text = (
        "---\nid: 01JA7K3M2X9F4Q8W6ZB1C2D3E4\nmodule: gameplay.Jigsaw\nentity: Reward\n"
        "kind: exclusion\nnote_date: '2026-11-20'\nauthor: a\nwhen: [ios]\n"
        f"---\n{TEXT}\n"
    )
    with pytest.raises(ValueError, match="when"):
        Entry.from_markdown(text)


# ---- §3.3 写入 / 检索全链路 ------------------------------------------------------

def test_evidence_record_search_filter_and_keep_unscoped(service):
    """场景：android / ios / 无 when 三条。期望：查 android 保留 android+无 when，排除 ios。"""
    assert service.record("gameplay.Jigsaw", "Reward", "exclusion", TEXT, when={"platform": "android"})["ok"]
    assert service.record("gameplay.Jigsaw", "Reward", "exclusion", TEXT_IOS, when={"platform": "ios"})["ok"]
    assert service.record("gameplay.Jigsaw", "Reward", "risk", TEXT_ANY)["ok"]

    android = service.search(module="gameplay.Jigsaw", when={"platform": "android"})
    assert check_search(android) == []
    ids_when = {
        (i["kind"], tuple(i.get("when", {}).get("platform", []) or ["*"]))
        for i in android["items"]
    }
    assert ("exclusion", ("android",)) in ids_when
    assert ("risk", ("*",)) in ids_when
    assert ("exclusion", ("ios",)) not in ids_when
    assert android.get("when_hint")

    ios = service.search(module="gameplay.Jigsaw", when={"platform": "ios"})
    kinds = {(i["kind"], tuple(i.get("when", {}).get("platform", []) or ["*"])) for i in ios["items"]}
    assert ("exclusion", ("ios",)) in kinds
    assert ("exclusion", ("android",)) not in kinds


def test_evidence_record_rejects_when_without_facets(tmp_path, monkeypatch):
    """场景：项目未声明 facets 仍写 when。期望：拒绝，code=when_invalid。"""
    monkeypatch.setenv("PMEM_AUTHOR", "evidence")
    root = tmp_path / "plain"
    mem = root / ".memory"
    mem.mkdir(parents=True)
    (mem / "config.yaml").write_text(
        "project: { name: plain }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n",
        encoding="utf-8",
    )
    (mem / "modules.yaml").write_text(
        "categories: { gameplay: {} }\nmodules:\n  gameplay.Jigsaw: { paths: [src/**] }\n",
        encoding="utf-8",
    )
    (root / "src").mkdir()
    svc = MemoryService(root)
    try:
        bad = svc.record("gameplay.Jigsaw", "Reward", "exclusion", TEXT, when={"platform": "android"})
        assert bad["ok"] is False
        assert bad["code"] == "when_invalid"
        assert "facets" in bad["error"]
        search_bad = svc.search(module="gameplay.Jigsaw", when={"platform": "android"})
        assert search_bad["ok"] is False and "facets" in search_bad["error"]
    finally:
        svc.close()


def test_evidence_clear_when_on_draft_overwrite(service):
    """场景：覆盖草稿传 when={}。期望：清空结构化条件；之后按平台查仍能命中（无 when 不过滤）。"""
    written = service.record(
        "gameplay.Jigsaw", "Reward", "exclusion", TEXT, when={"platform": "android"}
    )
    assert written["ok"]
    draft = written["draft_id"]
    cleared = service.record(
        "gameplay.Jigsaw", "Reward", "exclusion", TEXT, draft_id=draft, when={}
    )
    assert cleared["ok"]
    path = service.config.entries_dir / "gameplay.Jigsaw" / f"{draft}.md"
    entry = Entry.from_markdown(path.read_text(encoding="utf-8"))
    assert entry.when == {}
    hit = service.search(module="gameplay.Jigsaw", when={"platform": "ios"})
    assert any(i["id"] == draft for i in hit["items"])


def test_evidence_multidim_conflict_excludes(service):
    """场景：条目 platform=ios+model=flux；查询 platform=ios+model=sdxl。期望：因 model 冲突排除。"""
    assert service.record(
        "gameplay.Jigsaw", "Art", "exclusion", TEXT + " flux。",
        when={"platform": "ios", "model": "flux"},
    )["ok"]
    assert service.record(
        "gameplay.Jigsaw", "Art", "exclusion", TEXT + " sdxl。",
        when={"platform": "ios", "model": "sdxl"},
    )["ok"]
    only_flux = service.search(
        module="gameplay.Jigsaw", entity="Art", when={"platform": "ios", "model": "flux"}
    )
    models = [i.get("when", {}).get("model") for i in only_flux["items"] if i.get("when")]
    assert ["flux"] in models
    assert ["sdxl"] not in models


# ---- §3.2 enforced_by ------------------------------------------------------------

def test_evidence_enforced_by_roundtrip_search_hint_and_omit_empty(service, project):
    """场景：写入 enforced_by。期望：往返保留；检索带 enforced_hint；空列表不进 YAML。"""
    written = service.record(
        "gameplay.Jigsaw",
        "Reward",
        "exclusion",
        TEXT,
        enforced_by=["rules/reward.py#no_default_grant"],
    )
    assert written["ok"] and check_record(written) == []
    path = project / ".memory" / "entries" / "gameplay.Jigsaw" / f"{written['draft_id']}.md"
    entry = Entry.from_markdown(path.read_text(encoding="utf-8"))
    assert entry.enforced_by == ["rules/reward.py#no_default_grant"]
    assert entry.enforced is True
    found = service.search(module="gameplay.Jigsaw", query="幂等")
    assert check_search(found) == []
    assert any(i.get("enforced_by") for i in found["items"])
    assert found.get("enforced_hint")
    bare = Entry(
        id="01JA7K3M2X9F4Q8W6ZB1C2D3E4",
        module="gameplay.Jigsaw",
        entity="Reward",
        kind="exclusion",
        content=TEXT,
        note_date="2026-11-20",
        author="a",
    )
    assert "enforced_by" not in bare.to_markdown()


# ---- §3.4 边界校验 ----------------------------------------------------------------

def test_evidence_unknown_key_tip_uses_full_path(tmp_path):
    """场景：gate.mod 拼错。期望：警告含「是不是 gate.mode？」（复核修复）。"""
    mem = tmp_path / ".memory"
    mem.mkdir()
    (mem / "config.yaml").write_text(
        "project: { name: t }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n"
        "gate:\n  mod: warn\n",
        encoding="utf-8",
    )
    cfg = Config.load(tmp_path)
    joined = "\n".join(cfg.warnings)
    assert "gate.mod" in joined and "是不是 gate.mode？" in joined


def test_evidence_null_and_empty_facets_mean_disabled(tmp_path):
    """场景：facets: / facets: null / facets: {}。期望：未启用，不报错（复核修复）。"""
    mem = tmp_path / ".memory"
    mem.mkdir()
    for body in ("facets:\n", "facets: null\n", "facets: {}\n"):
        (mem / "config.yaml").write_text(
            f"project: {{ name: t }}\nvcs: none\nembedding: {{ backend: none }}\nwiki: {{ auto: false }}\n{body}",
            encoding="utf-8",
        )
        assert Config.load(tmp_path).facets == {}


def test_evidence_too_many_facets_warns(tmp_path):
    """场景：声明 5 个维度。期望：加载成功但警告建议不超过 4。"""
    mem = tmp_path / ".memory"
    mem.mkdir()
    (mem / "config.yaml").write_text(
        "project: { name: t }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n"
        "facets:\n  a: str\n  b: str\n  c: str\n  d: str\n  e: str\n",
        encoding="utf-8",
    )
    cfg = Config.load(tmp_path)
    assert len(cfg.facets) == 5
    assert any("不超过 4" in w for w in cfg.warnings)


def test_evidence_bad_facets_type_rejected(tmp_path):
    """场景：facets 写成列表。期望：ConfigError。"""
    mem = tmp_path / ".memory"
    mem.mkdir()
    (mem / "config.yaml").write_text(
        "project: { name: t }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n"
        "facets: [ios]\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="键值对"):
        Config.load(tmp_path)


def test_evidence_hook_validate_soft_only():
    """场景：Hook 字段类型错误。期望：只返回警告列表，不抛异常。"""
    assert validate_hook_payload({"conversation_id": "c1", "tool_name": "Read"}) == []
    warnings = validate_hook_payload(
        {"conversation_id": 1, "workspace_roots": "x", "tool_input": ["y"]}
    )
    assert any("conversation_id" in w for w in warnings)
    assert any("workspace_roots" in w for w in warnings)
    assert any("tool_input" in w for w in warnings)
    # 解析仍可用
    data = parse_payload(b'{"conversation_id":"c1","hook_event_name":"preToolUse"}')
    assert data["conversation_id"] == "c1"


def test_evidence_schema_unknown_key_unit():
    """场景：unknown_key_warnings 单元。期望：顶层与嵌套提示路径完整。"""
    warnings = unknown_key_warnings(
        {"gate": {"mod": "block"}, "extra": 1},
        {"gate": {"mode", "watch"}, "write": {"content_min"}},
        file_path=".memory/config.yaml",
    )
    assert any("不认识的键 extra" in w for w in warnings)
    assert any("gate.mod" in w and "是不是 gate.mode？" in w for w in warnings)


# ---- §3.5 返回契约 ----------------------------------------------------------------

def test_evidence_contracts_on_real_responses(service):
    """场景：真实 search/record/graph/list_modules。期望：契约检查无错误。"""
    written = service.record("gameplay.Jigsaw", "Reward", "exclusion", TEXT)
    assert check_record(written) == [], check_record(written)
    search = service.search(module="gameplay.Jigsaw", query="幂等")
    assert check_search(search) == [], check_search(search)
    graph = service.graph("gameplay.Jigsaw")
    assert check_graph(graph) == [], check_graph(graph)
    listed = service.list_modules()
    assert check_list_modules(listed) == [], check_list_modules(listed)


def test_evidence_fail_shapes_require_error_string():
    """场景：失败返回缺 error。期望：契约检查报错。"""
    assert check_search({"ok": False, "error": "x"}) == []
    assert check_search({"ok": False}) == ["失败返回缺少 error 字符串"]
    assert check_record({"ok": False, "error": "x", "code": "when_invalid"}) == []


# ---- CLI 集成 ---------------------------------------------------------------------

def _pmem(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "pmem", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_evidence_cli_when_record_search_doctor(project):
    """场景：CLI record/search --when + doctor 未知键。期望：过滤正确；doctor 见 gate.mode 提示。"""
    cfg = project / ".memory" / "config.yaml"
    text = cfg.read_text(encoding="utf-8").replace("gate: { mode: warn }", "gate: { mode: warn, mod: block }")
    cfg.write_text(text, encoding="utf-8")
    content = project / "body.md"
    content.write_text(TEXT, encoding="utf-8")

    doctor = _pmem("doctor", "--root", str(project))
    out = doctor.stdout + doctor.stderr
    assert "gate.mod" in out and "gate.mode" in out, out

    rec = _pmem(
        "record", "--root", str(project),
        "--module", "gameplay.Jigsaw", "--entity", "Reward", "--kind", "exclusion",
        "--content-file", str(content), "--when", "platform=android", "--brief",
    )
    assert rec.returncode == 0, rec.stdout + rec.stderr

    ios = _pmem(
        "search", "--root", str(project),
        "--module", "gameplay.Jigsaw", "--when", "platform=ios", "--brief",
    )
    assert ios.returncode == 0, ios.stdout + ios.stderr
    assert "旧发放" not in ios.stdout

    android = _pmem(
        "search", "--root", str(project),
        "--module", "gameplay.Jigsaw", "--when", "platform=android", "--brief",
    )
    assert android.returncode == 0, android.stdout + android.stderr
    assert "旧发放" in android.stdout or "条件" in android.stdout


def test_evidence_cli_when_arg_parser():
    """场景：--when 参数形态。期望：未传 None；空列表清空；k=v 与 JSON 可解析。"""
    assert _parse_when_arg(None) is None
    assert _parse_when_arg([]) == {}
    assert _parse_when_arg(["platform=android,ios"]) == {"platform": ["android", "ios"]}
    assert _parse_when_arg(['{"platform": "android"}']) == {"platform": "android"}


# ---- §3.6 / 分层 ------------------------------------------------------------------

def test_evidence_hook_process_stays_light():
    """场景：导入 hook_cmd + gate。期望：不加载 numpy/yaml/service/index.store（设计约束）。"""
    code = (
        "import sys, pmem.cli.hook_cmd, pmem.hooks.gate; "
        "print(','.join(m for m in ('numpy', 'yaml', 'pmem.service', 'pmem.index.store') if m in sys.modules))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == ""


def test_evidence_inherited_lessons_also_filtered_by_when(service):
    """场景：上级 ios 教训 + 子模块检索 when=android。期望：上级冲突教训不继承进来。"""
    assert service.record(
        "gameplay.Jigsaw", "Reward", "exclusion", TEXT_IOS, when={"platform": "ios"}
    )["ok"]
    assert service.record(
        "gameplay.Jigsaw.Reward", "Grant", "risk", TEXT_ANY
    )["ok"]
    child = service.search(module="gameplay.Jigsaw.Reward", when={"platform": "android"})
    assert check_search(child) == []
    # 上级 ios-only 不应出现在 android 查询里（含 inherited）
    for item in child["items"]:
        when = item.get("when") or {}
        if when.get("platform") == ["ios"]:
            pytest.fail(f"冲突上级教训仍返回：{item.get('id')} {when}")


def test_evidence_matrix_platform_filter_counts(service):
    """场景：矩阵写入 2×2 + 无 when。期望：各平台查询条数符合冲突排除规则。"""
    for plat, body in (("android", TEXT), ("ios", TEXT_IOS)):
        assert service.record(
            "gameplay.Jigsaw", "Matrix", "exclusion", body + plat, when={"platform": plat}
        )["ok"]
    assert service.record("gameplay.Jigsaw", "Matrix", "risk", TEXT_ANY + "通用")["ok"]

    for plat in ("android", "ios"):
        result = service.search(module="gameplay.Jigsaw", entity="Matrix", when={"platform": plat})
        assert check_search(result) == []
        platforms = []
        has_unscoped = False
        for item in result["items"]:
            when = item.get("when") or {}
            if not when:
                has_unscoped = True
            else:
                platforms.append(tuple(when.get("platform") or []))
        assert has_unscoped, "无 when 的通用风险应保留"
        assert (plat,) in platforms
        other = "ios" if plat == "android" else "android"
        assert (other,) not in platforms


def test_evidence_health_rule_candidates_skip_enforced(project, service):
    """场景：同议题 3 条防错 vs 已有 enforced_by 的议题。期望：前者进候选，后者跳过。"""
    from pmem.metrics.health import render

    body = TEXT + "再补足够长的正文，方便三条防错类都过字数下限。"
    assert service.record("gameplay.Jigsaw", "Reward", "exclusion", "排除：" + body)["ok"]
    assert service.record("gameplay.Jigsaw", "Reward", "risk", "风险：" + body)["ok"]
    assert service.record("gameplay.Jigsaw", "Reward", "correction", "更正：" + body)["ok"]
    assert service.record(
        "gameplay.Jigsaw", "Flow", "exclusion", "排除：" + body,
        enforced_by=["rules/reward.py#no_default_grant"],
    )["ok"]
    assert service.record("gameplay.Jigsaw", "Flow", "risk", "风险：" + body)["ok"]
    assert service.record("gameplay.Jigsaw", "Flow", "correction", "更正：" + body)["ok"]

    health = build_health(project)
    topics = {(r["module"], r["entity"]) for r in health["rule_candidates"]}
    assert ("gameplay.Jigsaw", "Reward") in topics
    assert ("gameplay.Jigsaw", "Flow") not in topics
    assert "可以写成规则的教训" in render(health)


def test_evidence_entry_when_scalar_roundtrip():
    """场景：when 单值写成标量。期望：读盘收成列表，再写出可为标量。"""
    entry = Entry(
        id="01JA7K3M2X9F4Q8W6ZB1C2D3E4",
        module="gameplay.Jigsaw",
        entity="Reward",
        kind="exclusion",
        content=TEXT,
        note_date="2026-11-20",
        author="a",
        when={"platform": ["android"]},
    )
    md = entry.to_markdown()
    assert "platform: android" in md or "platform:\n- android" in md or "platform: [android]" in md or "platform:\n  - android" in md
    parsed = Entry.from_markdown(md)
    assert parsed.when == {"platform": ["android"]}


def test_evidence_search_json_when_via_cli_parser():
    """场景：CLI --when JSON。期望：解析为对象供 search/record 使用。"""
    assert _parse_when_arg(['{"platform":["android","ios"]}']) == {"platform": ["android", "ios"]}


def test_evidence_version_is_073():
    """场景：安装包版本。期望：当前为 0.7.3。"""
    import pmem

    assert pmem.__version__ == "0.7.3"
    out = _pmem("--version")
    assert "0.7.3" in out.stdout


def test_package_version_sources_match():
    """场景：版本来源。期望：pyproject、uv.lock 与 pmem.__version__ 是同一个版本。"""
    import re

    import pmem

    root = Path(__file__).resolve().parents[1]
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'(?m)^version = "([^"]+)"\s*$', project)
    assert declared is not None
    version = declared.group(1)
    assert pmem.__version__ == version
    lock = (root / "uv.lock").read_text(encoding="utf-8")
    assert re.search(rf'(?m)^name = "pmem"\nversion = "{re.escape(version)}"\s*$', lock)


def test_evidence_consolidate_skill_has_rule_upgrade_step():
    """场景：设计 §3.1。期望：consolidate 技能含「可以写成规则」并指导 enforced_by。"""
    from pmem.generate.templates import COMPACT_SKILL, CONSOLIDATE_SKILL

    assert "可以写成规则的教训" in CONSOLIDATE_SKILL
    assert "enforced_by" in CONSOLIDATE_SKILL
    assert CONSOLIDATE_SKILL.format(generated="x")
    assert "--when" in COMPACT_SKILL and "facets" in COMPACT_SKILL
