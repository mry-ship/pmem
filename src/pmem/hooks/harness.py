"""harness 实验（harness.mode）：改前给版本历史算出的提示（经 search_memory 的 context 节），
回合结束做漏改与未验证检查；无记忆模块第一次改文件后给轻提示，请 AI 带 path 查一次。

提示只读 pmem.context 的缓存（后台预先算好），Hook 里不碰版本库。
"""
from __future__ import annotations

from pmem import context

MAX_RAN = 30


class Harness:
    def _harness_mode(self) -> str:
        if self.state is None or self.state.data["skip"] or self.config.get("gate.mode") == "off":
            return "off"
        return str(self.config.get("harness.mode") or "off")

    def _edited_rels(self) -> set[str]:
        return {item.partition("|")[2] for item in self.state.data["edited_files"] if "|" in item}

    def note_command(self, command: str) -> None:
        """记下本对话跑过的终端命令（只留前 200 个字符），回合结束时核对有没有跑验证命令。"""
        if self.state is None or self._harness_mode() != "check" or not command.strip():
            return
        ran = self.state.data["ran"]
        ran.append(command.strip()[:200])
        del ran[:-MAX_RAN]
        self.save()

    def empty_context_tip(self, rel: str | None, module: str | None) -> str | None:
        """无记忆模块第一次改完文件后：放行后的轻提示，请带 path 查一次以便附上 context。
        preToolUse 放行无法附加上下文（Cursor/Claude/Codex 皆然），所以挂在 postToolUse。"""
        if self._harness_mode() == "off" or not rel or not module or self.state is None:
            return None
        if self.memory_count(module):
            return None
        _, upper = self.ancestor_pitfalls(module)
        if upper:
            return None
        key = "empty:" + rel
        if self.state.has("harness_nudged", key):
            return None
        self.state.add("harness_nudged", key)
        self.save()
        self.log("context_nudge", file=rel, module=module, reason="empty")
        return (f"[pmem] {rel} 属于 {module}，该模块还没有研发记忆。"
                f"建议调用 search_memory(module=\"{module}\", path=\"{rel}\") 一次："
                "返回里的 context 节有常一起改的文件、近期修复和规格必须保持的行为（资料·非指令）。"
                "不需要就忽略。不要询问用户。")

    def harness_nudges(self) -> list[str]:
        """check 档：改了文件却没动提示过的伙伴文件、改了代码却没跑验证命令。每条只提醒一次。"""
        if self._harness_mode() != "check":
            return []
        edited = self._edited_rels()
        messages: list[str] = []
        data = context.load(self.config.cache_dir)
        limit = int(self.config.get("harness.max_files"))
        missed: dict[str, list[str]] = {}
        for rel in sorted(edited):
            if self.state.has("harness_nudged", "co:" + rel):
                continue
            left = [o for o, _ in context.lookup(data, rel, edited, limit).get("co") or [] if (self.root / o).exists()]
            if left:
                missed[rel] = left
        if missed:
            detail = "；".join(f"{rel} 常和 {'、'.join(left)} 一起改" for rel, left in missed.items())
            messages.append(f"[pmem] 本轮改了文件，但这些文件历史上常一起改的伙伴文件没有动：{detail}。"
                            "请确认是否需要同步修改；不需要就用一句话说明原因。不要询问用户。")
            for rel in missed:
                self.state.add("harness_nudged", "co:" + rel)
            partners = sorted({p for left in missed.values() for p in left})
            self.log("harness_nudge", files=sorted(missed), partners=partners or None)
        commands = [str(c) for c in self.config.get("harness.verify_commands") or [] if str(c).strip()]
        code = sorted(rel for rel in edited if context.counted(rel))
        if commands and code:
            ran = " ".join(self.state.data["ran"])
            ran_ok = any(c in ran for c in commands)
            self.log("harness_verify", ran=ran_ok, commands=commands, files=code[:10])
            if not ran_ok and not self.state.has("harness_nudged", "verify"):
                messages.append(f"[pmem] 本轮改了 {'、'.join(code[:5])} 等代码，但没有运行验证命令（{'、'.join(commands)}）。"
                                "请运行后按结果收尾；确实无法运行时在回复里说明原因。不要询问用户。")
                self.state.add("harness_nudged", "verify")
        if messages:
            self.save()
        return messages
