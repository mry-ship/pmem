"""自动发现没登记的代码目录：Hook 只做毫秒级的判断并拉起后台进程（pmem sync --auto），扫描和登记在后台完成。

状态存在本机缓存目录（不进版本库）：上次扫描时间、目录指纹、最近一次发现的结果和是否已提醒过。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

STATE_FILE = "autosync.json"
LOCK_FILE = "autosync.lock"
# 后台进程异常退出时锁文件留着；超过这个时长当作已失效
LOCK_STALE_SECONDS = 600
# 一次批量新建文件会连续触发 afterFileEdit，这段时间内只拉起一次
EDIT_SPAWN_GAP_SECONDS = 20
REASONS = ("edit", "session", "full")


def load_state(cache_dir: Path) -> dict:
    try:
        data = json.loads((cache_dir / STATE_FILE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(cache_dir: Path, data: dict) -> None:
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = cache_dir / f"{STATE_FILE}.{os.getpid()}.tmp"
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, cache_dir / STATE_FILE)
    except OSError:
        pass


def lock_busy(cache_dir: Path, now: float | None = None) -> bool:
    try:
        age = (now or time.time()) - (cache_dir / LOCK_FILE).stat().st_mtime
    except OSError:
        return False
    return age < LOCK_STALE_SECONDS


@contextmanager
def scan_lock(cache_dir: Path):
    """同一项目同一时刻只跑一个后台扫描；拿不到锁时 yield False。"""
    path = cache_dir / LOCK_FILE
    cache_dir.mkdir(parents=True, exist_ok=True)
    if path.exists() and not lock_busy(cache_dir):
        path.unlink(missing_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        yield False
        return
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        yield True
    finally:
        path.unlink(missing_ok=True)


def should_spawn(config, reason: str, now: float | None = None, folder: str | None = None) -> bool:
    """改到没登记的目录（edit）随时触发，只防连发，上次扫描后仍没归属的目录（folder）不再触发；
    会话开始（session）按 sync.interval_minutes 节流。"""
    if os.environ.get("PMEM_NO_AUTOSYNC") or config.get("sync.auto") == "off" or not config.modules_path.exists():
        return False
    now = now or time.time()
    cache_dir = config.cache_dir
    if lock_busy(cache_dir, now):
        return False
    state = load_state(cache_dir)
    if reason == "edit":
        if folder is not None and folder in set(state.get("unresolved_dirs") or []):
            return False
        return now - float(state.get("last_spawn") or 0) >= EDIT_SPAWN_GAP_SECONDS
    interval = float(config.get("sync.interval_minutes") or 0) * 60
    last = max(float(state.get("last_run") or 0), float(state.get("last_spawn") or 0))
    return now - last >= interval


def spawn(root: Path, cache_dir: Path, reason: str) -> bool:
    """拉起与当前 Hook 同一个 Python 的后台进程；Hook 进程退出后它继续跑。"""
    state = load_state(cache_dir)
    state["last_spawn"] = time.time()
    save_state(cache_dir, state)
    code = "import sys; from pmem.cli.main import main; sys.exit(main(sys.argv[1:]))"
    cmd = [sys.executable, "-c", code, "sync", "--auto", reason, "--root", str(root)]
    kwargs: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
                    "cwd": str(root), "close_fds": True}
    try:
        if sys.platform == "win32":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            try:
                # Cursor 可能把 Hook 放在作业对象里，Hook 结束时连子进程一起结束；能脱离就脱离
                subprocess.Popen(cmd, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kwargs)
            except OSError:
                subprocess.Popen(cmd, creationflags=flags, **kwargs)
        else:
            subprocess.Popen(cmd, start_new_session=True, **kwargs)
    except OSError:
        return False
    return True


def _paths(body: dict) -> str:
    return "、".join(body.get("paths") or [])


def counts(result: dict) -> dict[str, int]:
    return {
        "new_modules": len(result.get("new_modules") or {}), "new_candidates": len(result.get("new_candidates") or {}),
        "append_paths": len(result.get("append_paths") or {}), "third_party": len(result.get("third_party") or []),
        "promote": len(result.get("promote") or []),
    }


def count_text(result: dict) -> str:
    """“新增 2 个模块、1 个冷候选、1 个模块追加路径”这样的一句；全是 0 时为空串。"""
    n = counts(result)
    parts = [f"新增 {n['new_modules']} 个模块" if n["new_modules"] else "",
             f"{n['new_candidates']} 个冷候选" if n["new_candidates"] else "",
             f"{n['append_paths']} 个模块追加路径" if n["append_paths"] else "",
             f"{n['third_party']} 个第三方目录" if n["third_party"] else "",
             f"{n['promote']} 个冷候选转正" if n["promote"] else ""]
    return "、".join(p for p in parts if p)


def describe(result: dict) -> list[str]:
    """一次扫描结果里要告诉用户的条目。"""
    lines = [f"新模块 {mid}（{_paths(body)}）" for mid, body in (result.get("new_modules") or {}).items()]
    lines += [f"冷候选 {mid}（{_paths(body)}）" for mid, body in (result.get("new_candidates") or {}).items()]
    lines += [f"{mid} 追加路径 {'、'.join(paths)}" for mid, paths in (result.get("append_paths") or {}).items()]
    lines += [f"第三方目录 {p}" for p in result.get("third_party") or []]
    lines += [f"冷候选 {mid} 转正（{why}）" for mid, why in result.get("promote") or []]
    return lines


def take_notice(cache_dir: Path) -> str | None:
    """最近一次后台扫描有新发现、还没告诉过 Agent 时，返回一次提醒文字。"""
    # 后台扫描正在写状态时不读改写，免得把它刚写的结果和历史覆盖掉；扫完后下一次工具调用再提醒
    if lock_busy(cache_dir):
        return None
    state = load_state(cache_dir)
    result = state.get("result")
    if not isinstance(result, dict) or result.get("noticed"):
        return None
    result["noticed"] = True
    save_state(cache_dir, state)
    if result.get("error"):
        return f"[pmem] 后台自动扫描新目录时出错：{result['error']}。请提醒用户运行 pmem sync 查看。"
    items = describe(result)
    if not items:
        return None
    shown = "；".join(items[:8]) + (f" 等 {len(items)} 项" if len(items) > 8 else "")
    total = count_text(result)
    if result.get("applied"):
        return (f"[pmem] 后台扫描发现新的代码目录，已自动登记到 .memory/modules.yaml，共{total}：{shown}。"
                f"请在回复里告诉用户这次{total}（写明数量），名字不合适可用 pmem migrate rename <旧名> <新名> 改，"
                "记得提交 .memory/modules.yaml。")
    why = "modules.yaml 正文里有注释，自动重写会丢失，所以没有自动登记；" if result.get("skipped") == "comments" else ""
    return (f"[pmem] 后台扫描发现没登记的代码目录，待登记 {total.removeprefix('新增 ')}：{shown}。{why}"
            "请在回复里写明数量并提醒用户运行 pmem sync 预览、确认后 pmem sync --apply 登记。")
