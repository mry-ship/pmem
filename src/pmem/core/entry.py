from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

KINDS = ("conclusion", "exclusion", "correction", "risk", "decision")
STATUSES = ("draft", "seed", "active", "archived")

_FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.S)


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
        if self.source_conversation:
            meta["source"] = {"conversation": self.source_conversation}
        head = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).rstrip()
        return f"---\n{head}\n---\n{self.content.strip()}\n"

    @classmethod
    def from_markdown(cls, text: str) -> Entry:
        match = _FRONT_MATTER.match(text)
        if not match:
            raise ValueError("记忆文件缺少 YAML 头（以 --- 开始和结束）")
        meta = yaml.safe_load(match.group(1)) or {}
        source = meta.get("source") or {}
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
        )
