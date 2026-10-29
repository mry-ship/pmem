from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path

from pmem.catalog.coverage import coverage_report
from pmem.core.config import Config, ConfigError
from pmem.core.entry import VISIBLE_STATUSES
from pmem.core.quality import similar_entity_pairs
from pmem.core.registry import MAX_MODULE_DEPTH, ModuleRegistry, RegistryError
from pmem.service import COMPACT_MIN_GROUP
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs

OK, WARN, BAD = "✔", "!", "✘"
MAX_LISTED_PAIRS = 10
RECENT_ERROR_SECONDS = 24 * 3600
_STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ")
_CODEX_MCP = re.compile(r'^\s*\[\s*mcp_servers\s*\.\s*"?pmem"?\s*\]', re.MULTILINE)

DOCTOR_STATE_FILE = "last_doctor.json"
DOCTOR_CLAIM_LOCK = "last_doctor.claim"
DOCTOR_INTERVAL_HOURS = 24.0
DOCTOR_CLAIM_TTL_SECONDS = 30 * 60
DOCTOR_SPAWN_EVENTS = frozenset({"session", "prompt", "pre-tool", "post-tool", "edited", "stop"})
# 只有会把返回值交给 Agent 的事件才消费提示；pre-tool / stop 等会把提示吃掉却不展示。
DOCTOR_TIP_EVENTS = frozenset({"session", "post-tool"})


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


def run_doctor(root: Path, *, quiet: bool = False, source: str = "cli") -> int:
    """前台自检打印；quiet 只写本机 last_doctor.json，不改记忆文件。"""
    if quiet:
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                _run_doctor_body(root, warmup_embed=False)
            _save_quiet_state(root, buf.getvalue(), source)
            return 0
        except Exception:
            _mark_quiet_failed(root)
            raise
        finally:
            _clear_doctor_claim(root)
    return _run_doctor_body(root, warmup_embed=True)


def _run_doctor_body(root: Path, *, warmup_embed: bool = True) -> int:
    problems = warnings = 0

    def line(mark: str, text: str) -> None:
        nonlocal problems, warnings
        problems += mark == BAD
        warnings += mark == WARN
        print(f"  {mark} {text}")

    print(f"pmem 自检：{root}")
    try:
        config = Config.load(root)
    except ConfigError as exc:
        line(BAD, f"配置读不出：{exc}")
        print("自检中止：先改好 .memory/config.yaml")
        return 1
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
        print("      还没有划分模块：对 Agent 说“按 pmem-bootstrap 技能划分模块”")
    nested = [mid for mid, m in registry.modules.items() if m.depth > 2 and not m.merged_into]
    if nested:
        print(f"  i 有 {len(nested)} 个子模块（如 {nested[0]}）：团队成员需升级到支持父子模块的 pmem，"
              "旧版能读写已登记的子模块，但没有上级教训继承")
    deep = [mid for mid, m in registry.modules.items() if m.depth > MAX_MODULE_DEPTH]
    if deep:
        line(WARN, f"模块名超过 {MAX_MODULE_DEPTH} 段：{', '.join(deep[:5])}；用 pmem migrate rename 缩短")

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
    hidden = {s for _, e in entries for s in e.replaces()}
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
                   "对 Agent 说“按 pmem-compact 技能合并记忆”")
    by_module: dict[str, list[str]] = {}
    for e in visible:
        by_module.setdefault(e.module, []).append(e.entity)
    pairs = [(m, a, b) for m, names in sorted(by_module.items()) for a, b in similar_entity_pairs(names)]
    if pairs:
        line(WARN, f"{len(pairs)} 组实体名字相近，可能是同一议题起了多个名字（检索按实体加分会失效）：")
        for module, a, b in pairs[:MAX_LISTED_PAIRS]:
            print(f"      {module}：{a} / {b}")

    cursor = root / ".cursor"
    others = {"claude": root / ".claude" / "settings.json", "codex": root / ".codex" / "hooks.json"}
    # 只接了 Claude Code / Codex 的项目不检查 Cursor 配置，免得报一堆用不上的错
    if (cursor / "mcp.json").exists() or (cursor / "hooks.json").exists() or not any(p.exists() for p in others.values()):
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
    for agent, label, wired_mcp, skills in (
        ("claude", "Claude Code", "pmem" in _load(root / ".mcp.json").get("mcpServers", {}), root / ".claude" / "skills"),
        ("codex", "Codex", bool(_CODEX_MCP.search(_read(root / ".codex" / "config.toml"))), root / ".agents" / "skills"),
    ):
        if not others[agent].exists():
            continue
        handlers = _agent_handlers(_load(others[agent]), agent)
        wired_hooks = bool(handlers)
        if not (wired_hooks and wired_mcp):
            missing = "、".join(x for x, ok in (("Hooks", wired_hooks), ("MCP", wired_mcp)) if not ok)
            line(WARN, f"{label} 缺少 {missing}，请运行 pmem init --agents {agent}")
        elif agent == "claude" and not all(
                "PowerShell" in m and h.get("onFailure") == "continue" for m, h in handlers if "pre-tool" in h["command"]):
            line(WARN, f"{label} 的 Hooks 是旧版：Windows 上 PowerShell 改文件不受闸门检查，没装 Git Bash 时 Hook "
                       f"出错会拦下工具；请重新运行 pmem init --agents {agent} 更新")
        elif not (skills / "pmem-bootstrap" / "SKILL.md").exists():
            line(WARN, f"{label} 缺少 pmem 技能（{skills.relative_to(root).as_posix()}），请重新运行 pmem init --agents {agent}")
        else:
            line(OK, f"{label} 已接入（Hooks、MCP 与技能）")
    line(OK if shutil.which("pmem") else BAD, "PATH 中可以找到 pmem 命令" if shutil.which("pmem") else "PATH 中找不到 pmem，Agent 无法启动服务和 Hook")

    if warmup_embed:
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

    print("自检完成" + ("，有需要处理的问题" if problems else f"，有 {warnings} 项提醒" if warnings else "，一切正常"))
    return 1 if problems else 0


def _agent_handlers(data: dict, agent: str) -> list[tuple[str, dict]]:
    """Claude Code / Codex 配置里 pmem 的处理器，连同所在匹配组的 matcher。"""
    found = []
    for groups in (data.get("hooks") or {}).values():
        for group in groups if isinstance(groups, list) else []:
            for handler in group.get("hooks") or [] if isinstance(group, dict) else []:
                command = str(handler.get("command") or "") if isinstance(handler, dict) else ""
                if command.startswith("pmem hook") and f"--agent {agent}" in command:
                    found.append((str(group.get("matcher") or ""), handler))
    return found


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    except json.JSONDecodeError:
        return {}


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


def _clear_doctor_claim(root: Path, cache_dir: Path | None = None) -> None:
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


def _signals_from_output(text: str) -> list[str]:
    signals = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(BAD) or line.startswith(WARN):
            signals.append(line[1:].strip())
    return signals


def _save_quiet_state(root: Path, output: str, source: str) -> None:
    cache_dir = _doctor_cache_dir(root)
    if cache_dir is None:
        return
    signals = _signals_from_output(output)
    needs = bool(signals)
    tip = ""
    if needs:
        tip = "🩺 记忆医生：" + " · ".join(signals[:4]) + "（可 pmem doctor）"
    state = load_doctor_state(cache_dir)
    now = time.time()
    state.update({
        "last_run": now,
        "last_run_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "claimed_at": "",
        "status": "ok",
        "source": source,
        "needs_attention": needs,
        "tip_pending": needs,
        "tip_line": tip,
        "signals": signals[:12],
        "inspect_only": True,
    })
    save_doctor_state(cache_dir, state)


def _mark_quiet_failed(root: Path) -> None:
    cache_dir = _doctor_cache_dir(root)
    if cache_dir is None:
        return
    state = load_doctor_state(cache_dir)
    state["claimed_at"] = ""
    state["status"] = "quiet_failed"
    save_doctor_state(cache_dir, state)


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
        _clear_doctor_claim(root, cache_dir)
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
