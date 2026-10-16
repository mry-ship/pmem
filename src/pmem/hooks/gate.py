from __future__ import annotations

import json
import os
import re
from pathlib import Path

from wcmatch import glob as wglob

from pmem.core.config import Config
from pmem.core.entry import Entry
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
from pmem.hooks.state import SessionState
from pmem.index.anchors import STALE_LABEL, AnchorChecker
from pmem.index.graph import KIND_LABELS, current_entries, digest, preview
from pmem.metrics.events import log_event
from pmem.vcs.detect import detect_vcs

WRITE_TOOLS = {"write", "strreplace", "edit", "multiedit", "editnotebook", "delete", "search_replace"}
_GLOB = wglob.GLOBSTAR | wglob.BRACE | wglob.DOTGLOB | wglob.FORCEUNIX | wglob.IGNORECASE
_NULL_TARGETS = {"$null", "/dev/null", "nul", "&1", "&2"}
_REDIRECT = re.compile(r"(?<![0-9&])>>?\s*([^\s|;&<>]+)")
_PS_WRITERS = {"set-content", "add-content", "out-file", "new-item", "clear-content", "remove-item", "ri", "sc", "ac"}
_RM = {"rm", "del", "erase", "rmdir", "rd"}
_COPY = {"cp", "copy", "copy-item", "cpi"}
_MOVE = {"mv", "move", "move-item", "mi", "rename-item", "rni", "ren"}
_PATH_PARAMS = ("-path", "-literalpath", "-filepath", "-destination")
_SCRIPT_SUFFIXES = (".py", ".js", ".mjs", ".cjs")
_INTERPRETERS = {"python", "python3", "py", "node", "deno"}
_SCRIPT_MAX_BYTES = 200_000
_CODE_WRITES = re.compile(
    r"open\([^)]*['\"][wax]b?\+?['\"]|write_text|write_bytes|writeFileSync|appendFileSync|\.unlink\("
    r"|os\.(?:remove|rename|replace)\(|shutil\.(?:copy\w*|move|rmtree)\(|WriteAll\w+|AppendAll\w+"
)
_PATH_LITERAL = re.compile(r"['\"]([^'\"\s]*[/\\][^'\"\s]*|[^'\"\s/\\]+\.\w{1,8})['\"]")
_DOTNET_WRITE = re.compile(r"\[(?:System\.)?IO\.File\]::(?:WriteAll\w+|AppendAll\w+|Delete|Copy|Move)\(\s*['\"]([^'\"]+)",
                           re.IGNORECASE)
_PATCH_FILE = re.compile(r"^(?:\+\+\+ b|--- a)/(\S+)", re.MULTILINE)
VIEW_TOOLS = {"read", "grep", "glob", "semanticsearch", "codebase_search"}
SEARCH_TOOLS = VIEW_TOOLS - {"read"}
MAX_SEARCH_DIGESTS = 2
_ULID = r"[0-9A-HJKMNP-TV-Z]{26}"
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")
ALLOW = {"permission": "allow"}
PMEM_TOOLS = ("record_memory", "search_memory", "memory_graph")
MAX_AUTO_ANCHORS = 5
MAX_REVIEW_MODULES = 3
DIGEST_PREVIEW = 100
PITFALL_KINDS = ("exclusion", "risk", "correction")
MAX_GUARD_PITFALLS = 5
_PATH_TOKEN = re.compile(r"[\w.\-]*[/\\][\w./\\\-]+")


# ---- 终端命令里的写文件目标 ----

def _segments(command: str) -> list[str]:
    """按换行和 ; && || | 拆成单条命令；行尾的 ` 或 \\ 是续行，先接回去。"""
    joined = re.sub(r"[`\\][ \t]*\r?\n", " ", command or "")
    return re.split(r"\s*(?:\|\||&&|[;|\r\n])\s*", joined)


def _tokens(segment: str) -> list[str]:
    return [t.strip("'\"") for t in re.findall(r"'[^']*'|\"[^\"]*\"|\S+", segment)]


def _program(token: str) -> str:
    return re.split(r"[\\/]", token)[-1].lower().removesuffix(".exe")


def _expand(token: str) -> str:
    return os.path.expandvars(re.sub(r"\$env:(\w+)", lambda m: os.environ.get(m[1], m[0]), token))


def _read_small(path: str, base: str | None) -> str:
    full = Path(_expand(path))
    if not full.is_absolute():
        full = Path(base or ".") / full
    try:
        return full.read_text(encoding="utf-8", errors="replace") if full.stat().st_size <= _SCRIPT_MAX_BYTES else ""
    except OSError:
        return ""


def _code_targets(code: str) -> list[str]:
    """脚本或内联代码里写了文件时，把其中像路径的字符串都当作目标；宁可多拦一次，也别漏掉。"""
    return _PATH_LITERAL.findall(code) if _CODE_WRITES.search(code) else []


def _script_of(tokens: list[str]) -> str | None:
    """解释器（python、node 等）后的第一个参数：脚本路径或内联代码；`uv run x.py` 也算。不是在跑代码时为 None。"""
    names = [_program(t) for t in tokens]
    start = next((i + 1 for i, n in enumerate(names) if n in _INTERPRETERS), None)
    if start is not None:
        return next((t for t in tokens[start:] if not t.startswith("-")), "")
    if names[:2] == ["uv", "run"]:
        script = next((t for t in tokens[2:] if not t.startswith("-")), "")
        return script if script.lower().endswith(_SCRIPT_SUFFIXES) else None
    return None


def _git_targets(rest: list[str], base: str | None) -> list[str]:
    if not rest:
        return []
    sub, args = rest[0].lower(), rest[1:]
    if sub in ("checkout", "restore") and "--" in args:
        return args[args.index("--") + 1:]
    if sub in ("restore", "rm", "mv"):
        return [t for t in args if not t.startswith("-")]
    if sub in ("apply", "am"):
        return [p for t in args if not t.startswith("-") for p in _PATCH_FILE.findall(_read_small(t, base))]
    return []


def _copy_targets(head: str, rest: list[str]) -> list[str]:
    named = {t.lower(): rest[i + 1] for i, t in enumerate(rest[:-1]) if t.lower() in _PATH_PARAMS}
    positional = [t for t in rest if not t.startswith("-") and t not in named.values()]
    if head in _MOVE:
        return [*named.values(), *positional]
    destination = named.get("-destination") or (positional[-1] if len(positional) > 1 else None)
    return [destination] if destination else []


def shell_write_targets(command: str, base: str | None = None) -> list[str]:
    """终端命令会写到的文件。base 是命令的工作目录，用来读命令里引用的脚本和补丁。"""
    targets: list[str] = _DOTNET_WRITE.findall(command or "")
    runs_code = False
    for segment in _segments(command):
        targets += _REDIRECT.findall(segment)
        tokens = _tokens(segment)
        if not tokens:
            continue
        head, rest = tokens[0].lower(), tokens[1:]
        script = _script_of(tokens)
        if script is not None:
            runs_code = True
            if script.lower().endswith(_SCRIPT_SUFFIXES):
                targets += _code_targets(_read_small(script, base))
        if head == "sed" and any(t.startswith("-i") for t in rest) and rest:
            targets.append(rest[-1])
        elif head == "tee" or head in _RM:
            targets += [t for t in rest if not t.startswith("-")]
        elif head == "git":
            targets += _git_targets(rest, base)
        elif head in _COPY or head in _MOVE:
            targets += _copy_targets(head, rest)
        elif head in _PS_WRITERS:
            for i, token in enumerate(rest):
                if token.lower() in ("-path", "-filepath", "-literalpath") and i + 1 < len(rest):
                    targets.append(rest[i + 1])
                    break
            else:
                positional = [t for i, t in enumerate(rest) if not t.startswith("-") and (i == 0 or not rest[i - 1].startswith("-"))]
                targets += positional[:1]
    # 内联代码（python -c、heredoc、管道送入的脚本）会被分号拆散，按整条命令找
    if runs_code:
        targets += _code_targets(command)
    seen: list[str] = []
    for target in targets:
        if target.lower() not in _NULL_TARGETS and not target.startswith("-") and target not in seen:
            seen.append(target)
    return seen


# 以这些程序开头时，pmem 可以出现在它们的参数之后（如 uv run --extra embed pmem record）
_LAUNCHERS = {"uv", "uvx", "pipx", "python", "python3", "py"}


def cli_args(command: str, subcommand: str) -> list[dict]:
    """终端里的 `pmem search/record ...` 与对应 MCP 工具等价，按出现顺序返回每一处的 module/path 参数。"""
    found: list[dict] = []
    for segment in _segments(command):
        tokens = _tokens(segment)
        names = [re.split(r"[\\/]", t)[-1].lower().removesuffix(".exe") for t in tokens]
        start = next(
            (i + 2 for i in range(len(tokens) - 1)
             if names[i] == "pmem" and tokens[i + 1] == subcommand and (i == 0 or names[0] in _LAUNCHERS)),
            None,
        )
        if start is None:
            continue
        rest = tokens[start:]
        args: dict = {}
        for i, token in enumerate(rest[:-1]):
            if token in ("--module", "--path"):
                args[token[2:]] = rest[i + 1]
        found.append(args)
    return found


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
        found += [m for m in (self.module_of(self.relative(t.strip("."))) for t in _PATH_TOKEN.findall(text)) if m]
        return list(dict.fromkeys(found))

    def memory_count(self, module: str) -> int:
        folder = self.config.entries_dir / module
        return sum(1 for _ in folder.glob("*.md")) if folder.is_dir() else 0

    def module_entries(self, module: str) -> list[Entry]:
        folder = self.config.entries_dir / module
        entries = []
        for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
            try:
                entry = Entry.from_markdown(path.read_text(encoding="utf-8-sig"))
            except Exception:  # noqa: BLE001, S112
                continue
            entries.append(entry)
            self._files[entry.id] = path
        return entries

    def stale_problems(self, entries: list[Entry]) -> dict[str, list[str]]:
        try:
            checker = AnchorChecker(self.root, detect_vcs(self.root, self.config.get("vcs")))
            return checker.check(entries, self._files)
        except Exception:  # noqa: BLE001
            return {}

    def memory_lines(self, entries: list[Entry]) -> list[str]:
        """摘要行：类型｜议题｜日期：预览；关联代码之后改过的标“需核实”。"""
        problems = self.stale_problems(entries)
        lines = []
        for e in entries:
            mark = f"（⚠ {STALE_LABEL}：{'；'.join(problems[e.id])}）" if e.id in problems else ""
            lines.append(f"- {KIND_LABELS.get(e.kind, e.kind)}｜{e.entity}｜{e.note_date}{mark}："
                         f"{preview(e.content, DIGEST_PREVIEW)}")
        if problems:
            lines.append(f"标“{STALE_LABEL}”的记忆写下后关联代码又改过，依赖前先对照代码："
                         "仍成立就 confirm_memory，不成立就写 correction 替代。")
        return lines

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

    def _offer_digest(self, module: str, intro: str) -> str | None:
        """本对话还没看过该模块的记忆时，给出现行记忆摘要并记为已看过。"""
        if self.state is None or self.state.has("reviewed", module):
            return None
        entries = self.module_entries(module)
        picked = digest(entries)
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
        message = self._offer_digest(module, f"你正在看的 {rel} 属于 {module}") if module else None
        return {"additional_context": message} if message else {}

    def module_at(self, rel: str | None) -> str | None:
        """文件或目录所属的模块；目录跨多个模块时为 None。"""
        if not rel or rel == "." or not self._watched(rel):
            return None
        return self.module_of(rel) or self.module_of(rel.rstrip("/") + "/_")

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
        messages = [self._offer_digest(m, f"你正在搜索的 {rel} 属于 {m}") for m, rel in found.items()]
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

    def _guard(self, rel: str | None) -> dict | None:
        if rel is None or not self._watched(rel):
            return None
        module = self.module_of(rel)
        mode = self.config.get("gate.mode")
        if module is None or mode == "off" or self.state is None or self.state.data["skip"]:
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
                f"查过之后才能修改该模块。MCP 工具不可用时，在终端运行 pmem search --module {module} 也算；"
                "检索报错同样视为查过。确实不需要记忆时，请用户回复“跳过记忆”。"
            )
        # 检索按关键词排序，可能漏掉与这次修改相关的坑；排除项、风险、更正直接列出来，按这个顺序
        pitfalls = sorted((e for e in current_entries(self.module_entries(module)) if e.kind in PITFALL_KINDS),
                          key=lambda e: PITFALL_KINDS.index(e.kind))
        if pitfalls:
            shown = pitfalls[:MAX_GUARD_PITFALLS]
            more = f"（另有 {len(pitfalls) - len(shown)} 条，检索时可见）" if len(pitfalls) > len(shown) else ""
            message += "\n该模块已知的排除项、风险和更正，改之前先对照" + more + "：\n" + "\n".join(self.memory_lines(shown))
        self.log("gate", module=module, file=rel, mode=mode, pitfalls=len(pitfalls) or None)
        return {"permission": "deny", "user_message": message, "agent_message": message}

    def on_pre_tool(self) -> dict:
        name = str(self.payload.get("tool_name") or "")
        args = tool_input(self.payload)
        if "record_memory" in name:
            return self._inject(args, with_draft=True)
        if "search_memory" in name:
            self._mark_searched(args, via="mcp")
            # Cursor 的 tool_name 不带服务名，别家记忆服务的同名工具可能拒收多出的参数
            if "pmem" in name.lower() or self.module_from_args(args):
                return self._inject(args, with_draft=False)
            return dict(ALLOW)
        if "memory_graph" in name:
            self._mark_searched(args, via="graph")
            return dict(ALLOW)
        if name.lower() == "shell":
            command = str(args.get("command") or "")
            # 先登记命令里的 pmem search，同一条命令里对已查模块的写入才放行；其他模块的写入照样检查
            self._note_cli_calls(command)
            base = args.get("cwd") or str(self.root)
            paths = [self.relative(t, base) for t in shell_write_targets(command, base)]
        elif name.lower() in WRITE_TOOLS:
            raw = args.get("file_paths") or [args.get("file_path") or args.get("path") or args.get("target_file") or ""]
            paths = [self.relative(str(p)) for p in raw]
        else:
            return dict(ALLOW)
        return next((v for v in map(self._guard, paths) if v is not None), dict(ALLOW))

    def _note_cli_calls(self, command: str) -> None:
        """终端里的 pmem search/graph/record 与 MCP 工具等价，照样登记。"""
        searches = cli_args(command, "search") + cli_args(command, "graph")
        records = cli_args(command, "record")
        for cli_search in searches:
            self._mark_searched(cli_search, via="cli")
        for cli_record in records:
            module = self.module_from_args(cli_record)
            if module and self.state is not None:
                self.state.add("cli_recorded", module)
                self.save()
            self.log("record_call", module=module, via="cli")

    def _inject(self, args: dict, with_draft: bool) -> dict:
        if not args or self.state is None:
            return dict(ALLOW)
        updated = dict(args)
        updated["source_conversation"] = self.conversation
        module = self.module_from_args({"module": args.get("module")}) if with_draft else None
        # 同一模块下的不同议题是不同的记忆，只有议题也相同时才覆盖本对话写过的草稿
        entity = self.registry.resolve_entity(module, str(args.get("entity") or "")) if module else None
        draft = self.state.data["written"].get(draft_key(module, entity)) if module else None
        if draft and not args.get("draft_id"):
            updated["draft_id"] = draft
        if module and not args.get("anchors"):
            files = [item.split("|", 1)[1] for item in self.state.data["edited_files"] if item.startswith(module + "|")]
            if files:
                updated["anchors"] = files[-MAX_AUTO_ANCHORS:]
        return {"permission": "allow", "updated_input": updated}

    def _mark_searched(self, args: dict, via: str) -> None:
        module = self.module_from_args(args)
        if module and self.state is not None:
            for key in ("searched", "consulted", "reviewed"):
                self.state.add(key, module)
            self.save()
        self.log("search_call", module=module, via=via)

    def on_before_mcp(self) -> dict:
        name = str(self.payload.get("tool_name") or "")
        if "search_memory" in name or "memory_graph" in name:
            self._mark_searched(tool_input(self.payload), via="mcp")
        return dict(ALLOW)

    def on_after_mcp(self) -> dict:
        name = str(self.payload.get("tool_name") or "")
        if self.state is None or not any(t in name for t in PMEM_TOOLS):
            return {}
        response = tool_response(self.payload)
        if not response or response.get("ok") is not True:
            return {}
        module = self.module_from_args({"module": response["module"]}) if response.get("module") else None
        rows = [r for key in ("items", "timeline") for r in response.get(key) or [] if isinstance(r, dict)]
        ids = [str(i) for i in dict.fromkeys([response.get("id"), *(r.get("id") for r in rows)])
               if i and re.fullmatch(_ULID, str(i))]
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
        """工具调用之后：读代码时附上该模块的记忆摘要；Claude Code / Codex 另由此处理 pmem 工具的返回与编辑过的文件。"""
        from pmem.hooks.agents import edited_files

        name = str(self.payload.get("tool_name") or "")
        if any(t in name for t in PMEM_TOOLS):
            return self.on_after_mcp()
        if name.lower() == "read":
            return self._read_digest(tool_input(self.payload))
        if name.lower() in SEARCH_TOOLS:
            return self._search_digest(tool_input(self.payload))
        for path in edited_files(self.payload):
            self._mark_edited(path)
        return {}

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
        return [m for m in self.state.data["edited"] if m not in written and not self.state.has("nudged", m)]

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
        return [m for m in self.state.data["consulted"] if not self.state.has("nudged", m)]

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
            return {}
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
        return {"followup_message": "\n".join(messages)}


HANDLERS = {
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
    return handler(Gate(Path(root), payload))
