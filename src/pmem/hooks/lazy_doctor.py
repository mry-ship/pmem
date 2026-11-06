"""Hook 侧懒医生：到期后台跑 doctor --quiet，只在可展示事件上取一句提示。

放在 hooks 包，避免 gate 反向依赖 cli（分层：hooks 不能 import cli）。
后台进程仍用字符串拉起 pmem.cli.main，不在本模块 import cli。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from pmem.core.config import Config

DOCTOR_STATE_FILE = "last_doctor.json"
DOCTOR_CLAIM_LOCK = "last_doctor.claim"
DOCTOR_INTERVAL_HOURS = 24.0
DOCTOR_CLAIM_TTL_SECONDS = 30 * 60
DOCTOR_SPAWN_EVENTS = frozenset({"session", "prompt", "pre-tool", "post-tool", "edited", "stop"})
# 只有会把返回值交给 Agent 的事件才消费提示；pre-tool / stop 等会把提示吃掉却不展示。
DOCTOR_TIP_EVENTS = frozenset({"session", "post-tool"})


def _doctor_cache_dir(root: Path) -> Path | None:
    try:
        return Config.load(root).cache_dir
    except Exception:  # noqa: BLE001
        return None


def doctor_state_path(cache_dir: Path) -> Path:
    return cache_dir / DOCTOR_STATE_FILE


def doctor_claim_path(cache_dir: Path) -> Path:
    return cache_dir / DOCTOR_CLAIM_LOCK


def load_doctor_state(cache_dir: Path) -> dict:
    path = doctor_state_path(cache_dir)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def save_doctor_state(cache_dir: Path, state: dict) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = cache_dir / f"{DOCTOR_STATE_FILE}.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, cache_dir / DOCTOR_STATE_FILE)


def clear_doctor_claim(root: Path, cache_dir: Path | None = None) -> None:
    cache_dir = cache_dir or _doctor_cache_dir(root)
    if cache_dir is None:
        return
    try:
        doctor_claim_path(cache_dir).unlink(missing_ok=True)
    except OSError:
        pass


def is_doctor_due(cache_dir: Path, *, interval_hours: float = DOCTOR_INTERVAL_HOURS, now: float | None = None) -> bool:
    last = load_doctor_state(cache_dir).get("last_run")
    if last is None:
        return True
    try:
        return (now or time.time()) - float(last) >= interval_hours * 3600
    except (TypeError, ValueError):
        return True


def try_claim_lazy_doctor(
    cache_dir: Path,
    *,
    interval_hours: float = DOCTOR_INTERVAL_HOURS,
    claim_ttl: float = DOCTOR_CLAIM_TTL_SECONDS,
    now: float | None = None,
) -> bool:
    """抢后台巡检槽。成功跑完才写 last_run，崩溃不烧掉整个 24 小时窗口。"""
    now = now or time.time()
    if not is_doctor_due(cache_dir, interval_hours=interval_hours, now=now):
        return False
    lock = doctor_claim_path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    if lock.is_file():
        age = max(0.0, now - lock.stat().st_mtime)
        if age < claim_ttl:
            return False
        lock.unlink(missing_ok=True)
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(int(now)).encode("ascii"))
        finally:
            os.close(fd)
    except OSError:
        return False
    state = load_doctor_state(cache_dir)
    state["claimed_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
    state["status"] = "running"
    save_doctor_state(cache_dir, state)
    return True


def spawn_lazy_doctor(root: Path, cache_dir: Path, *, source: str = "hook") -> bool:
    """后台 `pmem doctor --quiet`。调用方须先 try_claim_lazy_doctor。"""
    code = "import sys; from pmem.cli.main import main; sys.exit(main(sys.argv[1:]))"
    cmd = [sys.executable, "-c", code, "doctor", "--quiet", "--source", source, "--root", str(root)]
    kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "cwd": str(root),
        "close_fds": True,
    }
    try:
        if sys.platform == "win32":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            try:
                subprocess.Popen(cmd, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kwargs)
            except OSError:
                subprocess.Popen(cmd, creationflags=flags, **kwargs)
        else:
            subprocess.Popen(cmd, start_new_session=True, **kwargs)
        return True
    except OSError:
        state = load_doctor_state(cache_dir)
        state["claimed_at"] = ""
        state["status"] = "spawn_failed"
        save_doctor_state(cache_dir, state)
        clear_doctor_claim(root, cache_dir)
        return False


def consume_doctor_tip(cache_dir: Path, *, now: float | None = None) -> str | None:
    """高信号提示每天最多一句，不把完整体检塞进 Hook。"""
    state = load_doctor_state(cache_dir)
    if not state.get("tip_pending") or not state.get("needs_attention"):
        return None
    tip = str(state.get("tip_line") or "").strip()
    if not tip:
        state["tip_pending"] = False
        save_doctor_state(cache_dir, state)
        return None
    day = time.strftime("%Y%m%d", time.localtime(now or time.time()))
    if state.get("tip_consumed_day") == day:
        state["tip_pending"] = False
        save_doctor_state(cache_dir, state)
        return None
    state["tip_pending"] = False
    state["tip_consumed_day"] = day
    save_doctor_state(cache_dir, state)
    return tip


def maybe_lazy_doctor_on_hook(root: Path, event: str, cache_dir: Path | None = None) -> str | None:
    """到期则后台巡检；只在会展示给 Agent 的事件上取出高信号提示。"""
    if os.environ.get("PMEM_NO_LAZY_DOCTOR"):
        return None
    cache_dir = cache_dir or _doctor_cache_dir(root)
    if cache_dir is None:
        return None
    if event in DOCTOR_SPAWN_EVENTS and try_claim_lazy_doctor(cache_dir):
        spawn_lazy_doctor(root, cache_dir, source=f"hook:{event}")
    if event not in DOCTOR_TIP_EVENTS:
        return None
    return consume_doctor_tip(cache_dir)
