"""写入：record_memory 的全部规则（内容校验、草稿覆盖、每日上限、锚点规范化、写作提示、相近记忆）。"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from pmem.core.entry import KINDS, RECORD_KINDS, SCOPES, SUMMARY_MAX, VISIBLE_STATUSES, Entry, auto_summary
from pmem.core.ids import new_ulid
from pmem.core.quality import content_hints, entity_hint, verify_hint
from pmem.core.registry import ResolvedModule, is_descendant, parent_module
from pmem.core.secrets import find_secrets
from pmem.core.textfmt import format_content
from pmem.service.base import MAX_LIMIT, ServiceBase, fail, returns_errors

MAX_INHERITED_ANCHORS = 10
MAX_SIMILAR = 2
MAX_ALIASES = 10
MAX_ALIAS_CHARS = 30
WRITABLE_STATUSES = ("active", "seed", "draft")
SIMILAR_HINT = (
    "similar 是同模块最相近的已有记忆：新结论与其中某条重复或推翻了它，就带 draft_id 重写并在 supersedes 填那条的 id；"
    "无关则忽略。"
)
SIBLING_HINT = ("sibling_similar 是兄弟模块里同一议题的教训：如果这个结论对 {parent} 的所有下级都成立，"
                "改写到 {parent}，并在 supersedes 填这些 id（可以替代下级模块的记忆）。")
ALIASES_HINT = "没填 aliases：把现象和关键术语的其他常用叫法（如 闪退/崩溃/crash）写进 aliases，换个说法也能搜到。"
ANCHOR_HINT = (
    "anchors 只写了文件：该文件以后任何改动都会让这条记忆标为“需核实”。能定位到函数时写成 路径#函数名"
    "（如 src/Reward.cs#Claim），只有这个函数改了才需要核实。"
)
HINTS_FOOTER = "以上只是提示，已写入；如需修改，带上 draft_id 再写一次即可覆盖。"
SUMMARY_HINT = ("没填 summary：已按正文第一句生成标题“{title}”。读代码摘要、Wiki 和去重后的检索只显示标题，"
                "不准确就带 draft_id 补一句 {limit} 字以内、可直接复述的结论（Agent 换说法复述时收益报告会漏计采用）。")
SUMMARY_LONG_HINT = "summary 有 {n} 字，超过建议的 {limit} 字：标题只写一句结论，细节放正文。"
MAX_VERIFY_CHARS = 300
MAX_APPLIES_CHARS = 120
# summary 超过 SUMMARY_MAX 只提示；超过这个数就是把正文写进了标题，摘要、Wiki 每行都会被撑爆
MAX_SUMMARY_CHARS = 200
MAX_ENTITY_CHARS = 60


def _one_line(text: str | None) -> str:
    return " ".join(str(text or "").split())


def _on_disk_case(root: Path, rel: str) -> str | None:
    """按磁盘上的真实大小写拼出相对路径；Windows 不区分大小写，Git 区分。路径不存在时返回 None。"""
    current, parts = root, []
    for part in Path(rel).parts:
        try:
            names = os.listdir(current)
        except OSError:
            return None
        match = part if part in names else next((n for n in names if n.lower() == part.lower()), None)
        if match is None:
            return None
        parts.append(match)
        current = current / match
    return "/".join(parts)


def _clean_aliases(raw: list[str] | None) -> list[str]:
    seen: list[str] = []
    for alias in raw or []:
        text = str(alias).strip()
        if text and len(text) <= MAX_ALIAS_CHARS and text.lower() not in {s.lower() for s in seen}:
            seen.append(text)
    return seen[:MAX_ALIASES]


class RecordOps(ServiceBase):
    def record(
        self,
        module: str,
        entity: str,
        kind: str,
        content: str,
        supersedes: list[str] | None = None,
        anchors: list[str] | None = None,
        draft_id: str | None = None,
        source_conversation: str | None = None,
        aliases: list[str] | None = None,
        status: str | None = None,
        summary: str | None = None,
        scope: str | None = None,
        verify: str | None = None,
        applies: str | None = None,
    ) -> dict:
        response = self._record(module, entity, kind, content, supersedes, anchors, draft_id,
                                source_conversation, aliases, status, summary, scope, verify, applies)
        if not response.get("ok"):
            self._log("record_rejected", conv=source_conversation, module=module, entity=entity or None,
                      code=response.get("code"), error=str(response.get("error") or "")[:200])
        return response

    @returns_errors
    def _record(self, module, entity, kind, content, supersedes, anchors, draft_id, source_conversation, aliases,
                status, summary=None, scope=None, verify=None, applies=None) -> dict:
        given_anchors = set(anchors or [])
        resolved = self.registry.resolve_module(module)
        target = self.registry.modules.get(resolved.id)
        if target is not None and target.deprecated:
            return fail(f"模块 {resolved.id} 已废弃（只读），不再接受新记忆；仍在维护的话先运行 "
                        f"pmem migrate deprecate {resolved.id} --undo --apply", "module_deprecated")
        if status and status not in WRITABLE_STATUSES:
            return fail(f"status 只能是 {' / '.join(WRITABLE_STATUSES)}，当前为 {status!r}", "status_invalid")
        scope = str(scope or "").strip().lower() or None
        if scope and scope not in SCOPES:
            return fail(f"scope 只能是 {' / '.join(SCOPES)}，当前为 {scope!r}", "scope_invalid")
        summary = _one_line(summary) or None
        if summary and len(summary) > MAX_SUMMARY_CHARS:
            return fail(f"summary 最多 {MAX_SUMMARY_CHARS} 字（建议 {SUMMARY_MAX} 字以内的一句话），当前 {len(summary)} 字",
                        "content_length")
        raw_entity = str(entity or "").strip()
        # splitlines 认 \r、\u2028 等所有换行；其他控制字符同样会拆断摘要行
        if len(raw_entity.splitlines()) > 1 or len(raw_entity) > MAX_ENTITY_CHARS \
                or any(ord(c) < 32 or 0x7f <= ord(c) < 0xa0 for c in raw_entity):
            return fail(f"entity 是模块内议题的短名（如 Reward、Config），须单行且不超过 {MAX_ENTITY_CHARS} 字",
                        "entity_invalid")
        applies = _one_line(applies) or None
        if applies and len(applies) > MAX_APPLIES_CHARS:
            return fail(f"applies 最多 {MAX_APPLIES_CHARS} 字（写这条在什么前提下成立），当前 {len(applies)} 字",
                        "content_length")
        verify = str(verify or "").strip() or None
        if verify and len(verify) > MAX_VERIFY_CHARS:
            return fail(f"verify 最多 {MAX_VERIFY_CHARS} 字（写怎么确认：命令、测试、现象），当前 {len(verify)} 字",
                        "content_length")
        content = (content or "").strip()
        problem = self._invalid_content(kind, content)
        if problem:
            return fail(problem[1], problem[0])
        entity_id = self.registry.resolve_entity(resolved.id, entity or "")
        if not entity_id:
            return fail("entity 不能为空，用于区分模块内的议题，如 Reward、Config", "entity_missing")

        # 替代自己的草稿说明要新建一条（草稿已提交时只能这样）；闸门可能按同议题自动注入了这个 draft_id
        if draft_id and draft_id in (supersedes or []):
            draft_id = None
        # 下面的草稿、归档、成环、每日上限判断都要看最新文件：终端可能刚归档或写入，常驻服务的索引有节流
        self.index.refresh(force=True)
        # 覆盖草稿时没传（None）的列表沿用原值，传空列表才清空；否则替代关系丢失，旧记忆会悄悄恢复现行
        old = self.index.find(draft_id) if draft_id else None
        if old is not None and old.status == "archived":
            return fail(f"记忆 {draft_id} 已归档，不能覆盖；要接着用就先 pmem archive {draft_id} --restore，"
                        f"要写新结论就新建一条并在 supersedes 中写 {draft_id}", "draft_forbidden")
        if old is not None:
            supersedes = old.supersedes if supersedes is None else supersedes
            anchors = old.anchors if anchors is None else anchors
            aliases = old.aliases if aliases is None else aliases
            summary = summary or old.summary
            scope = scope or old.scope
            verify = verify or old.verify
            applies = applies or old.applies
            if status is None and old.status in WRITABLE_STATUSES:
                status = old.status

        today = date.today().isoformat()
        supersedes = list(dict.fromkeys(s for s in supersedes or [] if s))
        replaced = [found for s in supersedes if (found := self.index.find(s)) is not None]
        # 被替代的记忆会从它所在模块的检索里消失，新结论却在别的模块，查原模块的人两边都看不到。
        # 下级模块例外：查下级会带上本模块的教训，把下级的结论提升到上级时可以直接替代
        cross = [e for e in replaced if e.module != resolved.id and not is_descendant(e.module, resolved.id)]
        if cross:
            where = "、".join(f"{e.id}（{e.module}）" for e in cross)
            return fail(f"supersedes 只能填本模块（{resolved.id}）或它下级模块的记忆，{where} 属于别的模块。"
                        f"旧结论在原模块已不成立：在原模块写一条 correction 替代它，正文说明新结论在 {resolved.id}；"
                        f"旧记忆本来就归错了模块：先 pmem migrate move <id> --to {resolved.id} --apply 搬过来再替代",
                        "supersede_cross_module")
        if old is not None and self._reaches(replaced, old.id):
            return fail(f"supersedes 会和 {old.id} 已有的替代关系连成环，两条记忆都会从检索里消失；"
                        "请新建一条（不带 draft_id）替代它们", "supersede_cycle")
        aliases = _clean_aliases(aliases)
        hits = find_secrets(" ".join([entity_id, *aliases, *(anchors or []), summary or "", verify or "", applies or ""]),
                            self.config.get("write.secret_patterns") or [])
        if hits:
            return fail("entity、aliases、anchors、summary、verify 或 applies 疑似包含敏感信息，已拒绝写入："
                        + "；".join(hits), "secret")
        hints = self._write_hints(resolved.id, entity_id, kind, content, aliases, merging=len(replaced) >= 2)
        hints += self._field_hints(kind, content, summary, verify)
        if anchors and not any("#" in a for a in anchors):
            hints.append(ANCHOR_HINT)
        # 替代仍然现行的旧记忆（含合并零碎记忆）不增加现行条数，不受每日上限约束；
        # 已被替代、已归档的不算，否则可以借它们无限写入
        hidden = self.index.superseded()
        replaces_current = any(e.id not in hidden and e.status in VISIBLE_STATUSES for e in replaced)
        # 覆盖同议题当天的草稿不增加当天条数；换了议题或覆盖的是前几天的草稿，照常计数
        same_draft = old is not None and old.module == resolved.id and old.note_date == today \
            and old.entity.lower() == entity_id.lower()
        if not same_draft and not replaces_current:
            over_cap = self._daily_cap_error(resolved.id, entity_id, today)
            if over_cap:
                return over_cap

        replaced_ids = [e.id for e in replaced]
        warnings = [f"supersedes 中的 {s} 不存在，已忽略对它的替代关系" for s in supersedes if s not in replaced_ids]
        if not anchors and replaced:
            anchors = list(dict.fromkeys(a for e in replaced for a in e.anchors))[:MAX_INHERITED_ANCHORS]
        anchors = list(dict.fromkeys(
            self._normalize_anchor(a, warnings if a in given_anchors else []) for a in anchors or [] if a.strip()
        ))
        entry = Entry(
            id=new_ulid(),
            module=resolved.id,
            entity=entity_id,
            kind=kind,
            content=format_content(content),
            note_date=today,
            author=self.user,
            revision=self.vcs.revision(),
            status=status or str(self.config.get("write.default_status")),
            supersedes=replaced_ids,
            anchors=anchors,
            source_conversation=source_conversation or None,
            aliases=aliases,
            summary=summary,
            scope=scope if scope != "module" else None,
            verify=verify,
            applies=applies,
            extra=dict(old.extra) if old is not None else {},
        )
        written = self.storage.write(entry, draft_id=draft_id or None)
        self.index.refresh(force=True)

        response = {
            "ok": True,
            "id": written.entry.id,
            "module": resolved.id,
            "entity": entity_id,
            "kind": kind,
            "path": written.path.relative_to(self.root).as_posix(),
            "overwritten": written.overwritten,
            "draft_id": written.entry.id,
        }
        flags, module_warnings = self._module_notes(resolved)
        response.update(flags)
        warnings += module_warnings
        if warnings:
            response["warnings"] = warnings
        similar = self._similar_memories(written.entry)
        if similar:
            response["similar"] = similar
            hints.append(SIMILAR_HINT)
        siblings = self._sibling_lessons(written.entry)
        if siblings:
            response["sibling_similar"] = siblings
            hints.append(SIBLING_HINT.format(parent=parent_module(resolved.id)))
        if hints:
            response["hints"] = hints + [HINTS_FOOTER]
        self._refresh_wiki(response)
        self._log(
            "record",
            conv=source_conversation,
            id=written.entry.id,
            module=resolved.id,
            entity=entity_id,
            kind=kind,
            overwritten=written.overwritten,
            supersedes=entry.supersedes or None,
        )
        return response

    def _reaches(self, start: list[Entry], target: str) -> bool:
        """沿 supersedes 从 start 往下走能否走到 target。"""
        stack, seen = list(start), set()
        while stack:
            entry = stack.pop()
            if entry.id == target:
                return True
            if entry.id in seen:
                continue
            seen.add(entry.id)
            stack += [found for s in entry.supersedes if (found := self.index.find(s)) is not None]
        return False

    def _normalize_anchor(self, raw: str, warnings: list[str]) -> str:
        """过期核对按相对路径、区分大小写去比对版本库记录：绝对路径或大小写不对的锚点永远不会标“需核实”。"""
        path, sep, symbol = raw.strip().replace("\\", "/").partition("#")
        rel = self._relative(path)
        while rel.startswith("./"):
            rel = rel[2:]
        if Path(rel).is_absolute():
            warnings.append(f"anchors 中的 {path} 不在项目目录内，无法核对是否过期")
            return f"{rel}{sep}{symbol}"
        actual = _on_disk_case(self.root, rel)
        if actual is None:
            warnings.append(f"anchors 中的 {rel} 在项目里不存在，请检查路径")
        return f"{actual or rel}{sep}{symbol}"

    def _invalid_content(self, kind: str, content: str) -> tuple[str, str] | None:
        """不合格时返回 (错误码, 提示)。"""
        if kind not in KINDS:
            return "kind_invalid", f"kind 必须是 {' / '.join(KINDS)} 之一"
        low, high = int(self.config.get("write.content_min")), int(self.config.get("write.content_max"))
        if not low <= len(content) <= high:
            return "content_length", f"正文长度需在 {low}–{high} 字之间，当前 {len(content)} 字"
        hits = find_secrets(content, self.config.get("write.secret_patterns") or [])
        if hits:
            return "secret", "正文疑似包含敏感信息，已拒绝写入：" + "；".join(hits)
        return None

    @staticmethod
    def _field_hints(kind: str, content: str, summary: str | None, verify: str | None) -> list[str]:
        hints = []
        if not summary:
            hints.append(SUMMARY_HINT.format(title=auto_summary(content), limit=SUMMARY_MAX))
        elif len(summary) > SUMMARY_MAX:
            hints.append(SUMMARY_LONG_HINT.format(n=len(summary), limit=SUMMARY_MAX))
        missing_verify = verify_hint(kind, verify)
        if missing_verify:
            hints.append(missing_verify)
        return hints

    def _write_hints(self, module_id: str, entity_id: str, kind: str, content: str, aliases: list[str],
                     merging: bool) -> list[str]:
        """只提示、不拦截的写作建议。合并多条零碎记忆时篇长只受硬上限约束。"""
        limit_key = "write.content_max" if merging else "write.recommend_max"
        hints = content_hints(content, int(self.config.get(limit_key)), kind)
        if not self.registry.is_global_entity(entity_id):
            new_entity = entity_hint(entity_id, self._known_entities(module_id))
            if new_entity:
                hints.append(new_entity)
        if not aliases:
            hints.append(ALIASES_HINT)
        return hints

    def _known_entities(self, module_id: str) -> list[str]:
        module = self.registry.modules.get(module_id) or self.registry.candidates.get(module_id)
        declared = [*module.entities, *module.components, *module.variants] if module else []
        used = [e.entity for e in self.index.entries() if e.module == module_id]
        return list(dict.fromkeys([*declared, *used]))

    def _daily_cap_error(self, module_id: str, entity_id: str, today: str) -> dict | None:
        same_day = [
            e.id for e in self.index.entries()
            if e.module == module_id and e.entity.lower() == entity_id.lower() and e.note_date == today
        ]
        cap = int(self.config.get("write.max_per_day_per_entity"))
        if len(same_day) < cap:
            return None
        return fail(
            f"{module_id}/{entity_id} 今天已有 {len(same_day)} 条记忆，达到上限 {cap}；"
            "请把新结论合并进已有的一条（带 draft_id 覆盖自己未提交的那条），或用 supersedes 替代旧结论",
            "daily_cap",
            existing_ids=same_day,
        )

    def _module_notes(self, resolved: ResolvedModule) -> tuple[dict, list[str]]:
        """写到别名、候选模块或未登记模块时，附在返回里的标记与提醒。"""
        flags: dict = {}
        warnings: list[str] = []
        if resolved.redirected_from:
            warnings.append(f"{resolved.redirected_from} 已并入 {resolved.id}")
        if resolved.candidate:
            flags["candidate_module"] = True
            warnings.append(f"{resolved.id} 是冷候选模块，已有记忆后建议负责人在 modules.yaml 中把它转为正式模块")
        elif not resolved.known:
            flags["new_module"] = True
            flags["similar_modules"] = [m for m in self._similar_modules(resolved.id) if m != resolved.id]
            warnings.append(f"{resolved.id} 尚未登记在 modules.yaml；如是笔误请改用相近模块")
        return flags, warnings

    def _sibling_lessons(self, entry: Entry) -> list[dict]:
        """兄弟模块里同一议题的现行教训：几个下级都写了同一件事，多半该写在上级。只看议题相同，不按相关度猜。"""
        parent = parent_module(entry.module)
        if parent is None or entry.kind in RECORD_KINDS:
            return []
        siblings = {m.lower() for m in self.registry.children(parent)} - {entry.module.lower()}
        hidden = self.index.superseded()
        rows = [
            {"id": e.id, "module": e.module, "kind": e.kind, "date": e.note_date, "preview": e.title}
            for e in self.index.entries()
            if e.module.lower() in siblings and e.entity.lower() == entry.entity.lower()
            and e.kind not in RECORD_KINDS and e.id not in hidden and e.status in VISIBLE_STATUSES
        ]
        return rows[:MAX_SIMILAR]

    def _similar_memories(self, entry: Entry) -> list[dict]:
        """同一议题下与新记忆最相近的有效记忆，交给写入的 Agent 判断是重复、推翻还是无关。

        只看同一实体：跨议题时相关度分不清真假（见 Ranking 排除项），每次都附两条无关记忆只会成为噪音。
        同一议题下条数很少，关键词就够；不加载语义模型，命令行写入因此快约 1 秒。
        """
        skip = {entry.id, *entry.supersedes}
        result = self._index_search(
            module=entry.module, entity=entry.entity, query=" ".join([entry.content, *entry.aliases]),
            limit=MAX_SIMILAR + len(skip), max_per_batch=MAX_LIMIT, verify=False, semantic=False,
        )
        rows = [
            {"id": i["id"], "entity": i["entity"], "kind": i["kind"], "date": i["date"],
             "preview": i.get("summary") or auto_summary(i["content"])}
            for i in result.items if i["id"] not in skip
        ]
        return rows[:MAX_SIMILAR]
