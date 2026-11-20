import pytest

from pmem.core.config import Config, ConfigError
from pmem.core.entry import Entry
from pmem.core.facets import FacetError, conflicts, normalize_when, parse_facets
from pmem.service import MemoryService


def test_parse_facets_enum_and_str():
    facets = parse_facets({"platform": ["ios", "android"], "model": "str"})
    assert facets["platform"].free is False and facets["platform"].values == ("ios", "android")
    assert facets["model"].free is True


def test_normalize_when_rejects_unknown_and_bad_value():
    facets = parse_facets({"platform": ["ios", "android"]})
    assert normalize_when({"platform": "Android"}, facets) == {"platform": ["android"]}
    with pytest.raises(FacetError, match="未声明"):
        normalize_when({"os": "ios"}, facets)
    with pytest.raises(FacetError, match="不在声明"):
        normalize_when({"platform": "web"}, facets)
    with pytest.raises(FacetError, match="未在 config"):
        normalize_when({"platform": "ios"}, {})


def test_conflicts_only_on_same_dimension():
    assert conflicts({}, {"platform": ["android"]}) is False
    assert conflicts({"model": ["flux"]}, {"platform": ["android"]}) is False
    assert conflicts({"platform": ["ios"]}, {"platform": ["android"]}) is True
    assert conflicts({"platform": ["ios", "android"]}, {"platform": ["android"]}) is False


def test_entry_when_round_trip():
    entry = Entry(
        id="01JA7K3M2X9F4Q8W6ZB1C2D3E4",
        module="gameplay.Jigsaw",
        entity="Reward",
        kind="exclusion",
        content="排除：不要在客户端去重，根因在服务端幂等。" + "x" * 10,
        note_date="2026-11-20",
        author="a",
        when={"platform": ["android"]},
    )
    parsed = Entry.from_markdown(entry.to_markdown())
    assert parsed.when == {"platform": ["android"]}


def test_config_loads_facets(tmp_path):
    mem = tmp_path / ".memory"
    mem.mkdir()
    (mem / "config.yaml").write_text(
        "facets:\n  platform: [ios, android]\n  model: str\n", encoding="utf-8")
    cfg = Config.load(tmp_path)
    assert set(cfg.facets) == {"platform", "model"}
    assert cfg.facets["model"].free is True


def test_config_rejects_bad_facets(tmp_path):
    mem = tmp_path / ".memory"
    mem.mkdir()
    (mem / "config.yaml").write_text("facets: [ios]\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="键值对"):
        Config.load(tmp_path)


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    root = tmp_path / "proj"
    mem = root / ".memory"
    mem.mkdir(parents=True)
    (mem / "config.yaml").write_text(
        "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n"
        "facets:\n  platform: [ios, android]\n",
        encoding="utf-8",
    )
    (mem / "modules.yaml").write_text(
        "categories: { gameplay: {} }\nmodules:\n  gameplay.Jigsaw: { paths: [src/**] }\n",
        encoding="utf-8",
    )
    (root / "src").mkdir()
    return root


def test_record_and_search_filter_by_when(project):
    text = "排除：Android 上不要用旧的发放接口，改走服务端幂等领取。"
    service = MemoryService(project)
    try:
        assert service.record("gameplay.Jigsaw", "Reward", "exclusion", text,
                              when={"platform": "android"})["ok"]
        assert service.record("gameplay.Jigsaw", "Reward", "exclusion", text + " iOS。",
                              when={"platform": "ios"})["ok"]
        assert service.record("gameplay.Jigsaw", "Reward", "risk", text + " 通用风险。")["ok"]
        android = service.search(module="gameplay.Jigsaw", when={"platform": "android"})
        kinds = {(i["kind"], tuple(i.get("when", {}).get("platform", []) or ["*"])) for i in android["items"]}
        assert ("exclusion", ("android",)) in kinds
        assert ("risk", ("*",)) in kinds
        assert ("exclusion", ("ios",)) not in kinds
        bad = service.record("gameplay.Jigsaw", "Reward", "exclusion", text, when={"platform": "web"})
        assert bad["ok"] is False and bad["code"] == "when_invalid"
    finally:
        service.close()


def test_when_requires_facets(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_AUTHOR", "alice")
    root = tmp_path / "plain"
    mem = root / ".memory"
    mem.mkdir(parents=True)
    (mem / "config.yaml").write_text(
        "project: { name: demo }\nvcs: none\nembedding: { backend: none }\nwiki: { auto: false }\n",
        encoding="utf-8",
    )
    (mem / "modules.yaml").write_text(
        "categories: { gameplay: {} }\nmodules:\n  gameplay.Jigsaw: { paths: [src/**] }\n",
        encoding="utf-8",
    )
    (root / "src").mkdir()
    service = MemoryService(root)
    try:
        bad = service.record("gameplay.Jigsaw", "Reward", "exclusion",
                             "排除：没有 facets 时不能写 when。" + "x" * 10,
                             when={"platform": "android"})
        assert bad["ok"] is False and "facets" in bad["error"]
    finally:
        service.close()
