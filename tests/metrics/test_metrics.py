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
    assert report["records"]["by_kind"] == {"exclusion": 1, "conclusion": 1}
    assert report["habits"]["gates"] == 1 and report["habits"]["gate_converted"] == 1
    assert report["habits"]["nudges"] == 1 and report["habits"]["nudge_converted"] == 0
    assert report["compare"]["hit"]["n"] == 1 and report["compare"]["enough"] is False
    assert report["assets"]["memories"] == 2 and report["assets"]["modules_registered"] == 2
    text = render(report)
    assert "跨人复用" in text and "样本不足" in text
