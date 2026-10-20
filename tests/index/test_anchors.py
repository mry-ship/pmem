import os
import subprocess
import time
from dataclasses import replace
from datetime import date, datetime
from datetime import time as dt_time
from pathlib import Path

import pytest

from pmem.core.entry import Entry
from pmem.core.ids import new_ulid
from pmem.index.anchors import AnchorChecker, anchor_affinity, checked_at, symbol_block
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


@pytest.mark.parametrize("head", ["def f(): return 1", "def f() -> int: return 1"])
def test_one_line_python_def_ends_on_its_own_line(head):
    assert symbol_block(f"{head}\n\ndef g():\n    return 2\n", "f") == head


def test_trailing_comment_after_the_colon_still_ends_the_signature():
    text = "def f(a,  # 第一行\n      b):  # 注释\n    return a\n\ndef g():\n    return 2\n"
    assert symbol_block(text, "f") == "def f(a,  # 第一行\n      b):  # 注释\n    return a"


def test_decorators_belong_to_the_python_block():
    text = "import x\n\n\n@cache\n@route('/a:b')\ndef f():\n    return 1\n"
    assert symbol_block(text, "f") == "@cache\n@route('/a:b')\ndef f():\n    return 1"


def test_flush_left_multiline_string_does_not_end_the_python_block():
    text = 'def f():\n    s = """\n:顶格内容\n"""\n    return s\n\n\ndef g():\n    pass\n'
    assert symbol_block(text, "f") == 'def f():\n    s = """\n:顶格内容\n"""\n    return s'


def test_multiline_decorator_belongs_to_the_python_block():
    text = "@route(\n    '/a',\n)\ndef f():\n    return 1\n"
    assert symbol_block(text, "f") == text.rstrip()


def test_escaped_quote_in_default_does_not_swallow_the_rest_of_the_file():
    text = 'def f(a="it\\"s:"):\n    return 1\n\n\ndef g():\n    return 2\n'
    assert symbol_block(text, "f") == 'def f(a="it\\"s:"):\n    return 1'
    # 语法写错（改到一半）时按文本截取，同样不能吞掉后面的函数
    broken = text + "def h(:\n"
    assert symbol_block(broken, "f") == 'def f(a="it\\"s:"):\n    return 1'


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
    moment = day if "T" in day else f"{day}T12:00:00"
    env = {**os.environ, "GIT_AUTHOR_DATE": moment, "GIT_COMMITTER_DATE": moment}
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


def _ms(moment: str) -> int:
    return int(datetime.fromisoformat(moment).timestamp() * 1000)


def _memory(root: Path, moment: str, anchor: str) -> tuple[Entry, Path]:
    entry = Entry(id=new_ulid(_ms(moment)), module="m.M", entity="E", kind="risk", content="x" * 30,
                  note_date=moment[:10], author="a", anchors=[anchor])
    path = root / ".memory" / "entries" / "m.M" / f"{entry.id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(entry.to_markdown(), encoding="utf-8")
    return entry, path


def test_changes_later_on_the_same_day_make_a_memory_stale(git_repo):
    """原先按天比较：上午核对、下午有人改了关联函数，这条仍显示已核对。"""
    code = git_repo / "calc.py"
    code.write_text(PY, encoding="utf-8")
    _commit(git_repo, "calc", "2026-09-05")
    entry = _entry("A", "calc.py#Box.size")
    entry.verified, entry.verified_at = "2026-09-06", "2026-09-06T09:00:00"
    code.write_text(PY.replace("return 1", "return 2"), encoding="utf-8")
    _commit(git_repo, "size", "2026-09-06")
    problems = AnchorChecker(git_repo, detect_vcs(git_repo)).check([entry], {})
    assert problems["A"] == ["calc.py 中 Box.size 在 2026-09-06 之后改过"]
    entry.verified_at = "2026-09-06T13:00:00"
    assert AnchorChecker(git_repo, detect_vcs(git_repo)).check([entry], {}) == {}


def test_baseline_moves_only_to_the_first_commit_of_the_memory(git_repo):
    """记忆连同代码一起提交不算之后改过；之后再提交记忆文件（格式化、归档）不能把基准往后推。"""
    def ago(hours: float) -> str:
        return datetime.fromtimestamp(time.time() - hours * 3600).isoformat(timespec="seconds")

    code = git_repo / "calc.py"
    code.write_text(PY, encoding="utf-8")
    _commit(git_repo, "calc", ago(5))
    entry, path = _memory(git_repo, ago(4), "calc.py#Box.size")
    code.write_text(PY.replace("return 1", "return 2"), encoding="utf-8")
    vcs = detect_vcs(git_repo)
    assert AnchorChecker(git_repo, vcs).check([entry], {entry.id: path}) == {}
    together = ago(3)
    _commit(git_repo, "fix with memory", together)
    assert AnchorChecker(git_repo, vcs).check([entry], {entry.id: path}) == {}

    code.write_text(PY.replace("return 1", "return 3"), encoding="utf-8")
    _commit(git_repo, "someone else", ago(2))
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    _commit(git_repo, "format memories", ago(1))
    problems = AnchorChecker(git_repo, vcs).check([entry], {entry.id: path})
    assert problems[entry.id] == [f"calc.py 中 Box.size 在 {together[:10]} 之后改过"]


def test_committed_memory_without_later_commit_is_not_treated_as_draft(git_repo):
    """只记了核对日期（按当天结束算）、核对当天下午就提交了：之后没有提交不等于还是草稿，基准不能取现在。"""
    code = git_repo / "calc.py"
    code.write_text(PY, encoding="utf-8")
    _commit(git_repo, "calc", "2026-09-01")
    entry, path = _memory(git_repo, "2026-09-05T09:00:00", "calc.py#Box.size")
    entry.verified = "2026-09-05"
    path.write_text(entry.to_markdown(), encoding="utf-8")
    _commit(git_repo, "memory", "2026-09-05T10:00:00")
    code.write_text(PY.replace("return 1", "return 2"), encoding="utf-8")
    _commit(git_repo, "later change", "2026-09-08")
    problems = AnchorChecker(git_repo, detect_vcs(git_repo)).check([entry], {entry.id: path})
    assert problems[entry.id] == ["calc.py 中 Box.size 在 2026-09-05 之后改过"]


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def _merged_old_branch(git_repo: Path, side_change: tuple[str, str]) -> tuple[Entry, Path]:
    """别人在 9 月 2 日的分支上改了代码；我 9 月 5 日在没有这次提交的本地写下记忆，9 月 10 日才合并进来。"""
    code = git_repo / "calc.py"
    code.write_text(PY, encoding="utf-8")
    _commit(git_repo, "calc", "2026-09-01")
    main = _git(git_repo, "rev-parse", "--abbrev-ref", "HEAD")
    _git(git_repo, "checkout", "-q", "-b", "side")
    code.write_text(PY.replace(*side_change), encoding="utf-8")
    _commit(git_repo, "side change", "2026-09-02")
    _git(git_repo, "checkout", "-q", main)
    entry, path = _memory(git_repo, "2026-09-05T10:00:00", "calc.py#Box.size")
    entry.revision = "git:" + _git(git_repo, "rev-parse", "--short", "HEAD")
    path.write_text(entry.to_markdown(), encoding="utf-8")
    _commit(git_repo, "memory", "2026-09-05T11:00:00")
    env = {**os.environ, "GIT_AUTHOR_DATE": "2026-09-10T12:00:00", "GIT_COMMITTER_DATE": "2026-09-10T12:00:00"}
    subprocess.run(["git", "merge", "-q", "--no-edit", "side"], cwd=git_repo, check=True, env=env)
    return entry, path


def test_older_commit_merged_in_after_writing_makes_a_memory_stale(git_repo):
    """按提交时间过滤会漏掉：这次提交早于写入，但写入时本地还没有它。"""
    entry, path = _merged_old_branch(git_repo, ("return 1", "return 2"))
    problems = AnchorChecker(git_repo, detect_vcs(git_repo)).check([entry], {entry.id: path})
    assert problems[entry.id] == ["calc.py 中 Box.size 于 2026-09-02 改过（写入时本地还没有这次提交，之后拉取或合并进来）"]
    file_level = replace(entry, anchors=["calc.py"])
    assert AnchorChecker(git_repo, detect_vcs(git_repo)).check([file_level], {entry.id: path})[entry.id] == [
        "calc.py 于 2026-09-02 改过（写入时本地还没有这次提交，之后拉取或合并进来）"]


def test_merged_commit_touching_another_function_is_ignored(git_repo):
    entry, path = _merged_old_branch(git_repo, ("return total", "return 0"))
    assert AnchorChecker(git_repo, detect_vcs(git_repo)).check([entry], {entry.id: path}) == {}


def test_confirmed_memory_is_not_rechecked_against_its_write_revision(git_repo):
    """核对时看到的已经是合并后的代码；再按写入时的版本比较，确认之后仍会一直显示需核实。"""
    entry, path = _merged_old_branch(git_repo, ("return 1", "return 2"))
    entry.verified, entry.verified_at = "2026-09-11", "2026-09-11T09:00:00"
    assert AnchorChecker(git_repo, detect_vcs(git_repo)).check([entry], {entry.id: path}) == {}


def test_invalid_dates_do_not_silently_disable_the_check(git_repo):
    """写入日无效时基准为 0：Windows 上 1970 年附近的时间戳转换会抛错，被吞掉就成了“都没改过”。"""
    code = git_repo / "calc.py"
    code.write_text(PY, encoding="utf-8")
    _commit(git_repo, "calc", "2026-09-01")
    entry = _entry("A", "calc.py")
    entry.note_date = "unknown"
    assert AnchorChecker(git_repo, detect_vcs(git_repo)).check([entry], {}) == {"A": ["calc.py 于 2026-09-01 改过"]}


def test_removed_definition_is_reported_as_missing(git_repo):
    code = git_repo / "calc.py"
    code.write_text(PY, encoding="utf-8")
    _commit(git_repo, "calc", "2026-09-01")
    code.write_text(PY.replace("def first(a,\n          b) -> int:", "first = None\nif (a,\n          b):"),
                    encoding="utf-8")
    _commit(git_repo, "drop first", "2026-09-10")
    problems = AnchorChecker(git_repo, detect_vcs(git_repo)).check([_entry("A", "calc.py#first")], {})
    assert problems["A"] == ["calc.py 中找不到 first"]


def test_checked_moment_prefers_precise_times():
    entry = _entry("A", "calc.py")
    assert _day_of(checked_at(entry)) == "2026-09-05"
    entry.verified = "2026-09-07"
    assert checked_at(entry) == datetime.combine(date(2026, 9, 7), dt_time.max).timestamp()
    entry.verified_at = "2026-09-07T08:30:00"
    assert checked_at(entry) == datetime(2026, 9, 7, 8, 30).timestamp()
    stamped = Entry(id=new_ulid(_ms("2026-09-05T10:00:00")), module="m.M", entity="E", kind="risk",
                    content="x" * 30, note_date="2026-09-05", author="a")
    assert checked_at(stamped) == datetime(2026, 9, 5, 10).timestamp()
    stamped.note_date = "2026-08-01"
    assert _day_of(checked_at(stamped)) == "2026-08-01"


def _day_of(moment: float) -> str:
    return datetime.fromtimestamp(moment).date().isoformat()


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


def test_anchor_affinity_matches_file_then_folder():
    assert anchor_affinity(["src/Jigsaw/Board.cs#Snap"], "src/jigsaw/board.cs") == 2
    assert anchor_affinity(["./src/Jigsaw/Board.cs"], "src\\Jigsaw\\Board.cs") == 2
    assert anchor_affinity(["src/Jigsaw/Piece.cs#Drop"], "src/Jigsaw/Board.cs") == 1
    assert anchor_affinity(["src/Shop/Board.cs"], "src/Jigsaw/Board.cs") == 0
    assert anchor_affinity(["README.md"], "setup.py") == 0
    assert anchor_affinity([], "src/Jigsaw/Board.cs") == 0
    assert anchor_affinity(["src/Jigsaw/Board.cs"], None) == 0


def test_digest_gives_the_open_file_up_to_half_the_slots():
    from pmem.index.graph import digest

    def entry(n, kind, anchor):
        return Entry(id=f"01M5AA00000000000000000{n:03d}", module="gameplay.Jigsaw", entity=f"T{n}", kind=kind,
                     content="正文", note_date="2026-10-19", author="a", anchors=[anchor])

    others = [entry(i, "exclusion", f"src/Jigsaw/UI/P{i}.cs") for i in range(6)]
    mine = [entry(10 + i, "conclusion", "src/Jigsaw/Board.cs#Snap") for i in range(4)]
    plain = digest(others + mine)
    assert all(e.kind == "exclusion" for e in plain)
    picked = digest(others + mine, path="src/Jigsaw/Board.cs")
    assert sum(e in mine for e in picked) == 3 and sum(e in others for e in picked) == 3
