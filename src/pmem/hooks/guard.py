"""改代码前的闸门：目标文件所属模块有记忆却没查过时拦截或提醒。"""

from __future__ import annotations

import glob
import re

from pmem.core.entry import PITFALL_KINDS
from pmem.hooks.shell import WILDCARD_PATH
from pmem.index.graph import current_entries, file_features

MAX_GUARD_PITFALLS = 5
MAX_GLOB_TARGETS = 200


class Guard:
    def _guard(self, rel: str | None, searched_here: set[str] = frozenset()) -> dict | None:
        """终端命令的写入目标。编辑工具给的是字面路径，直接用 _guard_path。"""
        if rel is not None and WILDCARD_PATH.search(rel) and not (self.root / rel).exists():
            # rm -rf src/* 这类通配符目标按实际展开出的文件和目录逐个检查；展开结果不再二次展开
            matches = glob.glob(rel, root_dir=self.root, recursive=True)[:MAX_GLOB_TARGETS]
            # app/[id]/page.tsx 这类路径里的方括号多半是字面字符（Next.js 动态路由），展开不出东西时按字面检查
            if matches or re.search(r"[*?]", rel):
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
        # 子模块自己还没有记忆、上级模块有教训时照样要先查：查子模块会带上上级的教训
        _, upper = self.ancestor_pitfalls(module)
        if count == 0 and upper == 0:
            return None
        if mode == "warn":
            if self.state.has("warned", module):
                return None
            self.state.add("warned", module)
            self.save()
        call = f'search_memory(module="{module}")'
        # Cursor 只把 user_message 交给 Agent（实测），因此指引必须完整写在这里
        held = f"已有 {count} 条研发记忆" + (f"，上级模块另有 {upper} 条教训" if upper else "")
        message = f"pmem：{rel} 属于 {module}（{held}）。请先调用 {call} 了解已有结论，"
        if mode == "warn":
            message += "然后重试本次修改。"
        else:
            message += (
                f"查过之后才能修改该模块。MCP 工具不可用时，在终端运行 pmem search --module {module} 也算"
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
        pitfalls = sorted((e for e in current_entries(entries) if e.kind in PITFALL_KINDS),
                          key=lambda e: PITFALL_KINDS.index(e.kind))
        shown = pitfalls[:MAX_GUARD_PITFALLS]
        inherited, _ = self.ancestor_pitfalls(module)
        features = file_features(entries, rel) if rel else []
        project = self.take_project_pitfalls(module, skip={e.id for e in [*shown, *inherited]})
        if not shown and not inherited and not project and not features:
            return "", 0
        self.save()
        text = ""
        if shown or inherited or project:
            more = f"（另有 {len(pitfalls) - len(shown)} 条，检索时可见）" if len(pitfalls) > len(shown) else ""
            head = "\n该模块已知的排除项、风险和更正，改之前先对照" + more + "：\n" if shown or inherited else "\n"
            text = head + "\n".join(self.lines_with_project([*shown, *inherited], project, own=module))
        if features:
            text += ("\n这个文件上的功能记录（用户要求、必须保持的行为），改动不要把它们改回去：\n"
                     + "\n".join(self.memory_lines(features)))
        return text, len(pitfalls)
