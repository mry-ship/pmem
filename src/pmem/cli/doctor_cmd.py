from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

from pmem.core.config import Config
from pmem.core.quality import similar_entity_pairs
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.index.store import VISIBLE_STATUSES
from pmem.scan.lite import iter_code_files
from pmem.service import COMPACT_MIN_GROUP
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs

OK, WARN, BAD = "✔", "!", "✘"
MAX_LISTED_PAIRS = 10
RECENT_ERROR_SECONDS = 24 * 3600
_STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ")


def _recent_errors(path: Path, now: float | None = None) -> list[str]:
    """hook-errors.log 里近 24 小时的错误，每条是“时间 + 堆栈”一整段。旧错误修好后不再反复显示。"""
    cutoff = (now or time.time()) - RECENT_ERROR_SECONDS
    records: list[list[str]] = []
    for text in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if _STAMP.match(text) or not records:
            records.append([text])
        else:
            records[-1].append(text)
    recent = []
    for record in records:
        match = _STAMP.match(record[0])
        if match and time.mktime(time.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")) >= cutoff:
            recent.append("\n".join(record))
    return recent


def coverage_report(root: Path, registry: ModuleRegistry) -> dict:
    files = list(iter_code_files(root))
    mapped = excluded = 0
    unmapped: Counter = Counter()
    conflicts: set[str] = set()
    used: Counter = Counter()
    for rel in files:
        if registry.is_excluded(rel):
            excluded += 1
            continue
        try:
            match = registry.module_for_path(rel)
        except RegistryError as exc:
            conflicts.add(str(exc).split("，")[0])
            continue
        if match is None:
            unmapped["/".join(rel.split("/")[:3]) if "/" in rel else "（根目录）"] += 1
        else:
            mapped += 1
            used[match.module_id] += 1
    shells = [
        mid for mid, m in {**registry.modules, **registry.candidates}.items()
        if m.paths and not m.merged_into and used[mid] == 0
    ]
    total = len(files) - excluded
    return {
        "files": len(files),
        "excluded": excluded,
        "mapped": mapped,
        "coverage": mapped / total if total else 1.0,
        "unmapped": unmapped.most_common(10),
        "conflicts": sorted(conflicts)[:10],
        "shells": shells,
    }


def run_doctor(root: Path) -> int:
    problems = 0

    def line(mark: str, text: str) -> None:
        nonlocal problems
        problems += mark == BAD
        print(f"  {mark} {text}")

    print(f"pmem 自检：{root}")
    config = Config.load(root)
    vcs = detect_vcs(root, config.get("vcs"))
    line(OK, f"配置可读；版本控制 {vcs.name}；作者 {vcs.current_user()}；闸门 {config.get('gate.mode')}")

    try:
        registry = ModuleRegistry.load(config.modules_path) if config.modules_path.exists() else ModuleRegistry({})
    except RegistryError as exc:
        line(BAD, str(exc))
        return 1
    n_modules = len(registry.modules)
    line(OK if n_modules else WARN, f"模块 {n_modules} 个、候选 {len(registry.candidates)} 个、大类 {' / '.join(registry.categories)}")
    if n_modules == 0:
        print("      还没有划分模块：在 Cursor 里对 Agent 说“按 pmem-bootstrap 技能划分模块”")

    cov = coverage_report(root, registry)
    pct = cov["coverage"] * 100
    line(OK if pct >= 95 else WARN, f"模块覆盖率 {pct:.1f}%（代码文件 {cov['files']}，第三方/忽略 {cov['excluded']}）")
    for folder, count in cov["unmapped"]:
        print(f"      未覆盖：{folder}（{count} 个文件）")
    for conflict in cov["conflicts"]:
        line(BAD, f"路径重叠：{conflict}")
    if cov["shells"]:
        line(WARN, f"空壳模块（路径匹配不到任何代码文件）：{', '.join(cov['shells'][:10])}")

    storage = FilesStorage(root, vcs)
    entries = list(storage.iter_all())
    hidden = {s for _, e in entries if e.status in VISIBLE_STATUSES for s in e.supersedes}
    visible = [e for _, e in entries if e.status in VISIBLE_STATUSES and e.id not in hidden]
    line(OK if not storage.warnings else WARN,
         f"现行记忆 {len(visible)} 条（记忆文件共 {len(entries)} 个，其余已被替代或停用）")
    for warning in storage.warnings[:5]:
        print(f"      {warning}")
    pending = vcs.uncommitted_count(config.entries_dir)
    if pending:
        line(WARN, f"本机有 {pending} 条记忆未提交，队友看不到；请连同 .memory/ 一起提交")
    big = [n for n in Counter((e.module, e.entity.lower()) for e in visible).values() if n >= COMPACT_MIN_GROUP]
    if big:
        line(WARN, f"{len(big)} 个议题各积累了 {COMPACT_MIN_GROUP} 条以上记忆（共 {sum(big)} 条），检索时会互相挤占；"
                   "在 Cursor 里对 Agent 说“按 pmem-compact 技能合并记忆”")
    by_module: dict[str, list[str]] = {}
    for e in visible:
        by_module.setdefault(e.module, []).append(e.entity)
    pairs = [(m, a, b) for m, names in sorted(by_module.items()) for a, b in similar_entity_pairs(names)]
    if pairs:
        line(WARN, f"{len(pairs)} 组实体名字相近，可能是同一议题起了多个名字（检索按实体加分会失效）：")
        for module, a, b in pairs[:MAX_LISTED_PAIRS]:
            print(f"      {module}：{a} / {b}")

    cursor = root / ".cursor"
    mcp = _load(cursor / "mcp.json").get("mcpServers", {})
    line(OK if "pmem" in mcp else BAD, ".cursor/mcp.json 已注册 pmem" if "pmem" in mcp else ".cursor/mcp.json 缺少 pmem，请运行 pmem init")
    hooks = json.dumps(_load(cursor / "hooks.json"))
    line(OK if "pmem hook" in hooks else WARN, "Hooks 已接入" if "pmem hook" in hooks else "Hooks 未接入（闸门不生效），请运行 pmem init")
    post = [h for h in _load(cursor / "hooks.json").get("hooks", {}).get("postToolUse", [])
            if str(h.get("command", "")).startswith("pmem hook post-tool")]
    if "pmem hook" in hooks and not post:
        line(WARN, "读代码时的记忆摘要未接入（postToolUse），请重新运行 pmem init")
    elif post and "Grep" not in str(post[0].get("matcher", "Grep")):
        line(WARN, "Hooks 是旧版：搜索代码（Grep / Glob）时不附记忆摘要，请重新运行 pmem init 更新")
    elif post and "Shell" not in str(post[0].get("matcher", "Shell")):
        line(WARN, "Hooks 是旧版：终端命令改了文件时不做事后核对，请重新运行 pmem init 更新")
    elif "pmem hook" in hooks and not (root / ".memory" / "bin" / "pmem-hook.cmd").exists():
        line(WARN, "Hooks 是旧版：队友没装 pmem 时不会提醒（缺 .memory/bin/pmem-hook），请重新运行 pmem init 更新")
    line(OK if (cursor / "rules" / "pmem.mdc").exists() else WARN, "规则文件 .cursor/rules/pmem.mdc")
    for agent, label, hooks_path, wired_mcp in (
        ("claude", "Claude Code", root / ".claude" / "settings.json", "pmem" in _load(root / ".mcp.json").get("mcpServers", {})),
        ("codex", "Codex", root / ".codex" / "hooks.json", "mcp_servers.pmem" in _read(root / ".codex" / "config.toml")),
    ):
        if not hooks_path.exists():
            continue
        wired_hooks = f"--agent {agent}" in json.dumps(_load(hooks_path))
        if wired_hooks and wired_mcp:
            line(OK, f"{label} 已接入（Hooks 与 MCP）")
        else:
            missing = "、".join(x for x, ok in (("Hooks", wired_hooks), ("MCP", wired_mcp)) if not ok)
            line(WARN, f"{label} 缺少 {missing}，请运行 pmem init --agents {agent}")
    line(OK if shutil.which("pmem") else BAD, "PATH 中可以找到 pmem 命令" if shutil.which("pmem") else "PATH 中找不到 pmem，Cursor 无法启动服务")

    backend = config.get("embedding.backend")
    has_fastembed = importlib.util.find_spec("fastembed") is not None
    if backend == "none" or (backend == "auto" and not has_fastembed):
        line(OK, "检索：关键词（安装 pmem[embed] 可启用语义检索）")
    else:
        from pmem.core.config import user_cache_base
        from pmem.index.embedder import make_embedder

        print("  … 准备语义模型（首次会下载约 90 MB）", flush=True)
        embedder, problem = make_embedder(config.get("embedding") or {}, user_cache_base() / "models")
        try:
            if embedder is None:
                raise RuntimeError(problem)
            embedder.embed(["预热"])
            line(OK, f"检索：关键词 + 语义（{embedder.id}）")
        except Exception as exc:  # noqa: BLE001
            line(WARN, f"语义模型不可用，将只用关键词检索：{exc}")

    errors = config.cache_dir / "hook-errors.log"
    recent_errors = _recent_errors(errors) if errors.exists() else []
    if recent_errors:
        line(WARN, f"近 24 小时 Hook 出错 {len(recent_errors)} 次（{errors}），最近一次：")
        for text in recent_errors[-1].splitlines()[-3:]:
            print(f"      {text}")
    log = config.cache_dir / "hooks.log"
    if log.exists():
        recent = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-1:]
        line(OK, f"Hook 最近一次介入：{recent[0][:120] if recent else '无'}")

    if sys.platform == "win32":
        try:
            import ctypes

            if ctypes.windll.kernel32.GetACP() != 65001:
                print("  i Windows 非 UTF-8 代码页：Cursor 传给 Hook 的中文会被转码，pmem 已自动兼容")
        except Exception:  # noqa: BLE001, S110
            pass

    print("自检完成" + ("，有需要处理的问题" if problems else "，一切正常"))
    return 1 if problems else 0


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    except json.JSONDecodeError:
        return {}
