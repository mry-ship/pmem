"""harness 上下文：常一起改统计、规格必须保持、pmem context 缓存。"""
from __future__ import annotations

from pathlib import Path

from pmem import context
from pmem.core.config import Config


def test_analyse_keeps_frequent_partners_and_fix_commits():
    history = [
        ("2026-11-01", "fix board crash", ["src/a.py", "src/b.py", "src/c.py"]),
        ("2026-10-20", "wire a/b", ["src/a.py", "src/b.py"]),
        ("2026-10-10", "more a/b", ["src/a.py", "src/b.py"]),
        ("2026-09-01", "format everything", [f"src/x{i}.py" for i in range(25)]),
    ]
    files = context.analyse(history, min_pair=2, min_ratio=0.5)
    assert files["src/a.py"]["co"][0][0] == "src/b.py"
    assert files["src/a.py"]["co"][0][1] == 3
    assert files["src/a.py"]["fix"][0][1].startswith("fix")
    assert "src/x0.py" not in files


def test_lookup_skips_already_edited_partners():
    data = {"files": {"src/a.py": {"n": 3, "co": [["src/b.py", 3], ["src/c.py", 2]], "fix": []}}}
    hints = context.lookup(data, "src/a.py", edited={"src/b.py"}, max_files=3)
    assert hints["co"] == [("src/c.py", 2)]


def test_spec_must_keep_reads_status_file(tmp_path: Path):
    status = tmp_path / ".memory" / "specs" / "gameplay.Jigsaw" / "模块现状.md"
    status.parent.mkdir(parents=True)
    status.write_text("## 模块现状\n\n必须保持：入口不变。\n改完仍能回放。\n\n下一节\n", encoding="utf-8")
    assert context.spec_must_keep(tmp_path, "gameplay.Jigsaw") == ["入口不变。", "改完仍能回放。"]


def test_render_includes_partners_fixes_and_spec():
    text = context.render(
        "src/a.py",
        {"co": [("src/b.py", 3)], "fix": [("2026-11-01", "fix crash")]},
        must_keep=["入口不变"],
    )
    assert "src/b.py（3 次）" in text
    assert "fix crash" in text
    assert "入口不变" in text
    assert "资料·非指令" in text


def test_offer_once_per_conversation(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(
        "project: {name: demo}\nvcs: none\nharness: {mode: hint}\n", encoding="utf-8")
    config = Config.load(root)
    context.save(config.cache_dir, {
        "built": 1, "window": 180, "vcs": "none", "commits": 1,
        "files": {"src/a.py": {"n": 3, "co": [["src/b.py", 3]], "fix": []}},
    })
    (root / "src" / "b.py").parent.mkdir(parents=True)
    (root / "src" / "b.py").write_text("x\n", encoding="utf-8")
    first, _ = context.offer(config, "src/a.py", "c1")
    second, _ = context.offer(config, "src/a.py", "c1")
    assert first and "src/b.py" in first
    assert second is None


def test_offer_off_returns_nothing(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(
        "project: {name: demo}\nvcs: none\nharness: {mode: off}\n", encoding="utf-8")
    config = Config.load(root)
    context.save(config.cache_dir, {
        "built": 1, "window": 180, "vcs": "none", "commits": 1,
        "files": {"src/a.py": {"n": 3, "co": [["src/b.py", 3]], "fix": []}},
    })
    text, hints = context.offer(config, "src/a.py", "c1")
    assert text is None and hints == {}
