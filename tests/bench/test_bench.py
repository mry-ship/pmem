import json
import sys
from pathlib import Path

import yaml

from pmem.bench.runner import RunMetrics, dry_run_executor, run_bench
from tests.conftest import run

CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\n"
ENTRY = """---
id: 01JA7K3M2X9F4Q8W6ZB1C2D3E4
module: gameplay.Jigsaw
entity: Reward
kind: exclusion
status: active
author: a
note_date: '2026-10-01'
---
不要在客户端重复发奖，奖励只由服务端发放
"""
CHECK = f'"{sys.executable}" -c "import pathlib,sys; sys.exit(0 if pathlib.Path(\'fixed.txt\').exists() else 1)"'


def make_cases(git_repo: Path) -> Path:
    memory = git_repo / ".memory"
    memory.mkdir()
    (memory / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (memory / "modules.yaml").write_text("modules: {}\n", encoding="utf-8")
    run(["git", "add", "-A"], git_repo)
    run(["git", "commit", "-q", "-m", "memory"], git_repo)
    folder = memory / "entries" / "gameplay.Jigsaw"
    folder.mkdir(parents=True)
    (folder / "01JA7K3M2X9F4Q8W6ZB1C2D3E4.md").write_text(ENTRY, encoding="utf-8")
    (git_repo / "hidden_check.txt").write_text("secret", encoding="utf-8")
    cases = git_repo / "cases.yaml"
    data = {"repeats": 2, "cases": [{"id": "reward", "commit": "HEAD", "prompt": "修复重复发奖", "check": CHECK,
                                     "check_files": {"hidden/check.txt": "hidden_check.txt"}}]}
    cases.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return cases


def test_arms_get_memory_only_when_on_and_results_are_summarised(git_repo):
    cases = make_cases(git_repo)
    seen = []

    def fake(prompt: str, cwd: Path, servers: dict, model: str, timeout: int) -> RunMetrics:
        has_memory = any((cwd / ".memory" / "entries").rglob("*.md"))
        seen.append((bool(servers), "project_rules" in prompt, has_memory, (cwd / "hidden").exists()))
        if servers:
            assert servers["pmem"]["args"] == ["serve", "--root", str(cwd)]
            (cwd / "fixed.txt").write_text("ok", encoding="utf-8")
        return RunMetrics(status="finished", duration_ms=1000 if servers else 3000,
                          input_tokens=100 if servers else 300, tool_calls=2 if servers else 6)

    out = git_repo / "out"
    records = run_bench(git_repo, cases, out, executor=fake, log=lambda _: None)

    assert seen == [(True, True, True, False), (False, False, False, False)] * 2
    assert [(r.arm, r.passed) for r in records] == [("on", True), ("off", False)] * 2
    assert len((out / "results.jsonl").read_text("utf-8").splitlines()) == 4
    summary = (out / "summary.md").read_text("utf-8")
    assert "通过率：100% vs 0%" in summary and "token 中位：-67%" in summary
    assert "worktree" not in run(["git", "worktree", "list"], git_repo).split("\n", 1)[-1]


def test_one_failing_run_is_recorded_and_the_rest_continue(git_repo):
    cases = make_cases(git_repo)
    calls = []

    def flaky(prompt: str, cwd: Path, servers: dict, model: str, timeout: int) -> RunMetrics:
        calls.append(bool(servers))
        if len(calls) == 1:
            raise ValueError("boom")
        return RunMetrics(status="finished")

    out = git_repo / "out"
    records = run_bench(git_repo, cases, out, repeats=1, executor=flaky, log=lambda _: None)
    assert [(r.metrics.status, r.passed) for r in records] == [("error", False), ("finished", False)]
    assert records[0].metrics.error == "boom" and (out / "summary.md").exists()


def test_dry_run_checks_the_starting_commit(git_repo):
    cases = make_cases(git_repo)
    records = run_bench(git_repo, cases, git_repo / "out", arms=("off",), repeats=1,
                        executor=dry_run_executor, log=lambda _: None)
    assert [r.passed for r in records] == [False]
    assert json.loads((git_repo / "out" / "results.jsonl").read_text("utf-8"))["metrics"]["status"] == "dry_run"
