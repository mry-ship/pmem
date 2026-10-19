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
# 适用范围：module（默认，只属于本模块）/ project（全项目都会踩的坑，任何模块的摘要都带上）
SCOPES = ("module", "project")
PITFALL_KINDS = ("exclusion", "risk", "correction")
SUMMARY_MAX = 60

_FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
KNOWN_KEYS = frozenset({"id", "module", "entity", "kind", "status", "supersedes", "anchors", "revision", "author",
                        "note_date", "aliases", "verified", "verified_at", "archived", "source",
                        "summary", "scope", "verify"})
# 正文开头常自带“决定：”“更正（2026-10-19）：”，和类型标签放在一起就成了“决定：决定：”
_KIND_PREFIX = re.compile(
    r"^\s*(?:决定|结论|更正|排除项?|风险|根因|原因|注意|背景|现象|问题|坑)(?:\s*[（(][^）)]{0,40}[）)])?\s*[：:]\s*"
)
_SENTENCE_END = re.compile(r"[。；;！!？?\n]")


def strip_kind_prefix(text: str) -> str:
    return _KIND_PREFIX.sub("", text, count=1)


def auto_summary(content: str, limit: int = SUMMARY_MAX) -> str:
    """没写 summary 时的标题：去掉类型前缀后的第一句，超长截断。"""
    body = strip_kind_prefix(content.strip())
    first = _SENTENCE_END.split(body, maxsplit=1)[0].strip() or body
    flat = " ".join(first.split())
    return flat if len(flat) <= limit else flat[:limit] + "…"


def _text(value) -> str | None:
    text = " ".join(str(value).split()) if value is not None else ""
    return text or None


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
    # 核对的精确时刻（带时区的 ISO 时间）：verified 只到天，同一天写下的新记忆分不出先后
    verified_at: str | None = None
    archived_on: str | None = None
    archived_from: str | None = None
    archived_by: str | None = None
    summary: str | None = None
    scope: str | None = None
    # 怎么确认问题已解决或结论仍成立：命令、测试、现象
    verify: str | None = None
    # 本版本不认识的 YAML 头字段（较新版本写的）：重写文件时原样带上，团队混用版本时不丢
    extra: dict = field(default_factory=dict)

    @property
    def title(self) -> str:
        """一行标题：写入时给的 summary，没有就从正文第一句生成。"""
        return self.summary or auto_summary(self.content)

    @property
    def project_wide(self) -> bool:
        return self.scope == "project"

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
        if self.summary:
            meta["summary"] = self.summary
        if self.scope and self.scope != "module":
            meta["scope"] = self.scope
        if self.verify:
            meta["verify"] = self.verify
        if self.aliases:
            meta["aliases"] = list(self.aliases)
        if self.verified:
            meta["verified"] = self.verified
            if self.verified_at:
                meta["verified_at"] = self.verified_at
        if self.archived_on:
            meta["archived"] = {"on": self.archived_on, "from": self.archived_from or "active"}
            if self.archived_by:
                meta["archived"]["by"] = self.archived_by
        if self.source_conversation:
            meta["source"] = {"conversation": self.source_conversation}
        meta.update({k: v for k, v in self.extra.items() if k not in KNOWN_KEYS})
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
            verified_at=str(meta["verified_at"]) if meta.get("verified_at") else None,
            archived_on=str(archived["on"]) if archived.get("on") else None,
            archived_from=restored if restored in STATUSES and restored != "archived" else None,
            archived_by=str(archived["by"]) if archived.get("by") else None,
            summary=_text(meta.get("summary")),
            scope=_text(meta.get("scope")),
            verify=str(meta["verify"]).strip() or None if meta.get("verify") else None,
            extra={k: v for k, v in meta.items() if k not in KNOWN_KEYS},
        )
