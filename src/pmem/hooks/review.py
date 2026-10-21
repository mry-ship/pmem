"""提问审查：读代码、搜索、提问提到模块时附上该模块的记忆摘要。"""

from __future__ import annotations

from pmem.hooks.payload import last_user_text, tool_paths, turn_tool_paths
from pmem.index.graph import current_entries, digest

VIEW_TOOLS = {"read", "grep", "glob", "semanticsearch", "codebase_search"}
SEARCH_TOOLS = VIEW_TOOLS - {"read"}
MAX_SEARCH_DIGESTS = 2
MAX_REVIEW_MODULES = 3


class Review:
    # 提问审查：让 Agent 在回答、修改之前看到相关模块的记忆

    def _reviews_on(self, setting: str) -> bool:
        return self.state is not None and not self.state.data["skip"] and self._reminders_on(setting, True)

    def _offer_digest(self, module: str, intro: str, rel: str | None = None) -> str | None:
        """本对话还没看过该模块的记忆时，给出现行记忆摘要并记为已看过；rel 是正在看的文件，相关记忆优先。"""
        if self.state is None or self.state.has("reviewed", module):
            return None
        entries = self.module_entries(module)
        picked = digest(entries, path=rel)
        inherited, _ = self.ancestor_pitfalls(module)
        picked += [e for e in inherited if e.id not in {p.id for p in picked}]
        project = self.take_project_pitfalls(module)
        if not picked and not project:
            return None
        if picked:
            self.state.add("reviewed", module)
        self.save()
        self.log("digest", module=module, ids=[e.id for e in picked], project=[e.id for e in project] or None)
        if picked:
            upper = "（含上级模块的坑）" if inherited else ""
            intro_line = (f"[pmem] {intro}，现行记忆 {len(current_entries(entries))} 条{upper}，回答或修改前先看"
                          f"（只列标题，全文用 search_memory(module=\"{module}\", query=...)）：")
        elif current_entries(entries):
            intro_line = (f"[pmem] {intro}，该模块只有和这个文件无关的功能记录"
                          f"（要看用 search_memory(module=\"{module}\")）。改动前先看全项目通用的坑：")
        else:
            intro_line = f"[pmem] {intro}，该模块还没有记忆。改动前先看全项目通用的坑："
        return "\n".join([intro_line, *self.lines_with_project(picked, project, own=module)])

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
        # 先挑出要给的模块再生成摘要：生成即记为“已看过”，生成了又丢掉的模块本对话就再也看不到摘要
        messages: list[str] = []
        for module, rel in found.items():
            if len(messages) >= MAX_SEARCH_DIGESTS:
                break
            message = self._offer_digest(module, f"你正在搜索的 {rel} 属于 {module}", rel)
            if message:
                messages.append(message)
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
