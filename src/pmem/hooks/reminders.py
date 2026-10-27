"""回合结束时的提醒：改了代码没写记忆、查了记忆没记结论、提问涉及的模块没查过。"""

from __future__ import annotations

import re

from wcmatch import glob as wglob

from pmem.core import seen
from pmem.hooks.memories import GLOB_FLAGS
from pmem.hooks.payload import turn_reply_text

# 【pmem修改】【pmem查询】等，也认旧写法【pmem】
PMEM_LINE = re.compile(r"【pmem[^】]{0,6}】")
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")


def _pmem_declare_line(line: str) -> bool:
    """自检声明只解析【pmem修改】与旧写法【pmem】行；检索/查询行里的记忆标题可能含“无新结论”等字，不能当声明。"""
    if not PMEM_LINE.match(line):
        return False
    return not line.startswith(("【pmem检索】", "【pmem查询】"))


def _segment_plain(segment: str) -> str:
    """去掉「标题」引号内的文字，避免把记忆标题里的“无需记录”“无新结论”当成声明。"""
    return re.sub(r"「[^」]*」", "", segment)


class Reminders:
    def _written(self) -> set[str]:
        return {key.split("|", 1)[0] for key in self.state.data["written"]} | set(self.state.data["cli_recorded"])

    def _reminders_on(self, setting: str, default: bool | None = None) -> bool:
        return bool(self.config.get(setting, default)) and self.config.get("gate.mode") != "off"

    def _pending_nudges(self, declared: set[str] = frozenset()) -> list[str]:
        """改了代码却没写记忆、回复里也没说明无需记录的模块。"""
        if not self._reminders_on("gate.stop_reminder", True):
            return []
        written = self._written()
        return [m for m in self._record_required()
                if m not in written and m not in declared and not self.state.has("nudged", m)]

    def _declarations(self, reply: str) -> tuple[set[str], set[str] | None]:
        """回复末尾【pmem】行里的说明，按“；”分段，免得一句说明把别的模块也带过去。
        无需记录：只认同一段里点了名的模块（功能记录与规格提醒）。
        无新结论：各段点名的模块并集，只放过这些模块的查阅/排查提醒；任一段没点名则查阅/排查提醒全部不发。
        返回 None 表示查阅/排查提醒全部不发；空集表示不因无新结论而放过任何模块。"""
        declared: set[str] = set()
        lookup_skip: set[str] = set()
        skip_all_lookup = False
        for line in reply.splitlines():
            line = line.strip().lstrip("-* ")
            if not _pmem_declare_line(line):
                continue
            for segment in re.split(r"[；;]", line):
                plain = _segment_plain(segment)
                if "无需记录" in plain:
                    declared.update(self.modules_in_text(segment))
                if "无新结论" in plain:
                    named = set(self.modules_in_text(segment))
                    if not named:
                        skip_all_lookup = True
                    else:
                        lookup_skip.update(named)
        concluded = None if skip_all_lookup else lookup_skip
        return declared, concluded

    def _record_required(self) -> list[str]:
        """改过、需要写功能记录的模块：只改了测试、生成代码、配置（gate.record_exempt）的不算，废弃模块不算。"""
        exempt = [str(p) for p in self.config.get("gate.record_exempt") or []]
        files: dict[str, list[str]] = {}
        for item in self.state.data["edited_files"]:
            module, _, rel = item.partition("|")
            files.setdefault(module, []).append(rel)

        def needed(module: str) -> bool:
            own = files.get(module)
            return not own or any(not any(wglob.globmatch(f, p, flags=GLOB_FLAGS) for p in exempt) for f in own)

        return [m for m in self.state.data["edited"] if not self._deprecated(m) and needed(m)]

    def _pending_specs(self, declared: set[str] = frozenset()) -> list[str]:
        """改了行为却还没写对应规格的模块。和功能记录分开记已提醒，避免互相抵消。"""
        if not self._reminders_on("spec.reminder", False):
            return []
        written = set(self.state.data.get("spec_written") or [])
        return [m for m in self._record_required()
                if m not in written and m not in declared and not self.state.has("spec_nudged", m)]

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

    def _pending_analysis(self) -> list[str]:
        """排查类对话收口：查过却没改也没写的模块，即使用过别的模块也要提醒（防错类必写）。"""
        if not self._reminders_on("gate.analysis_reminder"):
            return []
        return [m for m in self._analyzed() if not self.state.has("consult_nudged", m) and not self._deprecated(m)]

    def _consulted_only(self) -> list[str]:
        """整个对话只查了记忆、没改代码也没写记忆时，查过的模块；写代码时顺带查的模块不算。"""
        if not self._reminders_on("gate.analysis_reminder"):
            return []
        if self._written() or self.state.data["edited"]:
            return []
        return [m for m in self.state.data["consulted"]
                if not self.state.has("consult_nudged", m) and not self._deprecated(m)]

    def on_stop(self) -> dict:
        if self.state is None:
            return {}
        self.state.cleanup_old()
        seen.cleanup_old(self.config.cache_dir)
        status = self.payload.get("status")
        # 中断或出错结束的回合、用户说了“跳过记忆”的对话都不提醒；由提醒触发的续跑回合
        # （Cursor 的 loop_count、Claude Code 的 stop_hook_active）也不再追加，留到下一个回合
        finished = status in (None, "completed") and not self.state.data["skip"]
        follow = finished and not (self.payload.get("loop_count") or self.payload.get("stop_hook_active"))
        asked, viewed = self._unreviewed() if follow else ([], [])
        review = asked + viewed
        declared, concluded = self._declarations(turn_reply_text(self.payload.get("transcript_path"))) \
            if follow else (set(), set())
        pending = self._pending_nudges(declared) if follow else []
        specs = self._pending_specs(declared) if follow else []
        analyzed = self._analyzed() if finished else []
        analysis_pending = self._pending_analysis() if follow else []
        consulted_pending = (
            [m for m in self._consulted_only() if m not in analysis_pending] if follow else []
        )
        if concluded is None:
            analysis_pending, consulted_pending = [], []
        elif concluded:
            analysis_pending = [m for m in analysis_pending if m not in concluded]
            consulted_pending = [m for m in consulted_pending if m not in concluded]
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
            required=self._record_required() or None,
            analyzed=analyzed or None,
            review=review or None,
            nudged=(pending + analysis_pending + consulted_pending + specs) or None,
            **usage,
        )
        if not review and not pending and not analysis_pending and not consulted_pending and not specs:
            return {"followup_message": notice} if notice else {}
        for module in review:
            self.state.add("review_nudged", module)
        # 功能记录、查阅、规格各记一本，免得先催了查阅，后来改了代码却不再催功能记录
        for module in pending:
            self.state.add("nudged", module)
        for module in analysis_pending + consulted_pending:
            self.state.add("consult_nudged", module)
        for module in specs:
            self.state.add("spec_nudged", module)
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
                f"[pmem] 本轮修改了 {'、'.join(pending)}，还没有写研发记忆。"
                "1) 每个模块用 record_memory 写一条功能记录（kind=feature）：需求来源（谁要求的、为什么）、"
                "必须保持的行为、适用条件（applies）、入口在哪；summary 写一句“什么行为必须保持”，不写“改了哪个方法”；"
                "已有功能记录说的就是这件事时用 supersedes 更新它，实现了某条规划（plan）也用 supersedes 替代它。"
                "2) 本轮另有以下内容时，再各写一条对应类型的教训（优先防错类，避免只记流水账）："
                "试过不行、被排除的方向（exclusion，最值钱）；看代码看不出的约束或风险（risk）；"
                "推翻旧结论（correction）；确认的根因或踩到的坑（conclusion）；"
                "为什么选这个方案而不是别的（decision）。"
                "确实不需要记录（只改了注释、格式、重命名等，行为没变）时，在【pmem修改】行写“无需记录：<一句原因>”。不要询问用户。"
            )
        if analysis_pending:
            messages.append(
                f"[pmem] 本轮是排查类对话，查了 {'、'.join(analysis_pending)} 的记忆，却还没落结论。"
                "请为每个模块至少写一条教训（优先 exclusion：试过不行的方向；其次 risk / conclusion / correction）；"
                "确认没有任何可沉淀结论时，在【pmem修改】行写“已核对，无新结论”。不要询问用户。"
            )
        if consulted_pending:
            messages.append(
                f"[pmem] 本轮查了 {'、'.join(consulted_pending)} 的记忆，没有改代码也没有写记忆。"
                "得出了新结论就直接用 record_memory 记下（优先 exclusion / risk / conclusion / correction）；"
                "没有新结论时在【pmem修改】行写“已核对，无新结论”。不要询问用户。"
            )
        if specs:
            messages.append(
                f"[pmem] 本轮修改了 {'、'.join(specs)}，对应的模块规格还没更新。"
                "请按 pmem-spec 更新 .memory/specs/<模块>/ 里对应的那一份："
                "程序和现状只改正波及的段落，本轮新定的策划和美术写入并保留。"
                "无画面的模块美术节写「本模块无画面」。"
                "目录里还没有美术设计.md 时补上这一份。"
                "不要整篇重写，也不要改其他模块。不要询问用户。"
            )
        if notice:
            messages.append(notice)
        # 每条都以 [pmem] 开头：下一轮靠它认出这是自动提醒、不是用户提问
        return {"followup_message": "\n".join(messages)}
