import os
import subprocess
from pathlib import Path

import pytest

from pmem.core.entry import Entry
from pmem.index.anchors import AnchorChecker, symbol_block
from pmem.vcs.detect import detect_vcs

PY = '''\
import os


def first(a,
          b) -> int:
    total = a + b

    return total


class Box:
    def size(self):
        return 1
'''

CS = '''\
public class Reward
{
    public void Claim(int level)
    {
        if (level > 0) { Give(); }
    }

    private int Count => 3;
}
'''


def test_python_block_spans_multiline_signature_and_blank_lines():
    block = symbol_block(PY, "first")
    assert block.startswith("def first(a,") and block.endswith("return total")
    assert symbol_block(PY, "Box.size") == "    def size(self):\n        return 1"


def test_brace_block_for_csharp_method():
    block = symbol_block(CS, "Reward.Claim")
    assert block.splitlines()[0].strip() == "public void Claim(int level)"
    assert block.splitlines()[-1].strip() == "}" and "Give();" in block


def test_qualified_symbol_is_looked_up_inside_its_class():
    text = ("class Cache:\n    def close(self):\n        return 1\n\n\n"
            "class Index:\n    def close(self):\n        return 2\n")
    assert symbol_block(text, "Index.close") == "    def close(self):\n        return 2"
    assert symbol_block(text, "Cache.close") == "    def close(self):\n        return 1"
    assert symbol_block(text, "Missing.close") == "    def close(self):\n        return 1"
    ctor = "public class Shop\n{\n    public Shop(int a)\n    {\n        x = a;\n    }\n}\n"
    assert symbol_block(ctor, "Shop.Shop").splitlines()[0].strip() == "public Shop(int a)"


def test_calls_are_not_mistaken_for_definitions():
    assert symbol_block("void Run() {\n    return Claim(1);\n}\n", "Claim") is None
    assert symbol_block("x = 1\n", "missing") is None


def _commit(root: Path, message: str, day: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_DATE": f"{day}T12:00:00", "GIT_COMMITTER_DATE": f"{day}T12:00:00"}
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True, env=env)


def _entry(entry_id: str, anchor: str) -> Entry:
    return Entry(id=entry_id, module="m.M", entity="E", kind="risk", content="x" * 30, note_date="2026-09-05",
                 author="a", anchors=[anchor])


def test_only_the_changed_function_makes_a_memory_stale(git_repo):
    code = git_repo / "calc.py"
    code.write_text(PY, encoding="utf-8")
    _commit(git_repo, "calc", "2026-09-01")
    code.write_text(PY.replace("return 1", "return 2"), encoding="utf-8")
    _commit(git_repo, "size", "2026-09-10")
    checker = AnchorChecker(git_repo, detect_vcs(git_repo))
    entries = [_entry("A", "calc.py#first"), _entry("B", "calc.py#Box.size"), _entry("C", "calc.py")]
    problems = checker.check(entries, {})
    assert "A" not in problems
    assert problems["B"] == ["calc.py 中 Box.size 在 2026-09-05 之后改过"]
    assert problems["C"] == ["calc.py 于 2026-09-10 改过"]


def test_results_are_shared_across_processes_until_code_changes(git_repo, tmp_path_factory, monkeypatch):
    code = git_repo / "calc.py"
    code.write_text(PY, encoding="utf-8")
    _commit(git_repo, "calc", "2026-09-01")
    cache = tmp_path_factory.mktemp("cache") / "anchors.json"
    entries = [_entry("A", "calc.py#first")]
    assert AnchorChecker(git_repo, detect_vcs(git_repo), cache).check(entries, {}) == {}

    calls = []
    monkeypatch.setattr(AnchorChecker, "_check", lambda self, es, files: calls.append(es) or {})
    fresh = AnchorChecker(git_repo, detect_vcs(git_repo), cache)
    assert fresh.check(entries, {}) == {} and calls == []
    fresh.check([*entries, _entry("B", "calc.py#Box.size")], {})
    assert [e.id for e in calls[0]] == ["B"]

    monkeypatch.undo()
    code.write_text(PY.replace("return total", "return 0"), encoding="utf-8")
    problems = AnchorChecker(git_repo, detect_vcs(git_repo), cache).check(entries, {})
    assert problems["A"] == ["calc.py 中 first 在 2026-09-05 之后改过"]


def test_slow_dirty_listing_is_not_used_for_the_cache(git_repo, tmp_path_factory, monkeypatch):
    code = git_repo / "calc.py"
    code.write_text(PY, encoding="utf-8")
    _commit(git_repo, "calc", "2026-09-01")
    vcs = detect_vcs(git_repo)
    monkeypatch.setattr(type(vcs), "cheap_dirty_files", False)
    monkeypatch.setattr(type(vcs), "dirty_files", lambda self: pytest.fail("不该为指纹列未提交文件"))
    cache = tmp_path_factory.mktemp("cache") / "anchors.json"
    assert AnchorChecker(git_repo, vcs, cache).check([_entry("A", "calc.py#first")], {}) == {}
    assert not cache.exists()


def test_without_history_symbol_anchors_fall_back_to_file_level(tmp_path):
    code = tmp_path / "calc.py"
    code.write_text(PY, encoding="utf-8")
    checker = AnchorChecker(tmp_path, detect_vcs(tmp_path, "none"))
    assert "A" in checker.check([_entry("A", "calc.py#first")], {})
