from __future__ import annotations

import json
import os
import re
from pathlib import Path

from wcmatch import glob as wglob

from pmem.core.config import Config
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.hooks.payload import fuzzy_contains, tool_input
from pmem.hooks.state import SessionState
from pmem.metrics.events import log_event

WRITE_TOOLS = {"write", "strreplace", "edit", "multiedit", "editnotebook", "delete", "search_replace"}
_GLOB = wglob.GLOBSTAR | wglob.BRACE | wglob.DOTGLOB | wglob.FORCEUNIX | wglob.IGNORECASE
_NULL_TARGETS = {"$null", "/dev/null", "nul", "&1", "&2"}
_REDIRECT = re.compile(r"(?<![0-9&])>>?\s*([^\s|;&<>]+)")
_PS_WRITERS = {"set-content", "add-content", "out-file", "new-item", "clear-content", "remove-item", "ri", "sc", "ac"}
_RM = {"rm", "del", "erase", "rmdir", "rd"}
_ULID = r"[0-9A-HJKMNP-TV-Z]{26}"
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")
ALLOW = {"permission": "allow"}
MAX_AUTO_ANCHORS = 5


# ---- 终端命令里的写文件目标 ----

def _tokens(segment: str) -> list[str]:
    return [t.strip("'\"") for t in re.findall(r"'[^']*'|\"[^\"]*\"|\S+", segment)]


def shell_write_targets(command: str) -> list[str]:
    targets: list[str] = []
    for segment in re.split(r"\s*(?:\|\||&&|[;|])\s*", command or ""):
        targets += _REDIRECT.findall(segment)
        tokens = _tokens(segment)
        if not tokens:
            continue
        head, rest = tokens[0].lower(), tokens[1:]
        if head == "sed" and any(t.startswith("-i") for t in rest) and rest:
            targets.append(rest[-1])
        elif head == "tee" or head in _RM:
            targets += [t for t in rest if not t.startswith("-")]
        elif head in _PS_WRITERS:
            for i, token in enumerate(rest):
                if token.lower() in ("-path", "-filepath", "-literalpath") and i + 1 < len(rest):
                    targets.append(rest[i + 1])
                    break
            else:
                positional = [t for i, t in enumerate(rest) if not t.startswith("-") and (i == 0 or not rest[i - 1].startswith("-"))]
                targets += positional[:1]
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
    for segment in re.split(r"\s*(?:\|\||&&|[;|])\s*", command or ""):
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

    def memory_count(self, module: str) -> int:
        folder = self.config.entries_dir / module
        return sum(1 for _ in folder.glob("*.md")) if folder.is_dir() else 0

    def save(self) -> None:
        if self.state is not None:
            self.state.save()

    def log(self, event_type: str, **fields) -> None:
        log_event(self.config.cache_dir, event_type, conv=self.conversation or None, **fields)

    # 事件

    def on_prompt(self) -> dict:
        text = str(self.payload.get("prompt") or "")
        markers = self.config.get("gate.skip_markers") or []
        skip = any(fuzzy_contains(text, str(m)) for m in markers)
        analysis = any(
            fuzzy_contains(text.lower() if m.isascii() else text, m.lower() if m.isascii() else m)
            for m in (str(m) for m in self.config.get("gate.analysis_markers") or [])
        )
        if self.state is not None and (skip or analysis):
            self.state.data["skip"] = self.state.data["skip"] or skip
            self.state.data["analysis"] = self.state.data["analysis"] or analysis
            self.save()
        self.log("prompt", mode=self.payload.get("composer_mode"), skip=skip or None, analysis=analysis or None)
        return {"continue": True}

    def _guard(self, rel: str | None) -> dict | None:
        if rel is None:
            return None
        ignore = self.config.get("gate.ignore") or []
        watch = self.config.get("gate.watch") or []
        if any(wglob.globmatch(rel, p, flags=_GLOB) for p in ignore):
            return None
        if watch and not any(wglob.globmatch(rel, p, flags=_GLOB) for p in watch):
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
        retry = "然后重试本次修改" if mode == "warn" else "检索前不能修改该模块"
        # Cursor 只把 user_message 交给 Agent（实测），因此指引必须完整写在这里
        message = f"pmem：{rel} 属于 {module}（已有 {count} 条研发记忆）。请先调用 {call} 了解已有结论，{retry}。"
        self.log("gate", module=module, file=rel, mode=mode)
        return {"permission": "deny", "user_message": message, "agent_message": message}

    def on_pre_tool(self) -> dict:
        name = str(self.payload.get("tool_name") or "")
        args = tool_input(self.payload)
        if "record_memory" in name:
            return self._inject(args, with_draft=True)
        if "search_memory" in name:
            self._mark_searched(args, via="mcp")
            return self._inject(args, with_draft=False)
        if name.lower() == "shell":
            command = str(args.get("command") or "")
            searches, records = cli_args(command, "search"), cli_args(command, "record")
            for cli_search in searches:
                self._mark_searched(cli_search, via="cli")
            for cli_record in records:
                module = self.module_from_args(cli_record)
                if module and self.state is not None:
                    self.state.add("cli_recorded", module)
                    self.save()
                self.log("record_call", module=module, via="cli")
            if searches or records:
                return dict(ALLOW)
            base = args.get("cwd") or str(self.root)
            paths = [self.relative(t, base) for t in shell_write_targets(command)]
        elif name.lower() in WRITE_TOOLS:
            raw = args.get("file_path") or args.get("path") or args.get("target_file") or ""
            paths = [self.relative(str(raw))]
        else:
            return dict(ALLOW)
        for rel in paths:
            verdict = self._guard(rel)
            if verdict is not None:
                return verdict
        return dict(ALLOW)

    def _inject(self, args: dict, with_draft: bool) -> dict:
        if not args or self.state is None:
            return dict(ALLOW)
        updated = dict(args)
        updated["source_conversation"] = self.conversation
        module = self.module_from_args({"module": args.get("module")}) if with_draft else None
        draft = self.state.data["written"].get(module) if module else None
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
            self.state.add("searched", module)
            self.state.add("consulted", module)
            self.save()
        self.log("search_call", module=module, via=via)

    def on_before_mcp(self) -> dict:
        if "search_memory" in str(self.payload.get("tool_name") or ""):
            self._mark_searched(tool_input(self.payload), via="mcp")
        return dict(ALLOW)

    def on_after_mcp(self) -> dict:
        name = str(self.payload.get("tool_name") or "")
        if self.state is None or not any(t in name for t in ("record_memory", "search_memory")):
            return {}
        blob = json.dumps(self.payload, ensure_ascii=False)
        if not re.search(r'\\*"ok\\*"\s*:\s*true', blob):
            return {}
        module_match = re.search(r'\\*"module\\*"\s*:\s*\\*"([A-Za-z0-9_.]+)', blob)
        module = module_match.group(1) if module_match else None
        ids = list(dict.fromkeys(re.findall(r'\\*"id\\*"\s*:\s*\\*"(' + _ULID + ")", blob)))
        if "record_memory" in name:
            if module and ids:
                self.state.data["written"][module] = ids[0]
                self.state.add("recorded", ids[0])
            self.log("mcp_record", module=module, ids=ids[:1])
        else:
            if module:
                self.state.add("searched", module)
                self.state.add("consulted", module)
            for mid in ids:
                self.state.add("returned", mid)
            self.log("mcp_search", module=module, ids=ids)
        self.save()
        return {}

    def on_edited(self) -> dict:
        rel = self.relative(str(self.payload.get("file_path") or ""))
        module = self.module_of(rel)
        if module and self.state is not None:
            self.state.add("edited", module)
            self.state.add("edited_files", f"{module}|{rel}")
            self.save()
        if rel is not None:
            self.log("edit", module=module, file=rel)
        return {}

    def on_compact(self) -> dict:
        if self.state is not None:
            self.state.data["searched"] = []
            self.state.data["warned"] = []
            self.save()
        return {}

    def _written(self) -> set[str]:
        return set(self.state.data["written"]) | set(self.state.data["cli_recorded"])

    def _pending_nudges(self, status) -> list[str]:
        if status not in (None, "completed") or self.state.data["skip"]:
            return []
        if not self.config.get("gate.stop_reminder", True) or self.config.get("gate.mode") == "off":
            return []
        written = self._written()
        return [m for m in self.state.data["edited"] if m not in written and not self.state.has("nudged", m)]

    def _analyzed(self, status) -> list[str]:
        """排查类对话里查过记忆、但既没改代码也没写记忆的模块。"""
        if status not in (None, "completed") or self.state.data["skip"] or not self.state.data["analysis"]:
            return []
        done = self._written() | set(self.state.data["edited"])
        return [m for m in self.state.data["consulted"] if m not in done]

    def on_stop(self) -> dict:
        if self.state is None:
            return {}
        self.state.cleanup_old()
        status = self.payload.get("status")
        pending = self._pending_nudges(status)
        analyzed = self._analyzed(status)
        remind_analysis = self.config.get("gate.analysis_reminder") and self.config.get("gate.mode") != "off"
        analysis_pending = [m for m in analyzed if not self.state.has("nudged", m)] if remind_analysis else []
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
            nudged=(pending + analysis_pending) or None,
            **usage,
        )
        if not pending and not analysis_pending:
            return {}
        for module in pending + analysis_pending:
            self.state.add("nudged", module)
        self.save()
        parts = []
        if pending:
            parts.append(f"本轮修改了 {'、'.join(pending)}，但还没有写研发记忆")
        if analysis_pending:
            parts.append(f"本轮排查了 {'、'.join(analysis_pending)}，没有改代码也没有写记忆")
        return {
            "followup_message": (
                f"[pmem] {'；'.join(parts)}。如果得出了值得留给后人的结论"
                "（根因、排除过的方向、做出的决定、潜在风险），请用 record_memory 各记一条；"
                "只是机械改动或查阅、没有新结论的话，回复“无需记录”即可。"
            )
        }


HANDLERS = {
    "prompt": Gate.on_prompt,
    "pre-tool": Gate.on_pre_tool,
    "before-mcp": Gate.on_before_mcp,
    "after-mcp": Gate.on_after_mcp,
    "edited": Gate.on_edited,
    "compact": Gate.on_compact,
    "stop": Gate.on_stop,
}


def handle(event: str, payload: dict, root: Path) -> dict:
    handler = HANDLERS.get(event)
    if handler is None:
        return {}
    return handler(Gate(Path(root), payload))
