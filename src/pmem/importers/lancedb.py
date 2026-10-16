"""从参考实现（tilematch-dev-memory 一类）的 LanceDB 库导入记忆。

源库每个模块一张表 `mem_<大类>__<模块>`，字段 id / entity / note_date / content / created_at。
只读：先把库目录复制到临时目录再打开，避免与正在运行的 MCP 服务争用文件。
"""
from __future__ import annotations

import re
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pmem.core.entry import Entry
from pmem.core.ids import new_ulid
from pmem.core.secrets import find_secrets
from pmem.core.textfmt import format_content
from pmem.storage.files import FilesStorage

TABLE = re.compile(r"^mem_([a-z0-9_]+)__([A-Za-z0-9_]+)$")
SOURCE_PREFIX = "lancedb:"
_KIND_HINTS = (
    ("exclusion", ("排除", "不要", "勿", "禁止", "不是根因", "无效")),
    ("correction", ("更正", "纠正", "之前结论有误", "修正结论")),
    ("risk", ("风险", "注意", "隐患", "坑")),
    ("decision", ("决定", "决策", "方案确定", "约定")),
)


@dataclass
class ImportReport:
    written: Counter = field(default_factory=Counter)
    kinds: Counter = field(default_factory=Counter)
    skipped_existing: int = 0
    skipped_secret: list[str] = field(default_factory=list)
    skipped_empty: int = 0
    tables: int = 0


def guess_kind(content: str) -> str:
    head = content.strip()[:30]
    for kind, words in _KIND_HINTS:
        if any(w in head for w in words):
            return kind
    return "conclusion"


def _timestamp_ms(created_at: str, note_date: str) -> int:
    for raw in (created_at, note_date):
        if not raw:
            continue
        try:
            value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp() * 1000)
    return 0


def _table_names(db) -> list[str]:
    if not hasattr(db, "list_tables"):
        return list(db.table_names())
    names: list[str] = []
    token = None
    while True:
        response = db.list_tables(page_token=token) if token else db.list_tables()
        names += list(response.tables)
        token = response.page_token
        if not token:
            return names


def read_rows(db_dir: Path) -> tuple[list[dict], int]:
    import lancedb

    with tempfile.TemporaryDirectory(prefix="pmem-import-") as tmp:
        snapshot = Path(tmp) / db_dir.name
        shutil.copytree(db_dir, snapshot)
        db = lancedb.connect(str(snapshot))
        names = _table_names(db)
        rows: list[dict] = []
        tables = 0
        for name in sorted(names):
            match = TABLE.match(name)
            if not match:
                continue
            tables += 1
            module = f"{match.group(1)}.{match.group(2)}"
            data = db.open_table(name).to_arrow()
            columns = [c for c in ("id", "entity", "note_date", "content", "created_at") if c in data.column_names]
            for row in data.select(columns).to_pylist():
                row["module"] = module
                rows.append(row)
    return rows, tables


def import_rows(
    rows: list[dict], storage: FilesStorage, author: str, dry_run: bool = False, infer_kind: bool = False
) -> ImportReport:
    report = ImportReport()
    existing = {e.source_conversation for _, e in storage.iter_all() if e.source_conversation}
    rows = sorted(rows, key=lambda r: _timestamp_ms(str(r.get("created_at") or ""), str(r.get("note_date") or "")))
    for row in rows:
        content = str(row.get("content") or "").strip()
        source = f"{SOURCE_PREFIX}{row.get('id')}"
        if not content:
            report.skipped_empty += 1
            continue
        if source in existing:
            report.skipped_existing += 1
            continue
        if find_secrets(content, []):
            report.skipped_secret.append(f"{row['module']}/{row.get('id')}")
            continue
        created = _timestamp_ms(str(row.get("created_at") or ""), str(row.get("note_date") or ""))
        kind = guess_kind(content) if infer_kind else "conclusion"
        entry = Entry(
            id=new_ulid(created or None),
            module=row["module"],
            entity=str(row.get("entity") or "General"),
            kind=kind,
            content=format_content(content),
            note_date=str(row.get("note_date") or "")[:10] or datetime.now().date().isoformat(),
            author=author,
            source_conversation=source,
        )
        if not dry_run:
            storage.write(entry)
        existing.add(source)
        report.written[row["module"]] += 1
        report.kinds[kind] += 1
    return report


def catalog_from_reference(path: Path) -> dict:
    """把参考实现的 modules.yaml（categories → modules → entities）转成 pmem 的模块目录。"""
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}
    categories, modules = {}, {}
    for cat, info in (data.get("categories") or {}).items():
        info = info or {}
        categories[cat] = {k: info[k] for k in ("label", "description") if info.get(k)}
        for name, mod in (info.get("modules") or {}).items():
            entities = (mod or {}).get("entities") or []
            modules[f"{cat}.{name}"] = {"entities": entities} if entities else {}
    return {"schema_version": 1, "categories": categories, "modules": modules}
