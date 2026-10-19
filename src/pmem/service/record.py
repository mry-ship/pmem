"""写入：record_memory 的全部规则（内容校验、草稿覆盖、每日上限、锚点规范化、写作提示、相近记忆）。"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from pmem.core.entry import KINDS, Entry
from pmem.core.ids import new_ulid
from pmem.core.quality import content_hints, entity_hint
from pmem.core.registry import ResolvedModule
from pmem.core.secrets import find_secrets
from pmem.core.textfmt import format_content
from pmem.index.graph import preview
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
ALIASES_HINT = "没填 aliases：把现象和关键术语的其他常用叫法（如 闪退/崩溃/crash）写进 aliases，换个说法也能搜到。"
ANCHOR_HINT = (
    "anchors 只写了文件：该文件以后任何改动都会让这条记忆标为“需核实”。能定位到函数时写成 路径#函数名"
    "（如 src/Reward.cs#Claim），只有这个函数改了才需要核实。"
)
HINTS_FOOTER = "以上只是提示，已写入；如需修改，带上 draft_id 再写一次即可覆盖。"


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
    ) -> dict:
        response = self._record(module, entity, kind, content, supersedes, anchors, draft_id,
                                source_conversation, aliases, status)
        if not response.get("ok"):
            self._log("record_rejected", conv=source_conversation, module=module, entity=entity or None,
                      code=response.get("code"), error=str(response.get("error") or "")[:200])
        return response

    @returns_errors
    def _record(self, module, entity, kind, content, supersedes, anchors, draft_id, source_conversation, aliases,
                status) -> dict:
        given_anchors = set(anchors or [])
        resolved = self.registry.resolve_module(module)
        target = self.registry.modules.get(resolved.id)
        if target is not None and target.deprecated:
            return fail(f"模块 {resolved.id} 已废弃（只读），不再接受新记忆；仍在维护的话先运行 "
                        f"pmem migrate deprecate {resolved.id} --undo --apply", "module_deprecated")
        if status and status not in WRITABLE_STATUSES:
            return fail(f"status 只能是 {' / '.join(WRITABLE_STATUSES)}，当前为 {status!r}", "status_invalid")
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
        # 覆盖草稿时没传（None）的列表沿用原值，传空列表才清空；否则替代关系丢失，旧记忆会悄悄恢复现行
        old = self.index.find(draft_id) if draft_id else None
        if old is not None and old.status == "archived":
            return fail(f"记忆 {draft_id} 已归档，不能覆盖；要接着用就先 pmem archive {draft_id} --restore，"
                        f"要写新结论就新建一条并在 supersedes 中写 {draft_id}", "draft_forbidden")
        if old is not None:
            supersedes = old.supersedes if supersedes is None else supersedes
            anchors = old.anchors if anchors is None else anchors
            aliases = old.aliases if aliases is None else aliases
            if status is None and old.status in WRITABLE_STATUSES:
                status = old.status

        today = date.today().isoformat()
        supersedes = list(dict.fromkeys(s for s in supersedes or [] if s))
        replaced = [found for s in supersedes if (found := self.index.find(s)) is not None]
        aliases = _clean_aliases(aliases)
        hints = self._write_hints(resolved.id, entity_id, content, aliases, merging=len(replaced) >= 2)
        if anchors and not any("#" in a for a in anchors):
            hints.append(ANCHOR_HINT)
        # 替代旧记忆（含合并零碎记忆）不增加条数，不受每日上限约束
        if not draft_id and not replaced:
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
        )
        written = self.storage.write(entry, draft_id=draft_id or None)
        self.index.refresh(force=True)

        response = {
            "ok": True,
            "id": written.entry.id,
            "module": resolved.id,
            "entity": entity_id,
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

    def _write_hints(self, module_id: str, entity_id: str, content: str, aliases: list[str], merging: bool) -> list[str]:
        """只提示、不拦截的写作建议。合并多条零碎记忆时篇长只受硬上限约束。"""
        limit_key = "write.content_max" if merging else "write.recommend_max"
        hints = content_hints(content, int(self.config.get(limit_key)))
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
            {"id": i["id"], "entity": i["entity"], "kind": i["kind"], "date": i["date"], "preview": preview(i["content"])}
            for i in result.items if i["id"] not in skip
        ]
        return rows[:MAX_SIMILAR]
