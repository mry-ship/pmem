from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import time
from pathlib import Path

from wcmatch import glob as wglob

from pmem.core.config import Config
from pmem.core.entry import KIND_LABELS, Entry
from pmem.core.ids import ULID_PATTERN
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.hooks.payload import (
    asks_to_skip,
    fuzzy_contains,
    last_user_text,
    readable,
    tool_input,
    tool_paths,
    turn_tool_paths,
)
from pmem.hooks.shell import (  # noqa: F401
    VARIABLE_PATH,
    WILDCARD_PATH,
    cli_args,
    may_change_unseen,
    scan,
    shell_write_targets,
)
from pmem.hooks.state import SessionState
from pmem.index.anchors import ANCHOR_CACHE, STALE_LABEL, AnchorChecker
from pmem.index.graph import current_entries, digest, preview
from pmem.metrics.events import log_event

WRITE_TOOLS = {"write", "strreplace", "edit", "multiedit", "editnotebook", "delete", "search_replace"}
_GLOB = wglob.GLOBSTAR | wglob.BRACE | wglob.DOTGLOB | wglob.FORCEUNIX | wglob.IGNORECASE
VIEW_TOOLS = {"read", "grep", "glob", "semanticsearch", "codebase_search"}
SEARCH_TOOLS = VIEW_TOOLS - {"read"}
MAX_SEARCH_DIGESTS = 2
_ULID = ULID_PATTERN
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")
ALLOW = {"permission": "allow"}
PMEM_TOOLS = ("record_memory", "search_memory", "memory_graph")
MAX_AUTO_ANCHORS = 5
MAX_REVIEW_MODULES = 3
DIGEST_PREVIEW = 100
PITFALL_KINDS = ("exclusion", "risk", "correction")
MAX_GUARD_PITFALLS = 5
MAX_PENDING_SNAPSHOTS = 8
MAX_GLOB_TARGETS = 200
SLOW_SNAPSHOT_SECONDS = 1.0
SLOW_SNAPSHOT_PAUSE = 24 * 3600
SLOW_SNAPSHOT_MARK = "snapshot-slow"
ERROR_LOG = "hook-errors.log"
ERROR_SEEN = "hook-errors.seen"
ERROR_NOTICE_WINDOW = 24 * 3600
# Cursor 把结束提醒显示成一条用户消息，用户容易误以为要自己动手；以 [pmem] 开头，下一轮靠它认出不是用户提问
FOLLOWUP_HEADER = "[pmem] 以下是 pmem 自动发给 AI 的提醒，由 AI 处理，你无需操作。"
_PATH_TOKEN = re.compile(r"[\w.\-]*[/\\][\w./\\\-]+")
STALE_FOOTER = (f"标“{STALE_LABEL}”的记忆写下后关联代码又改过，依赖前先对照代码："
                "仍成立就 confirm_memory，不成立就写 correction 替代。")
_STALE_SLOT = "\x00stale:{}\x00"
_STALE_SLOT_RE = re.compile(r"\x00stale:(\w+)\x00")
_FOOTER_SLOT = "\x00footer:{}\x00"
_FOOTER_SLOT_RE = re.compile(r"\n?\x00footer:([\w,]*)\x00")


def _stale_mark(problems: list[str]) -> str:
    return f"（⚠ {STALE_LABEL}：{'；'.join(problems)}）" if problems else ""


def tool_response(payload: dict) -> dict | None:
    """pmem 工具的返回 JSON。各家包装不同（Cursor 的 result_json 是多层转义的字符串，
    Claude / Codex 的 tool_response 是内容块列表），逐层解开找带 ok 的对象；tool_input 不看。"""

    def walk(value, level: int):
        if level > 8:
            return None
        if isinstance(value, str):
            text = value.strip().lstrip("\ufeff")
            if text[:1] not in ("{", "["):
                return None
            try:
                return walk(json.loads(text), level + 1)
            except ValueError:
                return None
        if isinstance(value, dict):
            if "ok" in value:
                return value
            children = list(value.values())
        elif isinstance(value, list):
            children = value
        else:
            return None
        for child in children:
            found = walk(child, level + 1)
            if found is not None:
                return found
        return None

    return walk({k: v for k, v in payload.items() if k != "tool_input"}, 0)


_OUTPUT_FIELDS = ("tool_output", "tool_response", "output")


def shell_output(payload: dict) -> str | None:
    """终端命令执行后的输出文本（Cursor 的 tool_output、Claude Code / Codex 的 tool_response）；载荷里没有时返回 None。"""
    for key in _OUTPUT_FIELDS:
        value = payload.get(key)
        if value is None:
            continue
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return None


_SERVER_FIELDS = ("server", "server_name", "mcp_server", "url", "command")


def foreign_tool(payload: dict) -> bool:
    """同名的 search_memory 等工具来自别家记忆服务。工具名或载荷里带了服务信息且不是 pmem 时为 True；
    都没带时无法区分，按 pmem 处理。"""
    name = str(payload.get("tool_name") or "").lower()
    if name.startswith("mcp__"):
        return "pmem" not in name
    for key in _SERVER_FIELDS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return "pmem" not in value.lower()
    return False


def _command_key(command: str) -> str:
    return "cmd:" + hashlib.sha1(command.encode("utf-8", "replace")).hexdigest()[:16]


def _needs_snapshot(command: str, base: str) -> bool:
    """脚本、内联代码、变量拼出来的路径和不认识的程序（格式化、git stash 等）事前看不出写了什么，
    放行时记下快照，执行后比对未提交文件，见 Gate._shell_after。"""
    targets, runs_code = scan(command, base)
    return (runs_code or any(VARIABLE_PATH.search(t) or WILDCARD_PATH.search(t) for t in targets)
            or may_change_unseen(command))


def _around(text: str, marker: str, width: int = 12) -> str:
    """提问里触发标记的那一小段，方便看出是不是误判。"""
    flat = " ".join(text.split())
    at = flat.find(marker)
    if at < 0:
        return flat[: width * 2 + len(marker)]
    start, end = max(0, at - width), at + len(marker) + width
    return ("…" if start else "") + flat[start:end] + ("…" if end < len(flat) else "")


def draft_key(module: str, entity: str | None) -> str:
    return f"{module}|{(entity or '').strip().lower()}"


# ---- 主逻辑 ----

class Gate:
    def __init__(self, root: Path, payload: dict):
        self.root = root
        self.payload = payload
        self.config = Config.load(root)
        self.conversation = str(payload.get("conversation_id") or "")
        self.state = SessionState(self.config.cache_dir, self.conversation) if self.conversation else None
        modules_path = self.config.modules_path
        self.registry = ModuleRegistry.load(modules_path) if modules_path.exists() else ModuleRegistry({})
        self._files: dict[str, Path] = {}
        self._entries: dict[str, list[Entry]] = {}
        # 持有会话锁时只留占位符，释放后由 fill_stale 统一核对，免得并发的 Hook 排队等版本库查询
        self.defer_stale = False
        self._deferred: dict[str, Entry] = {}

    # 路径与模块

    def relative(self, path: str, base: str | None = None) -> str | None:
        if not path:
            return None
        full = Path(path)
        if not full.is_absolute():
            full = Path(base or self.root) / full
        try:
            rel = os.path.relpath(full, self.root)
        except ValueError:
            return None
        rel = rel.replace("\\", "/")
        return None if rel.startswith("../") or rel == ".." else rel

    def module_of(self, rel: str | None) -> str | None:
        if rel is None:
            return None
        try:
            match = self.registry.module_for_path(rel)
        except RegistryError:
            return None
        return match.module_id if match else None

    def module_from_args(self, args: dict) -> str | None:
        if args.get("module"):
            try:
                return self.registry.resolve_module(str(args["module"])).id
            except RegistryError:
                return None
        if args.get("path"):
            return self.module_of(self.relative(str(args["path"])))
        return None

    def modules_in_text(self, text: str) -> list[str]:
        """文字里提到的模块：完整模块 id、模块名或别名，以及能映射到模块的文件路径。"""
        lowered = text.lower()
        found = [mid for mid in self.registry.modules if mid.lower() in lowered]
        found += [mid for mid, pattern in self.registry.name_patterns().items() if pattern.search(text)]
        paths = (re.sub(r"^(?:\.[/\\])+", "", t).rstrip(".") for t in _PATH_TOKEN.findall(text))
        found += [m for m in (self.module_of(self.relative(p)) for p in paths) if m]
        return list(dict.fromkeys(found))

    def memory_count(self, module: str) -> int:
        """现行记忆条数；已被替代或停用的不算，全部作废的模块不再拦截。"""
        return len(current_entries(self.module_entries(module)))

    def module_entries(self, module: str) -> list[Entry]:
        if module in self._entries:
            return self._entries[module]
        folder = self.config.entries_dir / module
        entries = []
        for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
            try:
                entry = Entry.from_markdown(path.read_text(encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001, S112
                continue
            entries.append(entry)
            self._files[entry.id] = path
        self._entries[module] = entries
        return entries

    def vcs(self):
        # 只有核对过期、终端命令前后比对才用到版本库，按需导入以缩短钩子启动
        from pmem.vcs.detect import detect_vcs

        return detect_vcs(self.root, self.config.get("vcs"))

    def stale_problems(self, entries: list[Entry]) -> dict[str, list[str]]:
        try:
            checker = AnchorChecker(self.root, self.vcs(), self.config.cache_dir / ANCHOR_CACHE)
            return checker.check(entries, self._files)
        except Exception:  # noqa: BLE001
            return {}

    def memory_lines(self, entries: list[Entry]) -> list[str]:
        """摘要行：类型｜议题｜日期：预览；关联代码之后改过的标“需核实”。"""
        if self.defer_stale:
            self._deferred.update((e.id, e) for e in entries)
            marks = {e.id: _STALE_SLOT.format(e.id) for e in entries}
            return self._lines(entries, marks, _FOOTER_SLOT.format(",".join(marks)))
        problems = self.stale_problems(entries)
        marks = {i: _stale_mark(p) for i, p in problems.items()}
        return self._lines(entries, marks, STALE_FOOTER if problems else "")

    @staticmethod
    def _lines(entries: list[Entry], marks: dict[str, str], footer: str) -> list[str]:
        lines = []
        for e in entries:
            seed = "（种子，待确认）" if e.status == "seed" else ""
            lines.append(f"- {KIND_LABELS.get(e.kind, e.kind)}{seed}｜{e.entity}｜{e.note_date}{marks.get(e.id, '')}："
                         f"{preview(e.content, DIGEST_PREVIEW)}")
        if footer:
            lines.append(footer)
        return lines

    def fill_stale(self, result):
        """把锁内留下的占位符换成核对结果；没有需核实的记忆时占位符连同所在的提示行一起去掉。"""
        if not self._deferred:
            return result
        problems = self.stale_problems(list(self._deferred.values()))
        self._deferred = {}

        def fill(value):
            if isinstance(value, dict):
                return {k: fill(v) for k, v in value.items()}
            if isinstance(value, list):
                return [fill(v) for v in value]
            if not isinstance(value, str) or "\x00" not in value:
                return value
            text = _FOOTER_SLOT_RE.sub(
                lambda m: "\n" + STALE_FOOTER if any(i in problems for i in m.group(1).split(",")) else "", value)
            return _STALE_SLOT_RE.sub(lambda m: _stale_mark(problems.get(m.group(1), [])), text)

        return fill(result)

    def _watched(self, rel: str) -> bool:
        ignore = self.config.get("gate.ignore") or []
        watch = self.config.get("gate.watch") or []
        if any(wglob.globmatch(rel, p, flags=_GLOB) for p in ignore):
            return False
        return not watch or any(wglob.globmatch(rel, p, flags=_GLOB) for p in watch)

    def save(self) -> None:
        if self.state is not None:
            self.state.save()

    def log(self, event_type: str, **fields) -> None:
        log_event(self.config.cache_dir, event_type, conv=self.conversation or None, **fields)

    # 事件

    def on_prompt(self) -> dict:
        text = str(self.payload.get("prompt") or "")
        markers = self.config.get("gate.skip_markers") or []
        skip_marker = next((str(m) for m in markers if asks_to_skip(text, str(m))), None)
        skip = skip_marker is not None
        resume = any(asks_to_skip(text, str(m)) for m in self.config.get("gate.resume_markers") or [])
        analysis = any(
            fuzzy_contains(text.lower() if m.isascii() else text, m.lower() if m.isascii() else m)
            for m in (str(m) for m in self.config.get("gate.analysis_markers") or [])
        )
        asked = self.modules_in_text(text) if self.state is not None else []
        if self.state is not None:
            if resume:
                self.state.data.update(skip=False, skip_reason="", skip_noticed=False)
            elif skip and not self.state.data["skip"]:
                self.state.data.update(skip=True, skip_reason=_around(readable(text, skip_marker), skip_marker))
            self.state.data["analysis"] = self.state.data["analysis"] or analysis
            self.state.data["asked"] = asked
            self.save()
        self.log("prompt", mode=self.payload.get("composer_mode"), skip=skip or None, resume=resume or None,
                 analysis=analysis or None, asked=asked or None)
        result: dict = {"continue": True}
        # 只有能在提问时注入上下文的工具（Claude Code）才当场附上摘要；Cursor 靠读代码时的摘要和回合结束的核对
        if self.payload.get("prompt_context") and self._reviews_on("gate.question_review"):
            digests = [d for d in (self._offer_digest(m, f"你的问题提到了 {m}") for m in asked[:MAX_REVIEW_MODULES]) if d]
            if digests:
                result["additional_context"] = "\n\n".join(digests)
        return result

    # 提问审查：让 Agent 在回答、修改之前看到相关模块的记忆

    def _reviews_on(self, setting: str) -> bool:
        return self.state is not None and not self.state.data["skip"] and self._reminders_on(setting, True)

    def _offer_digest(self, module: str, intro: str, rel: str | None = None) -> str | None:
        """本对话还没看过该模块的记忆时，给出现行记忆摘要并记为已看过；rel 是正在看的文件，相关记忆优先。"""
        if self.state is None or self.state.has("reviewed", module):
            return None
        entries = self.module_entries(module)
        picked = digest(entries, path=rel)
        if not picked:
            return None
        self.state.add("reviewed", module)
        self.save()
        self.log("digest", module=module, ids=[e.id for e in picked])
        intro_line = (
            f"[pmem] {intro}，该模块有 {len(current_entries(entries))} 条现行研发记忆。回答或修改前先看这些结论"
            f"（摘要；要全文或更多请调用 search_memory(module=\"{module}\", query=\"<问题要点>\")）："
        )
        return "\n".join([intro_line, *self.memory_lines(picked)])

    def _skip_notice(self, module: str | None) -> dict:
        """本对话因“跳过记忆”关闭了检查时，第一次碰到有记忆的模块就告诉 Agent，误判也能被发现。"""
        if not module or self.state.data["skip_noticed"] or not self.memory_count(module):
            return {}
        self.state.data["skip_noticed"] = True
        self.save()
        self.log("skip_notice", module=module)
        resume = "、".join(f"“{m}”" for m in self.config.get("gate.resume_markers") or []) or "（未配置）"
        return {"additional_context": (
            f"[pmem] 本对话已按“跳过记忆”关闭记忆检查（来自提问：“{self.state.data['skip_reason']}”），"
            f"{module} 的记忆不会提示，改代码也不拦截。如果这不是用户的本意，请告诉用户：说 {resume} 可以重新打开。"
        )}

    def _read_digest(self, args: dict) -> dict:
        rel = self.relative(str(args.get("file_path") or args.get("path") or ""))
        if rel is None or not self._watched(rel):
            return {}
        if self.state is not None and self.state.data["skip"]:
            return self._skip_notice(self.module_of(rel))
        if not self._reviews_on("gate.read_digest"):
            return {}
        module = self.module_of(rel)
        message = self._offer_digest(module, f"你正在看的 {rel} 属于 {module}", rel) if module else None
        return {"additional_context": message} if message else {}

    def module_at(self, rel: str | None) -> str | None:
        """文件或目录所属的模块；目录跨多个模块时为 None。"""
        if not rel or rel == "." or not self._watched(rel):
            return None
        inside = self.module_of(rel.rstrip("/") + "/_")
        # 目录本身只匹配得上伞形模块（src/pmem/** 能匹配 src/pmem/vcs，src/pmem/vcs/** 不能），先按目录里的文件算
        if (self.root / rel).is_dir():
            return inside or self.module_of(rel)
        return self.module_of(rel) or inside

    def _search_digest(self, args: dict) -> dict:
        """Grep、Glob、语义搜索限定在某个模块的文件或目录里时，同读代码一样附上该模块的摘要。"""
        found = {}
        for path in tool_paths(args):
            rel = self.relative(path)
            module = self.module_at(rel)
            if module and module not in found:
                found[module] = rel
        if not found or self.state is None:
            return {}
        if self.state.data["skip"]:
            return self._skip_notice(next(iter(found)))
        if not self._reviews_on("gate.read_digest"):
            return {}
        messages = [self._offer_digest(m, f"你正在搜索的 {rel} 属于 {m}", rel) for m, rel in found.items()]
        messages = [m for m in messages if m][:MAX_SEARCH_DIGESTS]
        return {"additional_context": "\n\n".join(messages)} if messages else {}

    def _unreviewed(self) -> tuple[list[str], list[str]]:
        """本轮提问提到的、和本轮看过代码的模块里，有记忆却还没看过记忆的，分两组返回。
        Hook 只覆盖 Read 等少数工具，本轮看过的路径再从对话记录里补一遍。"""
        if not self._reviews_on("gate.question_review"):
            return [], []
        path = self.payload.get("transcript_path")
        text = last_user_text(path)
        if text is not None and text.lstrip().startswith("[pmem]"):
            return [], []
        asked = self.modules_in_text(text) if text is not None else self.state.data["asked"]
        viewed = [self.module_at(self.relative(p)) for p in turn_tool_paths(path, VIEW_TOOLS)]

        def pending(modules) -> list[str]:
            return [m for m in dict.fromkeys(modules) if m and not self.state.has("reviewed", m)
                    and not self.state.has("review_nudged", m) and self.memory_count(m)]

        asked = pending(asked)[:MAX_REVIEW_MODULES]
        viewed = [m for m in pending(viewed) if m not in asked][:MAX_REVIEW_MODULES - len(asked)]
        return asked, viewed

    def _target_modules(self, rel: str) -> list[str]:
        """写入目标涉及的模块。目录（rm -rf、Remove-Item -Recurse）按自身路径会落到更宽泛的伞形模块，
        要把登记在它下面的各个模块都算上，否则查过伞形模块就能删掉整个子模块。"""
        if not (self.root / rel).is_dir():
            return [m for m in [self.module_of(rel)] if m]
        base = rel.strip("/")
        # 项目根目录（rm -rf .）下的所有模块都算
        prefix = "" if base in ("", ".") else base.lower() + "/"
        found = [self.module_of(base + "/_" if prefix else "_")]
        for mid, module in self.registry.modules.items():
            for pattern in module.paths:
                unprefixed = re.sub(r"^(?:\./)+", "", pattern.replace("\\", "/"))
                literal = re.split(r"[*?\[{]", unprefixed, maxsplit=1)[0].lower()
                if literal.startswith(prefix):
                    found.append(mid)
        return [m for m in dict.fromkeys(found) if m]

    def _guard(self, rel: str | None, searched_here: set[str] = frozenset()) -> dict | None:
        if rel is not None and WILDCARD_PATH.search(rel):
            # rm -rf src/* 这类通配符目标按实际展开出的文件和目录逐个检查；展开结果不再二次展开
            matches = glob.glob(rel, root_dir=self.root, recursive=True)[:MAX_GLOB_TARGETS]
            return next((v for v in (self._guard_path(m.replace("\\", "/"), searched_here) for m in matches)
                         if v is not None), None)
        return self._guard_path(rel, searched_here)

    def _guard_path(self, rel: str | None, searched_here: set[str]) -> dict | None:
        if rel is None or not self._watched(rel):
            return None
        for module in self._target_modules(rel):
            if module in searched_here:
                continue
            denied = self._guard_module(rel, module)
            if denied is not None:
                return denied
        return None

    def _guard_module(self, rel: str, module: str) -> dict | None:
        mode = self.config.get("gate.mode")
        if mode == "off" or self.state is None or self.state.data["skip"]:
            return None
        if self.state.has("searched", module):
            return None
        count = self.memory_count(module)
        if count == 0:
            return None
        if mode == "warn":
            if self.state.has("warned", module):
                return None
            self.state.add("warned", module)
            self.save()
        call = f'search_memory(module="{module}")'
        # Cursor 只把 user_message 交给 Agent（实测），因此指引必须完整写在这里
        message = f"pmem：{rel} 属于 {module}（已有 {count} 条研发记忆）。请先调用 {call} 了解已有结论，"
        if mode == "warn":
            message += "然后重试本次修改。"
        else:
            message += (
                f"查过之后才能修改该模块。MCP 工具不可用时，在终端运行 pmem search --module {module} 也算"
                "（输出不能丢弃，如 > $null、| Out-Null）；检索要真正返回结果才算查过。"
                "确实不需要记忆时，请用户回复“跳过记忆”。"
            )
        text, total = self._pitfalls(module)
        message += text
        self.log("gate", module=module, file=rel, mode=mode, pitfalls=total or None)
        return {"permission": "deny", "user_message": message, "agent_message": message}

    def _pitfalls(self, module: str) -> tuple[str, int]:
        """检索按关键词排序，可能漏掉与这次修改相关的坑；排除项、风险、更正直接列出来，按这个顺序。"""
        pitfalls = sorted((e for e in current_entries(self.module_entries(module)) if e.kind in PITFALL_KINDS),
                          key=lambda e: PITFALL_KINDS.index(e.kind))
        if not pitfalls:
            return "", 0
        shown = pitfalls[:MAX_GUARD_PITFALLS]
        more = f"（另有 {len(pitfalls) - len(shown)} 条，检索时可见）" if len(pitfalls) > len(shown) else ""
        text = "\n该模块已知的排除项、风险和更正，改之前先对照" + more + "：\n" + "\n".join(self.memory_lines(shown))
        return text, len(pitfalls)

    def on_pre_tool(self) -> dict:
        name = str(self.payload.get("tool_name") or "")
        args = tool_input(self.payload)
        if any(t in name for t in PMEM_TOOLS) and foreign_tool(self.payload):
            return dict(ALLOW)
        if "record_memory" in name:
            return self._inject(args, with_draft=True)
        # MCP 检索在返回结果之后（after-mcp / post-tool）才登记为查过，调用失败不算
        if "search_memory" in name:
            # Cursor 的 tool_name 不带服务名，别家记忆服务的同名工具可能拒收多出的参数
            if "pmem" in name.lower() or self.module_from_args(args):
                return self._inject(args, with_draft=False)
            return dict(ALLOW)
        if "memory_graph" in name:
            return dict(ALLOW)
        if name.lower() == "shell":
            command = str(args.get("command") or "")
            # 命令里的 pmem search 先挂起，执行完才算查过；同一条命令里对这些模块的写入先放行，其他模块照样检查
            in_command = self._note_cli_calls(command)
            base = args.get("cwd") or str(self.root)
            targets, _ = scan(command, base)
            denied = next((v for v in (self._guard(self.relative(t, base), in_command) for t in targets)
                           if v is not None), None)
            if denied is not None:
                return denied
            if _needs_snapshot(command, base):
                self._snapshot_before_shell(command)
            return dict(ALLOW)
        if name.lower() not in WRITE_TOOLS:
            return dict(ALLOW)
        raw = args.get("file_paths") or [args.get("file_path") or args.get("path") or args.get("target_file") or ""]
        return next((v for v in map(self._guard, [self.relative(str(p)) for p in raw]) if v is not None), dict(ALLOW))

    def _note_cli_calls(self, command: str) -> set[str]:
        """终端里的 pmem search/graph/record 与 MCP 工具等价。都先挂起，命令执行完、看得到结果才登记
        （见 _confirm_cli_calls）；返回这条命令里检索的模块。"""
        searches = cli_args(command, "search") + cli_args(command, "graph")
        records = cli_args(command, "record")
        if self.state is not None and (searches or records):
            for field, calls in (("cli_pending", searches), ("cli_record_pending", records)):
                if calls:
                    pending = self.state.data[field]
                    pending[_command_key(command)] = calls
                    self.state.data[field] = dict(list(pending.items())[-MAX_PENDING_SNAPSHOTS:])
            self.save()
        return {m for m in map(self.module_from_args, searches) if m}

    def _pop_cli_pending(self, field: str, command: str, has_calls: bool) -> list[dict] | None:
        pending = self.state.data[field]
        key = _command_key(command)
        if key not in pending and len(pending) == 1 and has_calls:
            # 前后两次拿到的命令文本可能因转码不同；只有一条在等、且这条命令本身也调了 pmem 时才认作同一条，
            # 并行的 ls 这类命令先结束时不能把别的命令挂起的调用拿走
            key = next(iter(pending))
        return pending.pop(key, None)

    def _confirm_cli_calls(self) -> None:
        """命令跑完：挂起的终端检索登记为查过、写入登记为写过。拿得到命令输出时，检索要在输出里看到该模块，
        写入还要看到 draft_id（写入失败、|| 之后没执行的都没有）。"""
        if self.state is None:
            return
        command = str(tool_input(self.payload).get("command") or "")
        searches = self._pop_cli_pending("cli_pending", command,
                                         bool(cli_args(command, "search") or cli_args(command, "graph")))
        records = self._pop_cli_pending("cli_record_pending", command, bool(cli_args(command, "record")))
        if searches is None and records is None:
            return
        self.save()
        output = shell_output(self.payload)
        lowered = output.lower() if output is not None else None
        for args in searches or []:
            module = self.module_from_args(args)
            if lowered is not None and (not module or module.lower() not in lowered):
                self.log("search_call_unseen", module=module, via="cli")
                continue
            self._mark_searched(args, via="cli")
        for args in records or []:
            module = self.module_from_args(args)
            if lowered is not None and (not module or module.lower() not in lowered
                                        or "draft_id" not in lowered.replace("-", "_")):
                self.log("record_call_failed", module=module, via="cli")
                continue
            if module:
                self.state.add("cli_recorded", module)
            self.log("record_call", module=module, via="cli")
        self.save()

    def _inject(self, args: dict, with_draft: bool) -> dict:
        if not args or self.state is None:
            return dict(ALLOW)
        updated = dict(args)
        updated["source_conversation"] = self.conversation
        module = self.module_from_args({"module": args.get("module")}) if with_draft else None
        # 同一模块下的不同议题是不同的记忆，只有议题也相同时才覆盖本对话写过的草稿
        entity = self.registry.resolve_entity(module, str(args.get("entity") or "")) if module else None
        draft = self.state.data["written"].get(draft_key(module, entity)) if module else None
        if draft and not args.get("draft_id") and self._draft_open(module, draft):
            updated["draft_id"] = draft
        # 覆盖草稿时不补锚点，让服务沿用草稿原有的锚点；
        # 载荷被转码损坏、只按字段抠出了部分参数时，看不到 Agent 写的 anchors，补了会把它覆盖成只到文件
        if module and not args.get("anchors") and not updated.get("draft_id") and not self.payload.get("_partial"):
            files = [item.split("|", 1)[1] for item in self.state.data["edited_files"] if item.startswith(module + "|")]
            if files:
                updated["anchors"] = files[-MAX_AUTO_ANCHORS:]
        return {"permission": "allow", "updated_input": updated}

    def _draft_open(self, module: str, draft: str) -> bool:
        """草稿已提交就不能再覆盖：长对话跨过提交后，注入旧 id 只会让服务拒绝这次写入。"""
        path = self.config.entries_dir / module / f"{draft}.md"
        if not path.exists():
            return True
        try:
            return not self.vcs().is_committed(path)
        except Exception:  # noqa: BLE001
            return True

    def _mark_searched(self, args: dict, via: str) -> None:
        module = self.module_from_args(args)
        if module and self.state is not None:
            for key in ("searched", "consulted", "reviewed"):
                self.state.add(key, module)
            self.save()
        self.log("search_call", module=module, via=via)

    def on_before_mcp(self) -> dict:
        """旧版 hooks.json 仍会调用；检索改在返回结果之后登记，这里只放行。"""
        return dict(ALLOW)

    def on_after_mcp(self) -> dict:
        name = str(self.payload.get("tool_name") or "")
        if self.state is None or not any(t in name for t in PMEM_TOOLS) or foreign_tool(self.payload):
            return {}
        response = tool_response(self.payload)
        if not response or response.get("ok") is not True:
            return {}
        module = self.module_from_args({"module": response["module"]}) if response.get("module") else None
        rows = [r for key in ("items", "timeline") for r in response.get(key) or [] if isinstance(r, dict)]
        ids = [str(i) for i in dict.fromkeys([response.get("id"), *(r.get("id") for r in rows)])
               if i and re.fullmatch(_ULID, str(i))]
        if "record_memory" not in name and not self._from_pmem(name, response, ids):
            # 别家记忆服务的同名工具，不算查过 pmem 的记忆
            self.log("foreign_search", module=module)
            return {}
        if "record_memory" in name:
            if module and response.get("id") in ids:
                self.state.data["written"][draft_key(module, response.get("entity"))] = response["id"]
                self.state.add("recorded", response["id"])
            self.log("mcp_record", module=module, ids=ids[:1])
        else:
            if module:
                self.state.add("searched", module)
                self.state.add("consulted", module)
            # 不限模块的检索：结果里出现过的模块也算看过记忆
            for seen in {str(r["module"]) for r in rows if r.get("module")} | ({module} if module else set()):
                self.state.add("reviewed", seen)
            for mid in ids:
                self.state.add("returned", mid)
            self.log("mcp_search", module=module, ids=ids)
        self.save()
        return {}

    def _from_pmem(self, name: str, response: dict, ids: list[str]) -> bool:
        """结果来自 pmem：带 pmem 的来源标记、工具名里有服务名 pmem，或返回的记忆在本仓库。
        没有标记的旧版服务返回空结果时也不算，Agent 可以改用终端 pmem search。"""
        if response.get("server") == "pmem" or "pmem" in name.lower():
            return True
        return bool(ids) and self._has_local(ids)

    def _has_local(self, ids: list[str]) -> bool:
        folder = self.config.entries_dir
        return folder.is_dir() and any(next(folder.glob(f"*/{i}.md"), None) for i in ids)

    def on_edited(self) -> dict:
        self._mark_edited(str(self.payload.get("file_path") or ""))
        return {}

    def _mark_edited(self, path: str) -> None:
        rel = self.relative(path)
        module = self.module_of(rel)
        if module and self.state is not None:
            self.state.add("edited", module)
            self.state.add("edited_files", f"{module}|{rel}")
            self.save()
        if rel is not None:
            self.log("edit", module=module, file=rel)

    def on_post_tool(self) -> dict:
        result = self._post_tool()
        notice = self.error_notice()
        if notice:
            result = dict(result or {})
            result["additional_context"] = "\n\n".join(filter(None, [result.get("additional_context"), notice]))
        return result

    def error_notice(self) -> str | None:
        """Hook 出错时默认放行（不能卡住开发），但用户得知道闸门那次没起作用：有新错误就提醒一次。"""
        if self.config.get("gate.mode") == "off":
            return None
        log = self.config.cache_dir / ERROR_LOG
        seen = self.config.cache_dir / ERROR_SEEN
        try:
            changed = log.stat().st_mtime
        except OSError:
            return None
        try:
            last_seen = seen.stat().st_mtime
        except OSError:
            last_seen = time.time() - ERROR_NOTICE_WINDOW
        if changed <= last_seen:
            return None
        try:
            seen.parent.mkdir(parents=True, exist_ok=True)
            seen.write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
            tail = log.read_bytes()[-4096:].decode("utf-8", "replace")
        except OSError:
            return None
        lines = [line.strip() for line in tail.splitlines() if line.strip()]
        last = lines[-1][:200] if lines else ""
        self.log("error_notice", error=last)
        return (f"[pmem] 记忆闸门刚才出错，那次已自动放行、没有做记忆检查（{last}）。"
                f"请在回复里提醒用户运行 pmem doctor 查看原因（错误日志：{log}）。")

    def _post_tool(self) -> dict:
        """工具调用之后：读代码时附上该模块的记忆摘要；Claude Code / Codex 另由此处理 pmem 工具的返回与编辑过的文件。"""
        from pmem.hooks.agents import edited_files

        name = str(self.payload.get("tool_name") or "")
        if any(t in name for t in PMEM_TOOLS):
            return self.on_after_mcp()
        if name.lower() == "read":
            return self._read_digest(tool_input(self.payload))
        if name.lower() in SEARCH_TOOLS:
            return self._search_digest(tool_input(self.payload))
        if name.lower() == "shell":
            self._confirm_cli_calls()
            return self._shell_after()
        for path in edited_files(self.payload):
            self._mark_edited(path)
        return {}

    # 终端命令的事后核对：事前解析不出目标时，比对执行前后的未提交文件

    def _dirty_snapshot(self, paused_ok: bool = True) -> dict[str, list[int]] | None:
        # 大型工作副本（尤其 SVN）列未提交文件可能要好几秒；慢过一次就当天不再做，免得拖慢每条终端命令
        slow = self.config.cache_dir / SLOW_SNAPSHOT_MARK
        try:
            if paused_ok and slow.exists() and time.time() - slow.stat().st_mtime < SLOW_SNAPSHOT_PAUSE:
                return None
        except OSError:
            pass
        started = time.monotonic()
        try:
            files = self.vcs().dirty_files()
        except Exception:  # noqa: BLE001
            return None
        if time.monotonic() - started > SLOW_SNAPSHOT_SECONDS:
            try:
                slow.parent.mkdir(parents=True, exist_ok=True)
                slow.write_text(f"{time.monotonic() - started:.1f}s", encoding="utf-8")
            except OSError:
                pass
            self.log("snapshot_slow", seconds=round(time.monotonic() - started, 1))
            if paused_ok:
                # 执行前就慢：放弃这次比对，免得执行后再等一遍
                return None
        if files is None:
            return None
        snapshot = {}
        for rel in files:
            try:
                stat = (self.root / rel).stat()
                snapshot[rel] = [stat.st_mtime_ns, stat.st_size]
            except OSError:
                snapshot[rel] = [0, -1]
        return snapshot

    def _pending_snapshots(self) -> dict:
        # 旧版状态文件里是单个快照或 None
        pending = self.state.data.get("shell_before")
        return pending if isinstance(pending, dict) and all(k.startswith("cmd:") for k in pending) else {}

    def _snapshot_before_shell(self, command: str) -> None:
        """按命令分开存快照：Cursor 并行执行的几条命令各自比对，不互相覆盖。"""
        if self.state is None or self.config.get("gate.mode") == "off" or self.state.data["skip"]:
            return
        snapshot = self._dirty_snapshot()
        if snapshot is not None:
            pending = self._pending_snapshots()
            pending[_command_key(command)] = snapshot
            self.state.data["shell_before"] = dict(list(pending.items())[-MAX_PENDING_SNAPSHOTS:])
            self.save()

    def _only_committed(self, rel: str, before: dict, after: dict) -> bool:
        """git commit / svn commit 让文件不再“未提交”，但文件本身没动，不算命令改过。"""
        if rel in after:
            return False
        try:
            stat = (self.root / rel).stat()
        except OSError:
            return False
        return before.get(rel) == [stat.st_mtime_ns, stat.st_size]

    def _shell_after(self) -> dict:
        """命令实际改过的文件记为已编辑（结束时提醒写记忆）；改到没查过记忆的模块时立即提醒 Agent 补查。"""
        if self.state is None:
            return {}
        pending = self._pending_snapshots()
        command = str(tool_input(self.payload).get("command") or "")
        key = _command_key(command)
        if key not in pending and len(pending) == 1 and _needs_snapshot(command, str(self.root)):
            # 前后两次拿到的命令文本可能因转码不同；只有一条在等、且这条命令本身也会存快照时就是它。
            # 并行的 ls 这类命令先结束时不能把别的命令的快照拿走
            key = next(iter(pending))
        before = pending.pop(key, None)
        if before is None:
            return {}
        self.state.data["shell_before"] = pending
        after = self._dirty_snapshot(paused_ok=False)
        if after is None:
            self.save()
            return {}
        changed = sorted(rel for rel in set(before) | set(after)
                         if before.get(rel) != after.get(rel) and not self._only_committed(rel, before, after))
        # 编辑工具改过的文件已经过闸门检查；与终端命令并行改的不算到命令头上
        by_tools = {item.split("|", 1)[1] for item in self.state.data["edited_files"]}
        late: dict[str, list[str]] = {}
        for rel in changed:
            if not self._watched(rel) or rel in by_tools:
                continue
            self._mark_edited(rel)
            module = self.module_of(rel)
            if (module and not self.state.has("searched", module) and not self.state.has("late_warned", module)
                    and self.memory_count(module)):
                late.setdefault(module, []).append(rel)
        for module in late:
            self.state.add("late_warned", module)
        self.save()
        if not late:
            return {}
        messages = []
        for module, files in late.items():
            self.log("late_gate", module=module, files=files[:5])
            messages.append(
                f"[pmem] 刚才的终端命令改了 {'、'.join(files[:5])}，属于 {module}（已有 {self.memory_count(module)} 条研发记忆），"
                f"但本对话还没查过该模块的记忆。请立即调用 search_memory(module=\"{module}\") 核对这次修改，"
                "与记忆冲突就改回。" + self._pitfalls(module)[0]
            )
        return {"additional_context": "\n\n".join(messages)}

    def on_compact(self) -> dict:
        if self.state is not None:
            # 压缩后之前看过的记忆可能已不在上下文里
            for key in ("searched", "warned", "reviewed"):
                self.state.data[key] = []
            self.save()
        return {}

    def _written(self) -> set[str]:
        return {key.split("|", 1)[0] for key in self.state.data["written"]} | set(self.state.data["cli_recorded"])

    def _reminders_on(self, setting: str, default: bool | None = None) -> bool:
        return bool(self.config.get(setting, default)) and self.config.get("gate.mode") != "off"

    def _pending_nudges(self) -> list[str]:
        """改了代码却没写记忆的模块。"""
        if not self._reminders_on("gate.stop_reminder", True):
            return []
        written = self._written()
        return [m for m in self.state.data["edited"]
                if m not in written and not self.state.has("nudged", m) and not self._deprecated(m)]

    def _deprecated(self, module_id: str) -> bool:
        """废弃模块只读，写记忆会被拒绝，所以不提醒写。"""
        module = self.registry.modules.get(module_id)
        return module is not None and module.deprecated

    def _analyzed(self) -> list[str]:
        """排查类对话里查过记忆、但既没改代码也没写记忆的模块。"""
        if not self.state.data["analysis"]:
            return []
        done = self._written() | set(self.state.data["edited"])
        return [m for m in self.state.data["consulted"] if m not in done]

    def _consulted_only(self) -> list[str]:
        """整个对话只查了记忆、没改代码也没写记忆时，查过的模块；写代码时顺带查的模块不算。"""
        if not self._reminders_on("gate.analysis_reminder"):
            return []
        if self._written() or self.state.data["edited"]:
            return []
        return [m for m in self.state.data["consulted"] if not self.state.has("nudged", m) and not self._deprecated(m)]

    def on_stop(self) -> dict:
        if self.state is None:
            return {}
        self.state.cleanup_old()
        status = self.payload.get("status")
        # 中断或出错结束的回合、用户说了“跳过记忆”的对话都不提醒；由提醒触发的续跑回合
        # （Cursor 的 loop_count、Claude Code 的 stop_hook_active）也不再追加，留到下一个回合
        finished = status in (None, "completed") and not self.state.data["skip"]
        follow = finished and not (self.payload.get("loop_count") or self.payload.get("stop_hook_active"))
        asked, viewed = self._unreviewed() if follow else ([], [])
        review = asked + viewed
        pending = self._pending_nudges() if follow else []
        analyzed = self._analyzed() if finished else []
        consulted_pending = self._consulted_only() if follow else []
        notice = self.error_notice() if follow else None
        usage = {k: self.payload.get(k) for k in TOKEN_FIELDS if isinstance(self.payload.get(k), int)}
        self.save()
        self.log(
            "stop",
            status=status,
            loops=self.payload.get("loop_count"),
            transcript=self.payload.get("transcript_path"),
            returned=self.state.data["returned"] or None,
            recorded=self.state.data["recorded"] or None,
            edited=self.state.data["edited"] or None,
            analyzed=analyzed or None,
            review=review or None,
            nudged=(pending + consulted_pending) or None,
            **usage,
        )
        if not review and not pending and not consulted_pending:
            return {"followup_message": f"{FOLLOWUP_HEADER}\n{notice}"} if notice else {}
        for module in review:
            self.state.add("review_nudged", module)
        for module in pending + consulted_pending:
            self.state.add("nudged", module)
        self.save()
        messages = []
        if review:
            reasons = ([f"你的问题涉及 {'、'.join(asked)}"] if asked else []) + (
                [f"本轮看过 {'、'.join(viewed)} 的代码"] if viewed else [])
            messages.append(
                f"[pmem] {'，'.join(reasons)}，这些模块已有研发记忆，但本轮回答前没有查过。"
                f"请对每个模块调用 search_memory(module=\"<模块>\", query=\"<问题要点>\") 核对："
                "与回答一致就简短说明“已核对记忆”；记忆里有排除项、风险或不同结论，请据此修正回答。"
            )
        if pending:
            messages.append(
                f"[pmem] 本轮修改了 {'、'.join(pending)}，但还没有写研发记忆。请直接用 record_memory "
                "为每个模块写一条：为什么这样改、影响范围、潜在风险（已有记忆说的就是这件事时，用 supersedes "
                "更新它）。不要询问用户，写完用一句话说明记了什么。"
            )
        if consulted_pending:
            messages.append(
                f"[pmem] 本轮查了 {'、'.join(consulted_pending)} 的记忆，没有改代码也没有写记忆。"
                "得出了新结论（根因、排除过的方向、决定、风险）就直接用 record_memory 记下；"
                "没有新结论就简短说明“已核对，无新结论”。不要询问用户。"
            )
        if notice:
            messages.append(notice)
        return {"followup_message": "\n".join([FOLLOWUP_HEADER, *messages])}


HANDLERS = {
    # 新对话开始：装了 pmem 时无事可做；没装时由 .memory/bin/pmem-hook 包装脚本提醒
    "session": lambda gate: {},
    "prompt": Gate.on_prompt,
    "pre-tool": Gate.on_pre_tool,
    "before-mcp": Gate.on_before_mcp,
    "after-mcp": Gate.on_after_mcp,
    "edited": Gate.on_edited,
    "post-tool": Gate.on_post_tool,
    "compact": Gate.on_compact,
    "stop": Gate.on_stop,
}


def handle(event: str, payload: dict, root: Path) -> dict:
    handler = HANDLERS.get(event)
    if handler is None:
        return {}
    gate = Gate(Path(root), payload)
    if gate.state is None:
        return handler(gate)
    gate.defer_stale = True
    with gate.state.locked():
        result = handler(gate)
    gate.defer_stale = False
    return gate.fill_stale(result)
