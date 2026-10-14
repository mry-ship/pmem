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

WRITE_TOOLS = {"write", "strreplace", "edit", "multiedit", "editnotebook", "delete", "search_replace"}
_GLOB = wglob.GLOBSTAR | wglob.BRACE | wglob.DOTGLOB | wglob.FORCEUNIX | wglob.IGNORECASE
_NULL_TARGETS = {"$null", "/dev/null", "nul", "&1", "&2"}
_REDIRECT = re.compile(r"(?<![0-9&])>>?\s*([^\s|;&<>]+)")
_PS_WRITERS = {"set-content", "add-content", "out-file", "new-item", "clear-content", "remove-item", "ri", "sc", "ac"}
_RM = {"rm", "del", "erase", "rmdir", "rd"}
_ULID = r"[0-9A-HJKMNP-TV-Z]{26}"
ALLOW = {"permission": "allow"}


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

    # 事件

    def on_prompt(self) -> dict:
        text = str(self.payload.get("prompt") or "")
        markers = self.config.get("gate.skip_markers") or []
        if self.state is not None and any(fuzzy_contains(text, str(m)) for m in markers):
            self.state.data["skip"] = True
            self.save()
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
        retry = "检索后重试本操作即可。" if mode == "warn" else "检索前无法修改该模块的文件。"
        return {
            "permission": "deny",
            "user_message": f"pmem：修改 {module} 前先检索记忆",
            "agent_message": (
                f"[pmem] 你要修改的 {rel} 属于模块 {module}，该模块有 {count} 条研发记忆，"
                f"请先调用 {call} 了解已有的根因、排除项与决定，再继续修改。{retry}"
                "（用户说跳过记忆时可忽略。）"
            ),
        }

    def on_pre_tool(self) -> dict:
        name = str(self.payload.get("tool_name") or "")
        args = tool_input(self.payload)
        if "record_memory" in name:
            return self._inject(args)
        if "search_memory" in name:
            self._mark_searched(args)
            return dict(ALLOW)
        if name.lower() == "shell":
            base = args.get("cwd") or str(self.root)
            paths = [self.relative(t, base) for t in shell_write_targets(str(args.get("command") or ""))]
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

    def _inject(self, args: dict) -> dict:
        if not args or self.state is None:
            return dict(ALLOW)
        updated = dict(args)
        updated["source_conversation"] = self.conversation
        module = self.module_from_args({"module": args.get("module")})
        draft = self.state.data["written"].get(module) if module else None
        if draft and not args.get("draft_id"):
            updated["draft_id"] = draft
        return {"permission": "allow", "updated_input": updated}

    def _mark_searched(self, args: dict) -> None:
        module = self.module_from_args(args)
        if module and self.state is not None:
            self.state.add("searched", module)
            self.save()

    def on_before_mcp(self) -> dict:
        if "search_memory" in str(self.payload.get("tool_name") or ""):
            self._mark_searched(tool_input(self.payload))
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
        if "record_memory" in name:
            id_match = re.search(r'\\*"id\\*"\s*:\s*\\*"(' + _ULID + ")", blob)
            if module and id_match:
                self.state.data["written"][module] = id_match.group(1)
        elif module:
            self.state.add("searched", module)
        self.save()
        return {}

    def on_edited(self) -> dict:
        module = self.module_of(self.relative(str(self.payload.get("file_path") or "")))
        if module and self.state is not None:
            self.state.add("edited", module)
            self.save()
        return {}

    def on_compact(self) -> dict:
        if self.state is not None:
            self.state.data["searched"] = []
            self.state.data["warned"] = []
            self.save()
        return {}

    def on_stop(self) -> dict:
        if self.state is None:
            return {}
        self.state.cleanup_old()
        status = self.payload.get("status")
        if status not in (None, "completed") or self.state.data["skip"]:
            return {}
        if not self.config.get("gate.stop_reminder", True) or self.config.get("gate.mode") == "off":
            return {}
        written = self.state.data["written"]
        pending = [m for m in self.state.data["edited"] if m not in written and not self.state.has("nudged", m)]
        if not pending:
            return {}
        for module in pending:
            self.state.add("nudged", module)
        self.save()
        names = "、".join(pending)
        return {
            "followup_message": (
                f"[pmem] 本轮修改了 {names}，但还没有写研发记忆。如果得出了值得留给后人的结论"
                "（根因、排除过的方向、做出的决定、潜在风险），请用 record_memory 各记一条；"
                "只是机械改动、没有新结论的话，回复“无需记录”即可。"
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
