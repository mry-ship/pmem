from pathlib import Path

import pytest
import yaml

from pmem.cli.main import main
from pmem.core.ids import ulid_ms
from pmem.storage.files import FilesStorage
from pmem.vcs.base import VCS

lancedb = pytest.importorskip("lancedb")

ROWS = {
    "mem_gameplay__Jigsaw": [
        {"id": "a1", "entity": "Reward", "note_date": "2026-09-01", "created_at": "2026-09-01T10:00:00",
         "content": "排除：客户端去重无效，重复发放的根因是服务端 Claim 没有按关卡做幂等校验。"},
        {"id": "a2", "entity": "Reward", "note_date": "2026-08-01", "created_at": "2026-08-01T10:00:00",
         "content": "拼图奖励配置表按关卡段拆分，修改后需要同步更新服务端的发奖白名单。"},
    ],
    "mem_system__AdChase": [
        {"id": "b1", "entity": "Strategy", "note_date": "2026-09-05", "created_at": "2026-09-05T10:00:00",
         "content": "测试环境 api_key = 'sk-abcdefghijklmnopqrstuvwx' 只能在内网使用，广告追投策略按 eCPM 分层。"},
    ],
}
CATALOG = """
categories:
  gameplay:
    label: 核心玩法
    modules:
      Jigsaw: { entities: [Reward] }
      MatchCore: { entities: [] }
  system:
    label: 系统
    modules: {}
"""


def make_db(path: Path) -> Path:
    db = lancedb.connect(str(path))
    for table, rows in ROWS.items():
        db.create_table(table, data=[{**r, "module": table, "category": "", "job_id": "", "vector": [0.0, 1.0]}
                                     for r in rows])
    db.create_table("catalog", data=[{"x": 1}])
    return path


@pytest.fixture
def project(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    main(["init", "--root", str(root), "--type", "generic"])
    (root / ".memory" / "config.yaml").write_text("vcs: none\nembedding: { backend: none }\n", encoding="utf-8")
    return root


def entries(root: Path):
    return sorted((e for _, e in FilesStorage(root, VCS(root)).iter_all()), key=lambda e: e.id)


def test_import_is_readonly_idempotent_and_keeps_time_order(project, tmp_path, capsys):
    db = make_db(tmp_path / "db")
    catalog = tmp_path / "modules.yaml"
    catalog.write_text(CATALOG, encoding="utf-8")
    before = sorted(p.name for p in db.iterdir())

    args = ["import", "--root", str(project), "--lancedb", str(db), "--catalog", str(catalog), "--author", "team"]
    assert main(args) == 0
    out = capsys.readouterr().out
    assert "已导入 2 条" in out and "敏感信息而跳过 1 条" in out

    imported = entries(project)
    assert [e.source_conversation for e in imported] == ["lancedb:a2", "lancedb:a1"]
    assert ulid_ms(imported[0].id) < ulid_ms(imported[1].id)
    assert {e.module for e in imported} == {"gameplay.Jigsaw"}
    assert all(e.kind == "conclusion" and e.author == "team" for e in imported)

    modules = yaml.safe_load((project / ".memory" / "modules.yaml").read_text(encoding="utf-8"))
    assert {"gameplay.Jigsaw", "gameplay.MatchCore", "system.AdChase"} <= set(modules["modules"])
    assert modules["categories"]["gameplay"]["label"] == "核心玩法"

    assert main(args) == 0
    assert "跳过已导入过的 2 条" in capsys.readouterr().out
    assert len(entries(project)) == 2
    assert sorted(p.name for p in db.iterdir()) == before


def test_guess_kind_and_dry_run(project, tmp_path, capsys):
    db = make_db(tmp_path / "db")
    assert main(["import", "--root", str(project), "--lancedb", str(db), "--dry-run", "--guess-kind"]) == 0
    out = capsys.readouterr().out
    assert "将导入 2 条" in out and "exclusion 1" in out
    assert entries(project) == []
