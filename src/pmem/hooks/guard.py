"""改代码前的闸门：目标文件所属模块有记忆却没查过时拦截或提醒。"""

from __future__ import annotations

import glob
import json
import re

from pmem.core.entry import PITFALL_KINDS
from pmem.hooks.memories import DIGEST_MATERIAL
from pmem.hooks.payload import tool_paths, transcript_records
from pmem.hooks.shell import WILDCARD_PATH
from pmem.hooks.types import GateAttrs
from pmem.index.graph import current_entries, file_features

MAX_GUARD_PITFALLS = 5
MAX_GLOB_TARGETS = 200
_SPEC_BODY = ("策划设计.md", "美术设计.md", "程序设计.md", "模块现状.md")
_SPEC_REQUIRED = ("程序设计.md", "模块现状.md")
# 整行才算还没写完；正文里用反引号提到这个字面量不算空骨架
_SPEC_EMPTY_LINE = re.compile(r"(?m)^[ \t]*<!-- spec:empty -->[ \t]*\r?$")
# 摘录只带这些契约节。前面的所有权和入口不代替闭集、原文和失败条件。
_CONTRACT_HEADINGS = ("会话字段闭集", "入参字段闭集", "出参字段闭集", "原文（须按字面抄）", "失败条件", "必须保持")
# 骨架栏目。不在这张表里、又不是 Markdown 标题的句子，即使以冒号结尾也仍是正文。
# 与 spec_closed 的同名常量保持一致。
_SECTION_TITLES = (
    "入口", "入参字段闭集", "出参字段闭集", "原文（须按字面抄）", "必须保持",
    "会话字段闭集", "数据形状与闭集词表", "所有权", "决定表", "失败条件",
    "配置与环境变量", "关键流程", "生成物", "一轮例子", "单独拿走时还要带走的依赖规格",
)
# 与 spec_closed._line_heading 同一规则：已知标题切换，骨架栏目或 Markdown 标题结束当前节。
_ATX = re.compile(r"^#{1,6}\s+(\S.*?)\s*$")


def read_failed(payload: dict | None) -> bool:
    """这次查看有没有明确的失败。Cursor 的失败走 postToolUseFailure，不进 post-tool；
    顶层 is_error，或 error_message、failure_type，或 tool_response/tool_output 里的 is_error，都不能记成已读。"""
    if not isinstance(payload, dict):
        return False
    if payload.get("failure_type") or payload.get("is_error") is True:
        return True
    message = payload.get("error_message")
    if isinstance(message, str) and message.strip():
        return True
    if "failure" in str(payload.get("hook_event_name") or "").lower():
        return True
    for key in ("tool_response", "tool_output"):
        value = payload.get(key)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                continue
        if isinstance(value, dict) and value.get("is_error") is True:
            return True
    return False


def _result_id(block: dict) -> str:
    for key in ("tool_use_id", "id"):
        value = block.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _result_failed(block: dict) -> bool:
    if block.get("is_error") is True:
        return True
    error = block.get("error")
    return isinstance(error, str) and bool(error.strip())


def _split_title(body: str) -> tuple[str, str]:
    for mark in ("：", ":"):
        if mark in body:
            title, rest = body.split(mark, 1)
            return title.strip(), rest.strip()
    return body.strip(), ""


def _line_heading(line: str, names: tuple[str, ...]) -> tuple[str, str] | None:
    """已知标题返回 (名称, 同一行剩余)。未知栏目返回 ("", "")。普通正文返回 None。

    标题可以独占一行，也可以和第一句写在同一行。第一句仍进摘录。
    未知栏目只包括 Markdown 标题，以及骨架里的其他栏目。
    原文里单独成行、以冒号结尾的句子不是栏目，仍留在当前节。
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("<!--"):
        return None
    atx = _ATX.match(stripped)
    title, rest = _split_title(atx.group(1).strip() if atx else stripped)
    if title in names:
        return title, rest
    if atx or title in _SECTION_TITLES:
        return "", ""
    return None


def _contract_text(text: str) -> str:
    """摘录契约各节的全文。没有这些标题时附上整份正文，避免只看到开头。"""
    current: str | None = None
    buckets: dict[str, list[str]] = {name: [] for name in _CONTRACT_HEADINGS}
    for line in text.splitlines():
        found = _line_heading(line, _CONTRACT_HEADINGS)
        if found is not None:
            name, rest = found
            current = name or None
            if current and rest:
                buckets[current].append(rest)
            continue
        if current:
            buckets[current].append(line)
    parts = []
    for name in _CONTRACT_HEADINGS:
        body = "\n".join(buckets[name]).strip()
        if body:
            parts.append(f"{name}：\n{body}")
    return "\n\n".join(parts) if parts else text.strip()


def _successful_read_args(records: list) -> list[dict]:
    """对话记录里已经成功返回的 Read。没有配对结果，或结果标了失败，都不算。"""
    uses: list[dict] = []
    failed: dict[str, bool] = {}
    for _role, content in records:
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                name = str(block.get("name") or "").lower()
                if name == "read" and isinstance(block.get("input"), dict):
                    uses.append(block)
                continue
            if block.get("type") != "tool_result":
                continue
            tid = _result_id(block)
            if not tid:
                continue
            this = _result_failed(block)
            # 同一条 Read 只要有一条结果失败，就不算已读。
            failed[tid] = this if tid not in failed else failed[tid] or this
    args = []
    for block in uses:
        tid = block.get("id") if isinstance(block.get("id"), str) else ""
        if not tid:
            tid = block.get("tool_use_id") if isinstance(block.get("tool_use_id"), str) else ""
        if tid and failed.get(tid) is False:
            args.append(block["input"])
    return args


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
        if mode == "off" or self.state is None:
            return None
        if self.state.has("searched", module):
            return None
        if self.state.data["skip"]:
            return self._gate_pass(rel, module, "skip")
        count = self.memory_count(module)
        # 子模块自己还没有记忆、上级模块有教训时照样要先查：查子模块会带上上级的教训
        _, upper = self.ancestor_pitfalls(module)
        if count == 0 and upper == 0:
            return self._gate_pass(rel, module, "no_memory")
        if mode == "warn":
            if self.state.has("warned", module):
                return self._gate_pass(rel, module, "warned")
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
        self.log("gate", module=module, file=rel, mode=mode, pitfalls=total or None, tool=self._tool_use_id())
        return {"permission": "deny", "user_message": message, "agent_message": message}

    def _tool_use_id(self) -> str | None:
        """宿主给 preToolUse 的工具调用 id；afterFileEdit 没有它，所以闸门的判定要在这里留下，才能和哪次调用对上。"""
        value = self.payload.get("tool_use_id")
        return value if isinstance(value, str) and value else None

    def _gate_pass(self, rel: str, module: str, reason: str) -> None:
        """模块还没查过却放行：记下原因，report 才能区分“没记忆/已提醒过/用户跳过”和真正漏过。"""
        self.log("gate_pass", module=module, file=rel, reason=reason, tool=self._tool_use_id())

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
        return bool(self.config.get("spec.read_before_edit", False))

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

    def _mark_spec_path(self, raw: str) -> bool:
        """只认某一份规格正文。打开目录、通配或其他文件名都不算读过。"""
        rel = self.relative(str(raw))
        if not rel:
            return False
        rel = rel.replace("\\", "/").rstrip("/")
        prefix = self._spec_root() + "/"
        if not rel.startswith(prefix):
            return False
        module, _, filename = rel[len(prefix):].partition("/")
        if not module or "/" in filename or filename not in _SPEC_BODY:
            return False
        full = f"{prefix}{module}/{filename}"
        if self.state.has("spec_read", full):
            return False
        self.state.add("spec_read", full)
        return True

    def _note_spec_reads(self, args: dict, tool: str = "") -> None:
        """本对话用 Read 成功打开过的规格正文记下来，改代码前不用再拦。
        Grep、Glob、语义搜索只看到片段或文件名，打开目录也不等于读过其中的正文。"""
        if not self._spec_reads_on() or not isinstance(args, dict) or str(tool).lower() != "read":
            return
        changed = False
        for raw in tool_paths(args):
            changed = self._mark_spec_path(raw) or changed
        if changed:
            self.save()

    def _harvest_spec_reads(self) -> None:
        """post-tool 没覆盖 Read 时（quiet、Codex），从对话记录里补上已经成功返回的 Read。
        只有 tool_use、没有对应成功结果的不算。当前这次工具多半是写入，不能把它的路径当成读过规格。"""
        if not self._spec_reads_on():
            return
        payload = getattr(self, "payload", None) or {}
        path = payload.get("transcript_path") if isinstance(payload, dict) else None
        for args in _successful_read_args(transcript_records(path) or []):
            self._note_spec_reads(args, tool="read")

    def _spec_excerpt(self, rel: str) -> str:
        text = _contract_text(self._spec_text(rel) or "")
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
        message = (
            f"pmem：修改 {rel}（{module}）之前，请先阅读相关规格：{files}。请阅读后重试；若环境看不到 Read，摘录给过后再改会放行。\n{excerpt}"
        )
        for path in pending:
            self.state.add("spec_offered", path)
        self.save()
        self.log("spec_read", module=module, file=rel, mode=mode)
        return {"permission": "deny", "user_message": message, "agent_message": message}
