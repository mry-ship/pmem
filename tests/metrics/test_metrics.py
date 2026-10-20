import json
import time
from pathlib import Path

import pytest

from pmem.core.config import Config
from pmem.metrics.cite import assistant_text, judge
from pmem.metrics.events import log_event, read_events
from pmem.metrics.report import build_report, render
from pmem.service import MemoryService

MEMORY = (
    "拼图奖励重复发放的根因：PuzzleRewardService.Claim 在断线重连时被调用两次，"
    "服务端没有做幂等校验，导致同一关卡奖励入账两次。修复方案是按关卡 id 加领取记录。"
)


def write_transcript(path: Path, *replies: str) -> Path:
    lines = [json.dumps({"role": "user", "message": {"content": [{"type": "text", "text": "修一下拼图奖励"}]}})]
    for reply in replies:
        lines.append(json.dumps({"role": "assistant", "message": {"content": [{"type": "text", "text": reply}]}}))
    lines.append(json.dumps({"type": "turn_ended", "status": "completed"}))
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_events_roundtrip_and_since_filter(tmp_path):
    log_event(tmp_path, "search", ids=["A"], conv=None)
    records = list(read_events(tmp_path))
    assert records[0]["type"] == "search" and "conv" not in records[0]
    assert list(read_events(tmp_path, since=time.time() + 10)) == []


def test_read_events_skips_lines_that_are_json_but_not_objects(tmp_path):
    (tmp_path / "events.jsonl").write_text('123\n["x"]\n{"ts": 1, "event": "ok"}\n', encoding="utf-8")
    assert [r["event"] for r in read_events(tmp_path)] == ["ok"]


def _log_many(cache_dir: str, worker: int, count: int) -> None:
    for n in range(count):
        log_event(Path(cache_dir), "search", worker=worker, n=n, query="检索" * 3000)


def test_concurrent_processes_never_corrupt_lines(tmp_path, monkeypatch):
    import multiprocessing

    monkeypatch.delenv("PMEM_NO_EVENTS", raising=False)
    ctx = multiprocessing.get_context("spawn")
    workers = [ctx.Process(target=_log_many, args=(str(tmp_path), w, 40)) for w in range(4)]
    for p in workers:
        p.start()
    for p in workers:
        p.join(60)
    lines = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 160
    assert {(r["worker"], r["n"]) for r in map(json.loads, lines)} == {(w, n) for w in range(4) for n in range(40)}


def test_events_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_NO_EVENTS", "1")
    log_event(tmp_path, "search")
    assert not (tmp_path / "events.jsonl").exists()


def test_assistant_text_reads_only_assistant_messages(tmp_path):
    transcript = write_transcript(tmp_path / "t.jsonl", "第一段", "第二段")
    assert assistant_text(transcript) == "第一段\n\n第二段"


def test_judge_detects_reuse_and_ignores_unrelated_reply():
    used = "查到已有结论：PuzzleRewardService.Claim 在断线重连时被调用两次，服务端没有做幂等校验，我按关卡 id 加领取记录。"
    unrelated = "商店界面的按钮颜色改成蓝色，并调整了排行榜的刷新间隔。"
    assert judge({"m": MEMORY}, used)["m"]["cited"] is True
    assert judge({"m": MEMORY}, unrelated)["m"]["cited"] is False


CONFIG = "project: { name: demo }\nvcs: none\nembedding: { backend: none }\n"
MODULES = "categories: { gameplay: {} }\nmodules:\n  gameplay.Jigsaw: { paths: [src/Jigsaw/**] }\n  gameplay.Shop: { paths: [src/Shop/**] }\n"


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("PMEM_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "proj"
    (root / ".memory").mkdir(parents=True)
    (root / ".memory" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    (root / ".memory" / "modules.yaml").write_text(MODULES, encoding="utf-8")
    return root


def record_as(root: Path, monkeypatch, author: str, kind: str, content: str) -> str:
    monkeypatch.setenv("PMEM_AUTHOR", author)
    service = MemoryService(root)
    try:
        result = service.record("gameplay.Jigsaw", "Reward", kind, content)
    finally:
        service.close()
    assert result["ok"], result
    return result["id"]


def test_report_counts_benefits(project, tmp_path, monkeypatch):
    other_id = record_as(project, monkeypatch, "alice", "exclusion", MEMORY)
    record_as(project, monkeypatch, "me", "conclusion", "商店价格表缓存失效的结论：配置热更新后需要清理本地缓存才能生效。")

    monkeypatch.setenv("PMEM_AUTHOR", "me")
    service = MemoryService(project, source="mcp")
    try:
        found = service.search(module="gameplay.Jigsaw", query="拼图奖励重复", source_conversation="c1")
    finally:
        service.close()
    assert other_id in [i["id"] for i in found["items"]]

    cache = Config.load(project).cache_dir
    transcript = write_transcript(
        tmp_path / "c1.jsonl",
        "已有记忆说明 PuzzleRewardService.Claim 在断线重连时被调用两次，服务端没有做幂等校验，按关卡 id 加领取记录即可。",
    )
    log_event(cache, "gate", conv="c1", module="gameplay.Jigsaw")
    log_event(cache, "search_call", conv="c1", module="gameplay.Jigsaw", via="mcp")
    log_event(cache, "edit", conv="c1", module="gameplay.Jigsaw", file="src/Jigsaw/A.cs")
    log_event(cache, "stop", conv="c1", status="completed", input_tokens=500, output_tokens=20,
              transcript=str(transcript), returned=[other_id], nudged=["gameplay.Jigsaw"])

    report = build_report(project, days=7, heat=False)
    assert report["search"]["hits"] >= 1
    assert report["search"]["avoided"] >= 1
    assert report["search"]["reused"] >= 1 and report["search"]["reused_authors"] == 1
    assert report["citations"]["cited"] == 1, report["citations"]
    assert report["citations"]["top"] == [(other_id, 1)]
    assert report["records"]["by_kind"] == {"conclusion": 1}
    assert report["habits"]["gates"] == 1 and report["habits"]["gate_converted"] == 1
    assert report["habits"]["nudges"] == 1 and report["habits"]["nudge_converted"] == 0
    assert report["compare"]["hit"]["n"] == 1 and report["compare"]["enough"] is False
    assert report["assets"]["memories"] == 2 and report["assets"]["modules_registered"] == 2
    text = render(report)
    assert "跨人复用" in text and "样本不足" in text


def test_memory_written_in_the_same_conversation_is_not_reuse(project, tmp_path, monkeypatch):
    cache = Config.load(project).cache_dir
    log_event(cache, "prompt", conv="c3")
    own_id = record_as(project, monkeypatch, "me", "risk", MEMORY)
    transcript = write_transcript(tmp_path / "c3.jsonl", MEMORY)
    log_event(cache, "mcp_search", conv="c3", ids=[own_id])
    log_event(cache, "stop", conv="c3", status="completed", transcript=str(transcript))
    report = build_report(project, days=7, heat=False)
    assert report["citations"]["cited"] == 0
    assert report["usage"]["returned_memories"] == 0


def test_usage_lists_most_used_and_never_used(project, tmp_path, monkeypatch):
    used = record_as(project, monkeypatch, "alice", "exclusion", MEMORY)
    ignored = record_as(project, monkeypatch, "alice", "conclusion", "商店价格表缓存失效：配置热更新后需要清理本地缓存才能生效。")
    monkeypatch.setenv("PMEM_AUTHOR", "me")
    cache = Config.load(project).cache_dir
    for n in range(3):
        conv = f"u{n}"
        transcript = write_transcript(tmp_path / f"{conv}.jsonl", MEMORY if n == 0 else "改好了，测试通过。")
        log_event(cache, "mcp_search", conv=conv, ids=[used, ignored])
        log_event(cache, "mcp_search", conv=conv, ids=[ignored])
        log_event(cache, "stop", conv=conv, status="completed", transcript=str(transcript))
    report = build_report(project, days=7, heat=False)
    usage = report["usage"]
    assert usage["returned_memories"] == 2
    assert [(r["id"], r["cited"], r["returned"]) for r in usage["top"]] == [(used, 1, 3)]
    assert [(r["id"], r["returned"]) for r in usage["review"]] == [(ignored, 3)]
    text = render(report)
    assert "最常被用到" in text and ignored in text


def test_records_are_counted_from_files_even_without_events(project, monkeypatch):
    monkeypatch.setenv("PMEM_NO_EVENTS", "1")
    record_as(project, monkeypatch, "me", "risk", MEMORY)
    record_as(project, monkeypatch, "me", "decision", MEMORY)
    monkeypatch.delenv("PMEM_NO_EVENTS")
    report = build_report(project, days=7, heat=False)
    assert report["records"]["by_kind"] == {"risk": 1, "decision": 1}
    assert report["assets"]["uncommitted"] is None


def test_cli_record_after_nudge_counts_as_converted(project):
    cache = Config.load(project).cache_dir
    log_event(cache, "stop", conv="c2", status="completed", nudged=["gameplay.Jigsaw"])
    log_event(cache, "record_call", conv="c2", module="gameplay.Jigsaw", via="cli")
    report = build_report(project, days=7, heat=False)
    assert report["habits"]["nudges"] == 1 and report["habits"]["nudge_converted"] == 1


def test_analysis_conversations_are_reported(project):
    cache = Config.load(project).cache_dir
    for conv, left in (("a1", ["gameplay.Jigsaw"]), ("a2", None)):
        log_event(cache, "prompt", conv=conv, analysis=True)
        log_event(cache, "search_call", conv=conv, module="gameplay.Jigsaw", via="mcp")
        log_event(cache, "stop", conv=conv, status="completed", analyzed=left)
    report = build_report(project, days=7, heat=False)
    habits = report["habits"]
    assert (habits["analysis_conversations"], habits["analysis_left"], habits["analysis_left_modules"]) == (2, 1, 1)
    # 默认已开启结束提醒，不再建议“打开 gate.analysis_reminder”
    assert habits["analysis_reminder"] is True
    assert "打开 gate.analysis_reminder" not in render(report)


def test_cli_search_is_linked_to_conversation(project, monkeypatch):
    other_id = record_as(project, monkeypatch, "alice", "risk", MEMORY)
    cache = Config.load(project).cache_dir
    log_event(cache, "search_call", conv="c9", module="gameplay.Jigsaw", via="cli")
    monkeypatch.setenv("PMEM_AUTHOR", "me")
    service = MemoryService(project)
    try:
        service.search(module="gameplay.Jigsaw")
    finally:
        service.close()
    log_event(cache, "edit", conv="c9", module="gameplay.Jigsaw", file="src/Jigsaw/A.cs")
    log_event(cache, "stop", conv="c9", status="completed", input_tokens=10, output_tokens=1)
    report = build_report(project, days=7, heat=False)
    assert report["compare"]["hit"]["n"] == 1, other_id


def test_cli_search_logged_after_the_command_is_linked(project, monkeypatch):
    record_as(project, monkeypatch, "alice", "risk", MEMORY)
    cache = Config.load(project).cache_dir
    monkeypatch.setenv("PMEM_AUTHOR", "me")
    service = MemoryService(project)
    try:
        service.search(module="gameplay.Jigsaw")
    finally:
        service.close()
    log_event(cache, "search_call", conv="c9", module="gameplay.Jigsaw", via="cli")
    log_event(cache, "edit", conv="c9", module="gameplay.Jigsaw", file="src/Jigsaw/A.cs")
    log_event(cache, "stop", conv="c9", status="completed", input_tokens=10, output_tokens=1)
    report = build_report(project, days=7, heat=False)
    assert report["compare"]["hit"]["n"] == 1
