"""后台自动同步 modules.yaml：pmem sync --auto 的执行部分（触发与节流见 pmem.core.autosync）。

- 先比目录指纹（含代码文件的目录集合 + modules.yaml 的修改时间），没变就不规划；
- 平时的快速扫描不读提交历史（SVN 要走网络，大项目几十秒）、不统计记忆，只按文件数分新模块和冷候选；
- 距上次完整扫描超过 sync.full_hours 时读一次历史、统计记忆，冷候选按改动和记忆转正；
- sync.auto=apply 时按 pmem sync --apply 的规则只追加；正文里有注释（重写会丢）时退回只提醒。
"""
from __future__ import annotations

import hashlib
import time
from collections import Counter
from pathlib import Path

from pmem.catalog.sync import IDLE_DAYS, SyncPlan, apply_plan, plan_sync
from pmem.catalog.yamlfile import ModulesFile
from pmem.core.autosync import load_state, save_state, scan_lock
from pmem.core.config import Config
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.scan.lite import HEAT_DAYS, file_heat_windows, iter_code_files
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs


def fingerprint(root: Path, modules_path: Path) -> str:
    digest = hashlib.sha1()
    dirs = {rel.rsplit("/", 1)[0] if "/" in rel else "" for rel in iter_code_files(root)}
    for folder in sorted(dirs):
        digest.update(folder.encode("utf-8") + b"\n")
    try:
        stat = modules_path.stat()
        digest.update(f"{stat.st_mtime_ns}:{stat.st_size}".encode("ascii"))
    except OSError:
        pass
    return digest.hexdigest()


def summarize(plan: SyncPlan) -> dict:
    return {
        "new_modules": plan.new_modules, "new_candidates": plan.new_candidates, "append_paths": plan.append_paths,
        "third_party": plan.third_party, "promote": [list(p) for p in plan.promote],
    }


def run_auto(root: Path, reason: str, now: float | None = None) -> dict:
    """返回本次的结果（也写进缓存状态，供 Hook 下次提醒）：status 为 off / busy / unchanged / clean / found。"""
    config = Config.load(root)
    mode = config.get("sync.auto")
    if mode == "off" or not config.modules_path.exists():
        return {"status": "off"}
    cache_dir = config.cache_dir
    with scan_lock(cache_dir) as locked:
        if not locked:
            return {"status": "busy"}
        now = now or time.time()
        state = load_state(cache_dir)
        full = reason == "full" or now - float(state.get("last_full") or 0) >= float(config.get("sync.full_hours")) * 3600
        mark = fingerprint(config.root, config.modules_path)
        state["last_run"] = now
        if not full and mark == state.get("fingerprint"):
            save_state(cache_dir, state)
            return {"status": "unchanged"}
        try:
            result = _plan_and_apply(config, mode, full)
        except (RegistryError, OSError, ValueError) as exc:
            result = {"status": "error", "error": str(exc)[:300]}
        state = load_state(cache_dir)
        state.update(last_run=now, fingerprint=fingerprint(config.root, config.modules_path))
        if full:
            state["last_full"] = now
        if result["status"] in ("found", "error"):
            state["result"] = {**result, "time": now, "reason": reason, "noticed": False}
        save_state(cache_dir, state)
        return result


def _plan_and_apply(config: Config, mode: str, full: bool) -> dict:
    registry = ModuleRegistry.load(config.modules_path)
    heat: Counter = Counter()
    recent: Counter = Counter()
    memories: Counter = Counter()
    history = False
    if full:
        vcs = detect_vcs(config.root, config.get("vcs"))
        name, (heat, recent) = file_heat_windows(config.root, HEAT_DAYS, IDLE_DAYS, vcs=vcs)
        history = name != "none" and bool(heat or recent)
        storage = FilesStorage(config.root, vcs)
        memories = Counter(e.module for _, e in storage.iter_all() if e.status != "archived")
    plan = plan_sync(config.root, registry, memories, heat, recent, history=history)
    if not plan.changes:
        return {"status": "clean", "full": full}
    result = {"status": "found", "full": full, **summarize(plan), "applied": False}
    if mode != "apply":
        return result
    file = ModulesFile.read(config.modules_path)
    if file.lost_comments():
        result["skipped"] = "comments"
        return result
    new_data = apply_plan(file.data, plan)
    ModuleRegistry(new_data)
    file.write(new_data)
    result["applied"] = True
    return result
