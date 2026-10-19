from __future__ import annotations

import re
from dataclasses import dataclass, field

KINDS = ("conclusion", "exclusion", "correction", "risk", "decision")
# 展示顺序即先看的顺序：排除项、风险最能避免走弯路
KIND_LABELS = {"exclusion": "排除项", "risk": "风险", "correction": "更正", "decision": "决定", "conclusion": "结论"}
STATUSES = ("draft", "seed", "active", "archived")
VISIBLE_STATUSES = ("active", "seed", "draft")
# 归档记忆不再被检索到，但它的 supersedes 仍然算数：归档表示这条演进线整体过时
REPLACING_STATUSES = (*VISIBLE_STATUSES, "archived")

_FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)


@dataclass
class Entry:
    id: str
    module: str
    entity: str
    kind: str
    content: str
    note_date: str
    author: str
    revision: str = "none"
    status: str = "active"
    supersedes: list[str] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)
    source_conversation: str | None = None
    aliases: list[str] = field(default_factory=list)
    verified: str | None = None
    archived_on: str | None = None
    archived_from: str | None = None
    archived_by: str | None = None

    @property
    def checked_date(self) -> str:
        """最近一次确认成立的日期：核对过取核对日期，否则取写入日期。"""
        return max(self.note_date, self.verified or "")

    def status_on(self, day: str | None) -> str:
        """某天的状态：那天之后才归档的，按归档前的状态算；没记归档日期的旧文件一律按已归档。"""
        if day and self.status == "archived" and self.archived_on and self.archived_on > day:
            return self.archived_from or "active"
        return self.status

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"kind 必须是 {' / '.join(KINDS)} 之一，当前为 {self.kind!r}")
        if self.status not in STATUSES:
            raise ValueError(f"status 必须是 {' / '.join(STATUSES)} 之一，当前为 {self.status!r}")

    def to_markdown(self) -> str:
        meta: dict = {
            "id": self.id,
            "module": self.module,
            "entity": self.entity,
            "kind": self.kind,
            "status": self.status,
            "supersedes": list(self.supersedes),
            "anchors": list(self.anchors),
            "revision": self.revision,
            "author": self.author,
            "note_date": self.note_date,
        }
        if self.aliases:
            meta["aliases"] = list(self.aliases)
        if self.verified:
            meta["verified"] = self.verified
        if self.archived_on:
            meta["archived"] = {"on": self.archived_on, "from": self.archived_from or "active"}
            if self.archived_by:
                meta["archived"]["by"] = self.archived_by
        if self.source_conversation:
            meta["source"] = {"conversation": self.source_conversation}
        import yaml

        head = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).rstrip()
        return f"---\n{head}\n---\n{self.content.strip()}\n"

    @classmethod
    def from_markdown(cls, text: str) -> Entry:
        match = _FRONT_MATTER.match(text)
        if not match:
            raise ValueError("记忆文件缺少 YAML 头（以 --- 开始和结束）")
        import yaml

        meta = yaml.safe_load(match.group(1)) or {}
        source = meta.get("source") or {}
        archived = meta.get("archived") if isinstance(meta.get("archived"), dict) else {}
        restored = str(archived.get("from") or "")
        return cls(
            id=str(meta["id"]),
            module=str(meta["module"]),
            entity=str(meta["entity"]),
            kind=str(meta["kind"]),
            content=match.group(2).replace("\r\n", "\n").strip(),
            note_date=str(meta["note_date"]),
            author=str(meta.get("author") or ""),
            revision=str(meta.get("revision") or "none"),
            status=str(meta.get("status") or "active"),
            supersedes=[str(x) for x in meta.get("supersedes") or []],
            anchors=[str(x) for x in meta.get("anchors") or []],
            source_conversation=source.get("conversation"),
            aliases=[str(x) for x in meta.get("aliases") or []],
            verified=str(meta["verified"]) if meta.get("verified") else None,
            archived_on=str(archived["on"]) if archived.get("on") else None,
            archived_from=restored if restored in STATUSES and restored != "archived" else None,
            archived_by=str(archived["by"]) if archived.get("by") else None,
        )
