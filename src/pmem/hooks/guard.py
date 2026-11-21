"""改代码前的闸门：目标文件所属模块有记忆却没查过时拦截或提醒。"""

from __future__ import annotations

import glob
import re
from pathlib import Path

from pmem.core.entry import PITFALL_KINDS
from pmem.hooks.memories import DIGEST_MATERIAL
from pmem.hooks.payload import _transcript_tail, tool_paths
from pmem.hooks.review import VIEW_TOOLS
from pmem.hooks.shell import WILDCARD_PATH
from pmem.hooks.types import GateAttrs
from pmem.index.graph import current_entries, file_features

MAX_GUARD_PITFALLS = 5
MAX_GLOB_TARGETS = 200
_SPEC_BODY = ("策划设计.md", "美术设计.md", "程序设计.md", "模块现状.md")
_SPEC_REQUIRED = ("程序设计.md", "模块现状.md")
# 整行才算还没写完；正文里用反引号提到这个字面量不算空骨架
_SPEC_EMPTY_LINE = re.compile(r"(?m)^[ \t]*<!-- spec:empty -->[ \t]*\r?$")
_SPEC_EXCERPT = 800


class Guard(GateAttrs):
    def _expand_target(self, rel: str | None) -> list[str | None]:
        """通配符按实际文件展开。方括号还可能是字面路径，展开之后仍保留原路径。"""
        if rel is None:
            return []
        if WILDCARD_PATH.search(rel) and not (self.root / rel).exists():
            matches = glob.glob(rel, root_dir=self.root, recursive=True)[:MAX_GLOB_TARGETS]
            if matches or re.search(r"[*?]", rel):
                expanded = [m.replace("\\", "/") for m in matches]
                if "[" not in rel.replace("\\", "/"):
                    return expanded
                return [*expanded, rel]
        return [rel]

    def _guard(self, rel: str | None, searched_here: set[str] = frozenset()) -> dict | None:
        return self._guard_targets([(item, searched_here) for item in self._expand_target(rel)])

    def _guard_path(self, rel: str | None, searched_here: set[str]) -> dict | None:
        return self._guard_targets([(rel, searched_here)])

    def _guard_many(self, rels: list[str | None], searched_here: set[str]) -> dict | None:
        return self._guard_targets([(rel, searched_here) for rel in rels])

    def _guard_targets(self, pairs: list[tuple[str | None, set[str]]]) -> dict | None:
        """先把所有目标上没查过的记忆拦完，再拦规格。避免前面的规格提示盖住后面的记忆闸门。"""
        watched = [(rel, searched) for rel, searched in pairs if rel is not None and self._watched(rel)]
        for rel, searched in watched:
            for module in self._target_modules(rel):
                if module not in searched:
                    denied = self._guard_module(rel, module)
                    if denied is not None:
                        return denied
        self._harvest_spec_reads()
        for rel, _searched in watched:
            for module in self._target_modules(rel):
                denied = self._guard_spec(rel, module)
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
        # 子模块自己还没有记忆、上级模块有教训时照样要先查：查子模块会带上上级的教训
        _, upper = self.ancestor_pitfalls(module)
        if count == 0 and upper == 0:
            return None
        if mode == "warn":
            if self.state.has("warned", module):
                return None
            self.state.add("warned", module)
            self.save()
        call = f'search_memory(module="{module}", path="{rel}")'
        # Cursor 只把 user_message 交给 Agent（实测），因此指引必须完整写在这里
        held = f"已有 {count} 条研发记忆" + (f"，上级模块另有 {upper} 条教训" if upper else "")
        message = f"pmem：{rel} 属于 {module}（{held}）。请先调用 {call} 了解已有结论，"
        if mode == "warn":
            message += "然后重试本次修改。"
        else:
            message += (
                f"查过之后才能修改该模块。MCP 工具不可用时，在终端运行 "
                f"pmem search --module {module} --path {rel} 也算"
                "（输出不能丢弃，如 > $null、| Out-Null）；检索要真正返回结果才算查过。"
                "确实不需要记忆时，请用户回复“跳过记忆”。"
            )
        text, total = self._pitfalls(module, rel)
        message += text
        self.log("gate", module=module, file=rel, mode=mode, pitfalls=total or None)
        return {"permission": "deny", "user_message": message, "agent_message": message}

    def _pitfalls(self, module: str, rel: str | None = None) -> tuple[str, int]:
        """检索按关键词排序，可能漏掉与这次修改相关的坑；排除项、风险、更正直接列出来，按这个顺序。
        锚点就是要改的文件的功能记录也列出来：改回用户要求的行为最常发生在这里。"""
        entries = self.module_entries(module)
        hidden = self.replaced_ids()
        pitfalls = sorted((e for e in current_entries(entries, hidden) if e.kind in PITFALL_KINDS),
                          key=lambda e: (e.enforced, PITFALL_KINDS.index(e.kind)))
        shown = pitfalls[:MAX_GUARD_PITFALLS]
        inherited, _ = self.ancestor_pitfalls(module)
        features = file_features(entries, rel, replaced=hidden) if rel else []
        project = self.take_project_pitfalls(module, skip={e.id for e in [*shown, *inherited]})
        if not shown and not inherited and not project and not features:
            return "", 0
        self.save()
        text = ""
        if shown or inherited or project:
            more = f"（另有 {len(pitfalls) - len(shown)} 条，检索时可见）" if len(pitfalls) > len(shown) else ""
            head = ("\n该模块已知的排除项、风险和更正，改之前先对照下列资料" + more + "：\n"
                    if shown or inherited else "\n")
            text = head + "\n".join(self.lines_with_project([*shown, *inherited], project, own=module))
        if features:
            text += ("\n这个文件上的功能记录（用户要求、必须保持的行为；资料，改动不要无故改回去）：\n"
                     + DIGEST_MATERIAL + "\n"
                     + "\n".join(self.memory_lines(features)))
        return text, len(pitfalls)

    def _spec_reads_on(self) -> bool:
        if self.state is None or self.state.data.get("skip"):
            return False
        if self.config.get("gate.mode") == "off":
            return False
        return bool(self.config.get("spec.read_before_edit", True))

    def _spec_root(self) -> str:
        return str(self.config.get("spec.dir") or ".memory/specs").replace("\\", "/").strip("/")

    def _spec_text(self, rel: str) -> str | None:
        """读规格正文。指向项目内的符号链接照读；指出项目外的不读。"""
        try:
            resolved = (self.root / rel).resolve()
            if not resolved.is_relative_to(self.root.resolve()) or not resolved.is_file():
                return None
            return resolved.read_text(encoding="utf-8-sig")
        except OSError:
            return None

    def _specs_to_read(self, module: str) -> list[str]:
        """已写完的程序设计和模块现状。空骨架或不存在的不要求读。"""
        base = self._spec_root()
        required = []
        for name in _SPEC_REQUIRED:
            rel = f"{base}/{module}/{name}"
            text = self._spec_text(rel)
            if text is None or _SPEC_EMPTY_LINE.search(text):
                continue
            required.append(rel)
        return required

    def _spec_paths_named_in(self, text: str) -> list[str]:
        """从 Glob 模式里认出规格目录或某一份正文。扫整个仓库的 **/* 对不上前缀，不算读过。"""
        folded = text.replace("\\", "/")
        prefix = self._spec_root() + "/"
        found: list[str] = []
        start = 0
        while True:
            at = folded.find(prefix, start)
            if at < 0:
                break
            rest = folded[at + len(prefix):]
            module = rest.split("/", 1)[0].split("*", 1)[0].strip()
            tail = rest[len(module):].lstrip("/") if module else ""
            filename = tail.split("*", 1)[0].strip("/")
            if module and "*" not in module and "/" not in module:
                found.append(f"{prefix}{module}/{filename}" if filename in _SPEC_BODY else f"{prefix}{module}")
            start = at + len(prefix)
        return found

    def _mark_spec_path(self, raw: str) -> bool:
        rel = self.relative(str(raw))
        if not rel:
            return False
        rel = rel.replace("\\", "/").rstrip("/")
        prefix = self._spec_root() + "/"
        if not rel.startswith(prefix):
            return False
        module, _, filename = rel[len(prefix):].partition("/")
        if not module or "/" in filename:
            return False
        names = [filename] if filename in _SPEC_BODY else (list(_SPEC_BODY) if not filename else [])
        changed = False
        for name in names:
            full = f"{prefix}{module}/{name}"
            if not filename and self._spec_text(full) is None:
                continue
            if not self.state.has("spec_read", full):
                self.state.add("spec_read", full)
                changed = True
        return changed

    def _note_spec_reads(self, args: dict, tool: str = "") -> None:
        """本对话打开过的规格正文记下来，改代码前不用再拦。
        Grep 的 pattern 是搜索词，不能当成规格路径；只有 Glob 的 pattern 才算。"""
        if not self._spec_reads_on() or not isinstance(args, dict):
            return
        raws = list(tool_paths(args))
        pattern = args.get("glob_pattern") or args.get("glob")
        if "glob" in tool.lower() and not isinstance(pattern, str):
            pattern = args.get("pattern") if isinstance(args.get("pattern"), str) else None
        target = args.get("target_directory") if isinstance(args.get("target_directory"), str) else ""
        if isinstance(pattern, str) and pattern:
            if target:
                raws.append(target)
                name = pattern.replace("\\", "/").rstrip("/").split("/")[-1]
                if name in _SPEC_BODY:
                    raws.append(str(Path(target) / name))
            raws.extend(self._spec_paths_named_in("/".join(part for part in (target, pattern) if part)))
        changed = False
        for raw in raws:
            changed = self._mark_spec_path(raw) or changed
        if changed:
            self.save()

    def _harvest_spec_reads(self) -> None:
        """post-tool 没覆盖 Read 时（quiet、Codex），从对话记录里补上已经出现的读取。
        当前这次工具多半是写入，不能把它的路径当成读过规格。"""
        if not self._spec_reads_on():
            return
        payload = getattr(self, "payload", None) or {}
        for _role, content in _transcript_tail(payload.get("transcript_path") if isinstance(payload, dict) else None) or []:
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = str(block.get("name") or "").lower()
                if name not in VIEW_TOOLS or not isinstance(block.get("input"), dict):
                    continue
                self._note_spec_reads(block["input"], tool=name)

    def _spec_excerpt(self, rel: str) -> str:
        text = (self._spec_text(rel) or "").strip()
        if len(text) > _SPEC_EXCERPT:
            text = text[:_SPEC_EXCERPT] + "…"
        return f"{rel}：\n{text}" if text else rel

    def _guard_spec(self, rel: str, module: str) -> dict | None:
        if not self._spec_reads_on():
            return None
        pending = [path for path in self._specs_to_read(module) if not self.state.has("spec_read", path)]
        if not pending:
            return None
        mode = self.config.get("gate.mode")
        if mode == "warn":
            if self.state.has("spec_warned", module):
                return None
            self.state.add("spec_warned", module)
            self.save()
        elif mode != "block":
            return None
        else:
            # Cursor 对话记录不含工具调用，quiet / Codex 的 Hook 也看不到 Read。
            # 本对话还没记到过任何一次读取时，摘录已经给过就放行，避免一直拦。
            # 一旦记到过读取，没读完的文件继续拦。
            offered = [path for path in pending if self.state.has("spec_offered", path)]
            if offered and not self.state.data.get("spec_read") and len(offered) == len(pending):
                return None
        files = "、".join(pending)
        excerpt = "\n".join(self._spec_excerpt(path) for path in pending)
        message = (f"pmem：修改 {rel}（{module}）之前，请先阅读相关规格：{files}。读完再重试本次修改。\n"
                   f"{excerpt}")
        for path in pending:
            self.state.add("spec_offered", path)
        self.save()
        self.log("spec_read", module=module, file=rel, mode=mode)
        return {"permission": "deny", "user_message": message, "agent_message": message}
