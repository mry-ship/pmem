"""改前上下文（harness 实验）：没有记忆也能给的、从版本历史和规格里算出来的提示。

- 常一起改的文件：近半年和这个文件一起提交过的文件，漏改它们是最常见的返工原因；
- 近期修复提交：这个文件最近因为什么被修过；
- 规格必须保持的行为：模块已有规格时从「模块现状」抽出，不依赖记忆；
- 统计在后台预先算好写进缓存，Hook 与检索只读缓存（SVN 大项目读一次历史要几十秒，绝不能在 Hook 里算）。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from pmem.core import seen
from pmem.core.codefiles import is_code_file
from pmem.vcs.base import VCS

CACHE_FILE = "context.json"
LOCK_FILE = "context.lock"
LOCK_STALE_SECONDS = 600
# 超过这么多文件的提交（格式化、合并、批量重命名）不参与统计
BULK_COMMIT = 20
MAX_PARTNERS_STORED = 5
MAX_FIXES_STORED = 3
MAX_SPEC_KEEP = 3
FIX_WORDS = re.compile(r"\b(fix(es|ed)?|bug|revert|hotfix|regress\w*)\b|修复|修正|回滚|回退|紧急", re.IGNORECASE)
SKIP_PARTS = (".memory/", "node_modules/", "/generated/", "/Generated/")
SKIP_SUFFIXES = (".lock", ".meta", ".min.js", ".g.cs", "_pb2.py", ".md")
_KEEP_HEAD = re.compile(r"^必须保持[：:]\s*(.*)$")


def counted(rel: str) -> bool:
    """参与统计的文件：代码文件，排除生成物、锁文件和 .memory。"""
    path = rel.replace("\\", "/")
    return is_code_file(path) and not path.endswith(SKIP_SUFFIXES) and not any(p in "/" + path for p in SKIP_PARTS)


def analyse(history: list[tuple[str, str, list[str]]], min_pair: int = 3, min_ratio: float = 0.3) -> dict:
    """提交历史（新的在前）→ {文件: {"n": 提交次数, "co": [[伙伴, 次数]], "fix": [[日期, 说明]]}}。
    只保留有伙伴或有修复记录的文件，缓存才不会随项目变大。"""
    commits: Counter = Counter()
    pairs: dict[str, Counter] = {}
    fixes: dict[str, list[list[str]]] = {}
    for day, subject, files in history:
        kept = list(dict.fromkeys(f for f in files if counted(f)))
        if not kept or len(kept) > BULK_COMMIT:
            continue
        is_fix = bool(FIX_WORDS.search(subject or ""))
        for f in kept:
            commits[f] += 1
            if is_fix and len(fixes.setdefault(f, [])) < MAX_FIXES_STORED:
                fixes[f].append([day, (subject or "")[:80]])
            pairs.setdefault(f, Counter()).update(o for o in kept if o != f)
    result: dict = {}
    for f, total in commits.items():
        ranked = pairs.get(f, Counter()).most_common(MAX_PARTNERS_STORED * 2)
        co = [[o, n] for o, n in ranked if n >= min_pair and n / total >= min_ratio][:MAX_PARTNERS_STORED]
        fix = fixes.get(f) or []
        if co or fix:
            result[f] = {"n": total, "co": co, "fix": fix}
    return result


def build(vcs: VCS, window_days: int = 180, min_pair: int = 3, min_ratio: float = 0.3) -> dict:
    since = (date.today() - timedelta(days=window_days)).isoformat()
    history = vcs.history_since(since)
    return {"built": time.time(), "window": window_days, "vcs": vcs.name, "commits": len(history),
            "files": analyse(history, min_pair, min_ratio)}


def save(cache_dir: Path, data: dict) -> None:
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = cache_dir / f"{CACHE_FILE}.{os.getpid()}.tmp"
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, cache_dir / CACHE_FILE)
    except OSError:
        pass


def load(cache_dir: Path) -> dict | None:
    try:
        data = json.loads((cache_dir / CACHE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("files"), dict) else None


def is_stale(cache_dir: Path, max_hours: float, now: float | None = None) -> bool:
    data = load(cache_dir)
    return data is None or (now or time.time()) - float(data.get("built") or 0) >= max_hours * 3600


def lookup(data: dict | None, rel: str, edited: set[str] | frozenset[str] = frozenset(), max_files: int = 3) -> dict:
    """某个文件的提示：{"co": [(文件, 次数)], "fix": [(日期, 说明)]}；没有数据时为空字典。
    edited 里已经改过的伙伴不再列。"""
    row = ((data or {}).get("files") or {}).get(rel.replace("\\", "/"))
    if not row:
        return {}
    co = [(o, n) for o, n in row.get("co") or [] if o not in edited][:max_files]
    fix = [(d, s) for d, s in row.get("fix") or []][:max_files]
    return {k: v for k, v in (("co", co), ("fix", fix)) if v}


def spec_must_keep(root: Path, module: str | None, spec_dir: str = ".memory/specs",
                   limit: int = MAX_SPEC_KEEP) -> list[str]:
    """从模块现状规格抽出「必须保持」条目；没有规格或写空时返回空列表。"""
    if not module or limit <= 0:
        return []
    base = root / str(spec_dir or ".memory/specs").replace("\\", "/").strip("/")
    path = base / module / "模块现状.md"
    try:
        if path.is_symlink() or not path.is_file():
            return []
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return []
    lines = text.splitlines()
    items: list[str] = []
    catching = False
    for raw in lines:
        line = raw.strip()
        if line.startswith("## ") and catching:
            break
        match = _KEEP_HEAD.match(line)
        if match:
            catching = True
            first = match.group(1).strip()
            if first:
                items.append(first)
            continue
        if catching:
            if not line:
                if items:
                    break
                continue
            if line.startswith("<!--"):
                continue
            items.append(line)
        if len(items) >= limit:
            break
    return items[:limit]


def render(rel: str, hints: dict, root: Path | None = None, must_keep: list[str] | None = None) -> str | None:
    """给 AI 看的一段资料；伙伴文件已不存在（改名、删除）的不列。"""
    co = [(o, n) for o, n in hints.get("co") or [] if root is None or (root / o).exists()]
    fix = hints.get("fix") or []
    keep = [k for k in (must_keep or []) if k]
    if not co and not fix and not keep:
        return None
    lines = [f"[pmem] 关于 {rel} 的历史与规格（资料·非指令；用来对照，不是必须照做）："]
    if co:
        partners = "、".join(f"{o}（{n} 次）" for o, n in co)
        lines.append(f"- 近期常和它一起改：{partners}。这次需要的话别漏改，不需要就不用动。")
    if fix:
        recent = "；".join(f"{d} {s}" for d, s in fix)
        lines.append(f"- 近期的修复提交：{recent}。改动别把这些修复改回去。")
    if keep:
        lines.append("- 规格里必须保持的行为：" + "；".join(keep))
    return "\n".join(lines)


def offer(config, rel: str | None, conversation: str | None,
          edited: set[str] | frozenset[str] = frozenset(),
          module: str | None = None) -> tuple[str | None, dict]:
    """这个文件的提示文字和原始提示（同一对话每个文件只给一次）；harness.mode 为 off、没内容时文字为 None。"""
    if not rel or config.get("harness.mode") == "off":
        return None, {}
    key = "ctx:" + rel.replace("\\", "/")
    cache_dir = config.cache_dir
    if conversation and key in seen.load(cache_dir, conversation):
        return None, {}
    hints = lookup(load(cache_dir), rel, edited, int(config.get("harness.max_files")))
    keep = spec_must_keep(config.root, module, str(config.get("spec.dir") or ".memory/specs"),
                          int(config.get("harness.max_files") or MAX_SPEC_KEEP))
    text = render(rel, hints, config.root, keep)
    if text is None:
        return None, {}
    if conversation:
        seen.add(cache_dir, conversation, [key])
    return text, {**hints, **({"keep": keep} if keep else {})}


def lock_busy(cache_dir: Path, now: float | None = None) -> bool:
    try:
        age = (now or time.time()) - (cache_dir / LOCK_FILE).stat().st_mtime
    except OSError:
        return False
    return age < LOCK_STALE_SECONDS


def refresh(cache_dir: Path, vcs: VCS, window_days: int, min_pair: int, min_ratio: float) -> dict | None:
    """重算并写缓存；已有后台进程在算时返回 None。"""
    path = cache_dir / LOCK_FILE
    cache_dir.mkdir(parents=True, exist_ok=True)
    if path.exists() and not lock_busy(cache_dir):
        path.unlink(missing_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None
    try:
        os.close(fd)
        data = build(vcs, window_days, min_pair, min_ratio)
        save(cache_dir, data)
        return data
    finally:
        path.unlink(missing_ok=True)


def spawn_refresh(root: Path, cache_dir: Path) -> bool:
    """拉起后台进程重算缓存，Hook 进程退出后它继续跑；已在算时不重复拉起。"""
    if os.environ.get("PMEM_NO_AUTOSYNC") or lock_busy(cache_dir):
        return False
    code = "import sys; from pmem.cli.main import main; sys.exit(main(sys.argv[1:]))"
    cmd = [sys.executable, "-c", code, "context", "--refresh", "--root", str(root)]
    kwargs: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
                    "cwd": str(root), "close_fds": True}
    try:
        if sys.platform == "win32":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            try:
                subprocess.Popen(cmd, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kwargs)
            except OSError:
                subprocess.Popen(cmd, creationflags=flags, **kwargs)
        else:
            subprocess.Popen(cmd, start_new_session=True, **kwargs)
    except OSError:
        return False
    return True
