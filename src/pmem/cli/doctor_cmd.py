from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import shutil
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
from pmem.generate.templates import HOOK_WRAPPER
from pmem.hooks.lazy_doctor import (
    DOCTOR_CLAIM_TTL_SECONDS,
    DOCTOR_INTERVAL_HOURS,
    DOCTOR_SPAWN_EVENTS,
    DOCTOR_STATE_FILE,
    DOCTOR_TIP_EVENTS,
    clear_doctor_claim,
    consume_doctor_tip,
    doctor_claim_path,
    doctor_state_path,
    is_doctor_due,
    load_doctor_state,
    maybe_lazy_doctor_on_hook,
    save_doctor_state,
    spawn_lazy_doctor,
    try_claim_lazy_doctor,
)
from pmem.service import COMPACT_MIN_GROUP
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs

OK, WARN, BAD = "✔", "!", "✘"

# 兼容旧 import：tests / 外部仍可从 doctor_cmd 取懒医生 API
__all__ = [
    "DOCTOR_CLAIM_TTL_SECONDS",
    "DOCTOR_INTERVAL_HOURS",
    "DOCTOR_SPAWN_EVENTS",
    "DOCTOR_STATE_FILE",
    "DOCTOR_TIP_EVENTS",
    "consume_doctor_tip",
    "doctor_claim_path",
    "doctor_state_path",
    "is_doctor_due",
    "load_doctor_state",
    "maybe_lazy_doctor_on_hook",
    "run_doctor",
    "save_doctor_state",
    "spawn_lazy_doctor",
    "try_claim_lazy_doctor",
]


def _is_hook_command(command, event: str) -> bool:
    text = str(command or "")
    return text.startswith((f"pmemw hook {event}", f"pmem hook {event}"))


def _iter_hook_commands(hooks_data: dict) -> list[str]:
    """Cursor 扁平 hooks 与 Claude/Codex 三层 hooks 里的 command 字符串。"""
    out: list[str] = []
    table = hooks_data.get("hooks") if isinstance(hooks_data, dict) else None
    if not isinstance(table, dict):
        return out
    for entries in table.values():
        if not isinstance(entries, list):
            continue
        for item in entries:
            if not isinstance(item, dict):
                continue
            cmd = item.get("command")
            if isinstance(cmd, str) and cmd.strip():
                out.append(cmd)
            nested = item.get("hooks")
            if isinstance(nested, list):
                for handler in nested:
                    if isinstance(handler, dict) and isinstance(handler.get("command"), str):
                        text = handler["command"].strip()
                        if text:
                            out.append(text)
    return out


def _is_console_python_hook(command: str) -> bool:
    """Windows 上用控制台 Python 起 Hook 会弹黑框；pyw/pythonw 除外。macOS 的 python3 没问题。"""
    cmd = str(command or "").strip()
    if not cmd:
        return False
    if re.match(r"^(pyw|pythonw)(\.exe)?\b", cmd, re.IGNORECASE):
        return False
    return bool(re.match(r"^(python3?|py)(\.exe)?\b", cmd, re.IGNORECASE))


MAX_LISTED_PAIRS = 10
RECENT_ERROR_SECONDS = 24 * 3600
_STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ")
_CODEX_MCP = re.compile(r'^\s*\[\s*mcp_servers\s*\.\s*"?pmem"?\s*\]', re.MULTILINE)


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
            clear_doctor_claim(root)
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
        hooks_data = _load(cursor / "hooks.json")
        hooks = json.dumps(hooks_data)
        wired_hooks = "pmemw hook" in hooks or "pmem hook" in hooks or HOOK_WRAPPER in hooks
        line(OK if wired_hooks else WARN, "Hooks 已接入" if wired_hooks else "Hooks 未接入（闸门不生效），请运行 pmem init")
        post = [h for h in hooks_data.get("hooks", {}).get("postToolUse", [])
                if isinstance(h, dict) and _is_hook_command(h.get("command"), "post-tool")]
        pre = [h for h in hooks_data.get("hooks", {}).get("preToolUse", [])
               if isinstance(h, dict) and _is_hook_command(h.get("command"), "pre-tool")]
        after_mcp = [h for h in hooks_data.get("hooks", {}).get("afterMCPExecution", [])
                     if isinstance(h, dict) and _is_hook_command(h.get("command"), "after-mcp")]
        post_matcher = str(post[0].get("matcher", "")) if post else ""
        pre_matcher = " ".join(str(h.get("matcher", "")) for h in pre)
        read_heavy = bool(re.search(r"Read|Grep|Glob|SemanticSearch|codebase_search", post_matcher))
        gate_tools = bool(re.search(r"Write|Edit|StrReplace|Shell", pre_matcher))
        shell_only_post = bool(post) and "Shell" in post_matcher and not read_heavy
        # 默认 full：闸门+读码摘要；quiet 仅 Shell post。禁止把 Write/Edit 拆掉。
        if wired_hooks and pre and not gate_tools:
            line(WARN, "preToolUse 未匹配 Write/Edit/Shell：改代码闸门失效；请 pmem init --hooks full")
        elif wired_hooks and not post:
            line(WARN, "postToolUse 未接入：终端 pmem search 无法登记「已查过」；请 pmem init --hooks full")
        elif post and "Grep" not in post_matcher and not shell_only_post:
            line(WARN, "Hooks 是旧版：搜索代码（Grep / Glob）时不附记忆摘要，请重新运行 pmem init 更新")
        elif post and "Shell" not in post_matcher:
            line(WARN, "Hooks 是旧版：终端命令改了文件时不做事后核对，请重新运行 pmem init 更新")
        elif wired_hooks and pre and after_mcp and read_heavy and "Write" in pre_matcher:
            line(OK, "Hooks=full（闸门+读码摘要+提醒）")
        elif wired_hooks and pre and after_mcp and shell_only_post:
            line(OK, "Hooks=quiet（闸门+提醒；postToolUse 仅 Shell；要完整摘要用 pmem init --hooks full）")
        elif "pmem-hook session" in hooks:
            line(WARN, "Hooks 是旧版：sessionStart 仍走 .cmd/.sh 包装，Windows 上易弹黑框；请重新运行 pmem init 更新")
        elif sys.platform == "win32" and "pmem hook" in hooks and "pmemw hook" not in hooks:
            line(WARN, "Windows 上 Hook 仍用控制台版 pmem，会弹黑框；请升级 pmem 后重新运行 pmem init")
        if any("||" in str(h.get("command") or "") for entries in hooks_data.get("hooks", {}).values()
               for h in entries if isinstance(h, dict)):
            line(WARN, "hooks.json 命令含 ||，Cursor 会经 cmd/PowerShell 启动，Windows 必弹控制台；请改成单个可执行文件")
        if sys.platform == "win32" and any(_is_console_python_hook(c) for c in _iter_hook_commands(hooks_data)):
            line(WARN, "hooks.json 在 Windows 上用控制台版 python3/python/py 起 Hook，会弹黑框；"
                 "请改成 pyw -3 -u（macOS/Linux 仍用 python3）")
        mcp_cmd = str((mcp.get("pmem") or {}).get("command") or "")
        if mcp_cmd in ("pmemw", "pmemw.exe"):
            line(WARN, "MCP 用了 pmemw：Windows 上容易掐断 stdio（Connection closed）；请重新运行 pmem init 改回 pmem")
        user_mcp = Path.home() / ".cursor" / "mcp.json"
        if user_mcp.is_file() and "pmem" in json.dumps(_load(user_mcp).get("mcpServers", {})):
            line(WARN, "用户级 ~/.cursor/mcp.json 也注册了 pmem，可能盖住项目配置；多项目时请清空用户级 pmem，只用各项目 .cursor/mcp.json")
        if "pmem" in mcp:
            from pmem.generate.mcp_enable import cursor_server_config_hash, cursor_state_db

            db = cursor_state_db()
            approved_ok = False
            if db is not None:
                try:
                    import sqlite3

                    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
                    row = con.execute(
                        "SELECT value FROM ItemTable WHERE key=?",
                        ("cursor/approvedProjectMcpServers",),
                    ).fetchone()
                    con.close()
                    approved = json.loads(row[0]) if row and row[0] else []
                    suffix = f"-{root.name}-pmem:{cursor_server_config_hash(mcp.get('pmem') or {})}"
                    approved_ok = any(str(x).endswith(suffix) for x in approved)
                except Exception:
                    approved_ok = False
            if approved_ok:
                line(OK, "Cursor 已项目级批准 pmem MCP")
            else:
                from pmem.generate.mcp_enable import cursor_running

                tip = ("（Cursor 正在运行，自动批准会被它覆盖；请完全退出 Cursor 后重跑 pmem init，"
                       "或 设置 → MCP 手动启用后 Reload Window）" if cursor_running()
                       else "（设置 → MCP 启用，或再跑 pmem init）")
                line(WARN, "Cursor 尚未项目级批准 pmem MCP" + tip)
        line(OK if (cursor / "rules" / "pmem.mdc").exists() else WARN, "规则文件 .cursor/rules/pmem.mdc")
    for agent, label, wired_mcp, skills in (
        ("claude", "Claude Code", "pmem" in _load(root / ".mcp.json").get("mcpServers", {}), root / ".claude" / "skills"),
        ("codex", "Codex", bool(_CODEX_MCP.search(_read(root / ".codex" / "config.toml"))), root / ".agents" / "skills"),
    ):
        if not others[agent].exists():
            continue
        handlers = _agent_handlers(_load(others[agent]), agent)
        wired_hooks = bool(handlers)
        cursor_pmem = "pmem" in json.dumps(_load(cursor / "hooks.json")) if (cursor / "hooks.json").exists() else False
        if (agent == "claude" and sys.platform == "win32" and wired_mcp and not wired_hooks
                and cursor_pmem):
            line(OK, f"{label} MCP 已接入；Windows 与 Cursor 同开时故意不装 Claude Hooks（防双开弹窗）")
        elif not (wired_hooks and wired_mcp):
            missing = "、".join(x for x, ok in (("Hooks", wired_hooks), ("MCP", wired_mcp)) if not ok)
            line(WARN, f"{label} 缺少 {missing}，请运行 pmem init --agents {agent}")
        elif agent == "claude" and not all(
                "PowerShell" in m and h.get("onFailure") == "continue" for m, h in handlers if "pre-tool" in h["command"]):
            line(WARN, f"{label} 的 Hooks 是旧版：Windows 上 PowerShell 改文件不受闸门检查，没装 Git Bash 时 Hook "
                       f"出错会拦下工具；请重新运行 pmem init --agents {agent} 更新")
        elif sys.platform == "win32" and any(h["command"].startswith("pmem hook") for _, h in handlers):
            line(WARN, f"{label} 的 Hooks 仍用控制台版 pmem，Windows 会弹黑框；请升级 pmem 后重新运行 pmem init --agents {agent}")
        elif sys.platform == "win32" and any(_is_console_python_hook(h["command"]) for _, h in handlers):
            line(WARN, f"{label} 的 Hooks 在 Windows 上用控制台版 python3/python/py，会弹黑框；"
                 f"请改成 pyw -3 -u（macOS/Linux 仍用 python3）")
        elif agent == "claude" and sys.platform == "win32" and wired_hooks and cursor_pmem:
            line(WARN, f"{label} 在 Windows 上仍装了 Hooks：Cursor 会双开翻倍弹窗；请 pmem init（会清空 Claude 侧 pmem Hook）")
        elif not (skills / "pmem-bootstrap" / "SKILL.md").exists():
            line(WARN, f"{label} 缺少 pmem 技能（{skills.relative_to(root).as_posix()}），请重新运行 pmem init --agents {agent}")
        else:
            line(OK, f"{label} 已接入（Hooks、MCP 与技能）")

    has_pmem = shutil.which("pmem") is not None
    has_pmemw = shutil.which("pmemw") is not None
    line(OK if has_pmem else BAD, "PATH 中可以找到 pmem 命令" if has_pmem else "PATH 中找不到 pmem，Agent 无法启动服务和 Hook")
    if has_pmem and not has_pmemw:
        line(WARN, "PATH 中有 pmem 但没有 pmemw（Hook 无控制台入口），请重新安装当前版 pmem")

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
        print("  i 防弹窗：Hook 用 pmemw（勿用 pmem/.cmd/||）；与 Cursor 同开时不要装 Claude Hooks；"
              "勿用控制台版 python/py 起 Hook。Hook 内 git/svn 已 CREATE_NO_WINDOW；"
              "若仍弹，多半是 Cursor 外层用未藏窗的 pwsh/cmd 拉 Hook，"
              "可试 terminal.integrated.windowsUseConptyDll=true 后重启。"
              "不要靠拆掉闸门或读码摘要来消黑框。")


    print("自检完成" + ("，有需要处理的问题" if problems else f"，有 {warnings} 项提醒" if warnings else "，一切正常"))
    return 1 if problems else 0


def _agent_handlers(data: dict, agent: str) -> list[tuple[str, dict]]:
    """Claude Code / Codex 配置里 pmem 的处理器，连同所在匹配组的 matcher。"""
    found = []
    for groups in (data.get("hooks") or {}).values():
        for group in groups if isinstance(groups, list) else []:
            for handler in group.get("hooks") or [] if isinstance(group, dict) else []:
                command = str(handler.get("command") or "") if isinstance(handler, dict) else ""
                if command.startswith(("pmem hook", "pmemw hook")) and f"--agent {agent}" in command:
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


def _signals_from_output(text: str) -> list[str]:
    signals = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith((BAD, WARN)):
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
