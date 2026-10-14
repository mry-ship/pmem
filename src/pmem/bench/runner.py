"""pmem bench：同一任务分别在“有记忆 / 无记忆”下交给 Agent，比较成功率、token、耗时与工具调用。

每次运行都在独立的 git worktree 中从指定提交开始；Agent 结束后再放入隐藏的验收文件并执行检查命令。
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import statistics
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from pmem.core.config import Config
from pmem.generate.templates import RULE

ARMS = ("on", "off")
DEFAULT_MODEL = "composer-2.5"
EDIT_TOOLS = {"write", "strreplace", "edit", "multiedit", "delete", "editnotebook"}


@dataclass
class Case:
    id: str
    prompt: str
    commit: str = "HEAD"
    check: str = ""
    check_files: dict[str, str] = field(default_factory=dict)
    setup: str = ""
    timeout_minutes: int = 20


@dataclass
class RunMetrics:
    status: str = "unknown"
    duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    tool_calls: int = 0
    memory_calls: int = 0
    edit_calls: int = 0
    cost_cents: float | None = None
    error: str = ""


@dataclass
class RunRecord:
    case: str
    arm: str
    repeat: int
    passed: bool
    metrics: RunMetrics
    check_output: str = ""


Executor = Callable[[str, Path, dict, str, int], RunMetrics]


def load_cases(path: Path) -> tuple[dict, list[Case]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = [Case(**raw) for raw in data.get("cases") or []]
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("用例 id 不能重复")
    return data, cases


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败：{proc.stderr.strip()}")
    return proc.stdout


def prepare_workspace(repo: Path, case: Case, arm: str, target: Path) -> Path:
    """在 target 建 worktree；on 组放入当前记忆库，off 组清空记忆。"""
    _git(repo, "worktree", "add", "--detach", str(target), case.commit)
    memory = target / ".memory"
    if memory.exists():
        shutil.rmtree(memory / "entries", ignore_errors=True)
    if arm == "on":
        shutil.copytree(repo / ".memory", memory, dirs_exist_ok=True)
    else:
        (memory / "entries").mkdir(parents=True, exist_ok=True)
    return target


def remove_workspace(repo: Path, target: Path) -> None:
    if (target / ".memory" / "config.yaml").exists():
        shutil.rmtree(Config.load(target).cache_dir, ignore_errors=True)
    subprocess.run(["git", "worktree", "remove", "--force", str(target)], cwd=repo, capture_output=True, check=False)
    shutil.rmtree(target, ignore_errors=True)


def arm_options(arm: str, workspace: Path) -> tuple[str, dict]:
    """返回 (提示词前缀, MCP 配置)。只给 on 组 pmem 工具与使用规则，其余设置一律不加载。"""
    if arm != "on":
        return "", {}
    body = RULE.split("---", 2)[-1] if RULE.startswith("---") else RULE
    rule = "\n".join(line for line in body.strip().splitlines() if not line.startswith("<!--"))
    servers = {
        "pmem": {
            "command": "pmem",
            "args": ["serve", "--root", str(workspace)],
            "env": {"PMEM_NO_EVENTS": "1"},
        }
    }
    return f"<project_rules>\n{rule}\n</project_rules>\n\n", servers


def _utf8_env() -> dict:
    return {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def run_check(case: Case, repo: Path, workspace: Path) -> tuple[bool, str]:
    for dest, src in case.check_files.items():
        target = workspace / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / src, target)
    if not case.check:
        return True, ""
    proc = subprocess.run(case.check, cwd=workspace, shell=True, capture_output=True, text=True, env=_utf8_env(),
                          encoding="utf-8", errors="replace", check=False, timeout=600)
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def sdk_executor(prompt: str, cwd: Path, mcp_servers: dict, model: str, timeout_minutes: int) -> RunMetrics:
    try:
        from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions, StdioMcpServerConfig
    except ImportError as exc:
        raise RuntimeError("缺少 Cursor SDK：pip install \"pmem[bench]\" 或 uv pip install cursor-sdk") from exc
    api_key = os.environ.get("CURSOR_API_KEY")
    if not api_key:
        raise RuntimeError("请先设置环境变量 CURSOR_API_KEY（Cursor Dashboard → Integrations）")

    metrics = RunMetrics()
    started = time.monotonic()
    seen_calls: set[str] = set()
    options = AgentOptions(
        model=model,
        api_key=api_key,
        local=LocalAgentOptions(cwd=str(cwd)),
        mcp_servers={name: StdioMcpServerConfig(**cfg) for name, cfg in mcp_servers.items()} or None,
    )
    try:
        with Agent.create(options) as agent:
            run = agent.send(prompt)
            for message in run.messages():
                if getattr(message, "type", "") != "tool_call" or message.call_id in seen_calls:
                    continue
                seen_calls.add(message.call_id)
                name = str(message.name or "").lower()
                metrics.tool_calls += 1
                metrics.memory_calls += "search_memory" in name or "record_memory" in name
                metrics.edit_calls += name in EDIT_TOOLS
                if time.monotonic() - started > timeout_minutes * 60 and run.supports("cancel"):
                    run.cancel()
            result = run.wait()
            metrics.status = str(result.status)
            metrics.duration_ms = result.duration_ms or int((time.monotonic() - started) * 1000)
            if result.usage:
                metrics.input_tokens = result.usage.input_tokens
                metrics.output_tokens = result.usage.output_tokens
                metrics.cache_read_tokens = result.usage.cache_read_tokens
            with contextlib.suppress(Exception):
                usage = run.usage()
                if usage is not None and usage.cost is not None:
                    metrics.cost_cents = usage.cost.charged_cents
    except CursorAgentError as exc:
        metrics.status = "startup_error"
        metrics.error = str(exc)
    return metrics


def dry_run_executor(prompt: str, cwd: Path, mcp_servers: dict, model: str, timeout_minutes: int) -> RunMetrics:
    """不调用 Agent，直接验收起始提交：用于确认用例有效（应当不通过）。"""
    return RunMetrics(status="dry_run")


def run_bench(
    repo: Path,
    cases_path: Path,
    out_dir: Path,
    arms: tuple[str, ...] = ARMS,
    repeats: int | None = None,
    model: str | None = None,
    executor: Executor | None = None,
    only: list[str] | None = None,
    log: Callable[[str], None] = print,
) -> list[RunRecord]:
    settings, cases = load_cases(cases_path)
    repeats = repeats or int(settings.get("repeats", 1))
    model = model or settings.get("model") or DEFAULT_MODEL
    executor = executor or sdk_executor
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.jsonl"
    records: list[RunRecord] = []
    scratch = Path(tempfile.mkdtemp(prefix="pmem-bench-"))
    try:
        for case in cases:
            if only and case.id not in only:
                continue
            for i in range(repeats):
                for arm in arms:
                    workspace = scratch / f"{case.id}-{arm}-{i}"
                    log(f"[{case.id}] {arm} 第 {i + 1}/{repeats} 次……")
                    try:
                        prepare_workspace(repo, case, arm, workspace)
                        if case.setup:
                            subprocess.run(case.setup, cwd=workspace, shell=True, capture_output=True, check=False,
                                           env=_utf8_env())
                        prefix, servers = arm_options(arm, workspace)
                        metrics = executor(prefix + case.prompt, workspace, servers, model, case.timeout_minutes)
                        passed, output = run_check(case, repo, workspace) if metrics.status != "startup_error" else (False, "")
                    finally:
                        remove_workspace(repo, workspace)
                    record = RunRecord(case.id, arm, i, passed, metrics, output)
                    records.append(record)
                    with results_path.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
                    log(f"  {'通过' if passed else '未通过'}，{metrics.duration_ms / 1000:.0f} 秒，"
                        f"{metrics.input_tokens + metrics.output_tokens} token，{metrics.tool_calls} 次工具调用")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    (out_dir / "summary.md").write_text(summarize(records), encoding="utf-8")
    return records


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _delta(on: float, off: float) -> str:
    return f"{(on - off) / off:+.0%}" if off else "—"


def summarize(records: list[RunRecord]) -> str:
    lines = ["# pmem bench 结果", "", "| 用例 | 组 | 次数 | 通过率 | 耗时中位(秒) | token 中位 | 工具调用中位 | 记忆工具调用 |",
             "|---|---|---|---|---|---|---|---|"]
    overall: dict[str, list[RunRecord]] = {arm: [] for arm in ARMS}
    for case in dict.fromkeys(r.case for r in records):
        for arm in ARMS:
            rows = [r for r in records if r.case == case and r.arm == arm]
            if not rows:
                continue
            overall[arm] += rows
            lines.append(
                f"| {case} | {arm} | {len(rows)} | {sum(r.passed for r in rows) / len(rows):.0%} "
                f"| {_median([r.metrics.duration_ms / 1000 for r in rows]):.0f} "
                f"| {_median([r.metrics.input_tokens + r.metrics.output_tokens for r in rows]):.0f} "
                f"| {_median([r.metrics.tool_calls for r in rows]):.0f} "
                f"| {_median([r.metrics.memory_calls for r in rows]):.0f} |"
            )
    on, off = overall["on"], overall["off"]
    if on and off:
        def med(rows, fn):
            return _median([fn(r) for r in rows])

        def tokens(r):
            return r.metrics.input_tokens + r.metrics.output_tokens

        lines += [
            "",
            "## 有记忆 vs 无记忆",
            "",
            f"- 通过率：{sum(r.passed for r in on) / len(on):.0%} vs {sum(r.passed for r in off) / len(off):.0%}",
            f"- 耗时中位：{_delta(med(on, lambda r: r.metrics.duration_ms), med(off, lambda r: r.metrics.duration_ms))}",
            f"- token 中位：{_delta(med(on, tokens), med(off, tokens))}",
            f"- 工具调用中位：{_delta(med(on, lambda r: r.metrics.tool_calls), med(off, lambda r: r.metrics.tool_calls))}",
            "",
            "每组样本少于 5 次时只看方向；Agent 输出有随机性，建议 repeats ≥ 3。",
        ]
    return "\n".join(lines) + "\n"
