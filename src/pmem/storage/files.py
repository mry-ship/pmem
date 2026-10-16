from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from pmem.core.entry import Entry
from pmem.core.ids import is_ulid
from pmem.vcs.base import VCS


class StorageError(ValueError):
    pass


@dataclass
class WriteResult:
    entry: Entry
    path: Path
    overwritten: bool


class FilesStorage:
    """记忆文件存储：.memory/entries/<module>/<id>.md，一条一个文件。"""

    def __init__(self, root: str | Path, vcs: VCS, svn_auto_add: bool = True):
        self.root = Path(root).resolve()
        self.entries_dir = self.root / ".memory" / "entries"
        self.vcs = vcs
        self.svn_auto_add = svn_auto_add
        self.warnings: list[str] = []

    def path_for(self, entry: Entry) -> Path:
        return self.entries_dir / entry.module / f"{entry.id}.md"

    def find_path(self, entry_id: str) -> Path | None:
        # id 会拼进匹配模式，只接受 ULID，免得 ../ 或通配符指到记忆目录以外
        if not is_ulid(entry_id) or not self.entries_dir.is_dir():
            return None
        return next(self.entries_dir.glob(f"*/{entry_id}.md"), None)

    def read(self, path: Path) -> Entry:
        return Entry.from_markdown(path.read_text(encoding="utf-8-sig"))

    def get(self, entry_id: str) -> Entry | None:
        path = self.find_path(entry_id)
        return self.read(path) if path else None

    def iter_files(self) -> Iterator[Path]:
        if self.entries_dir.is_dir():
            yield from sorted(self.entries_dir.glob("*/*.md"))

    def iter_all(self) -> Iterator[tuple[Path, Entry]]:
        self.warnings = []
        for path in self.iter_files():
            try:
                yield path, self.read(path)
            except Exception as exc:  # noqa: BLE001
                self.warnings.append(f"跳过无法解析的记忆文件 {path.relative_to(self.root)}：{exc}")

    def _check_draft(self, entry: Entry, draft_id: str) -> Path:
        if not is_ulid(draft_id):
            raise StorageError(f"draft_id {draft_id!r} 不是有效的记忆 id（26 位 ULID）；请用写入时返回的 draft_id")
        path = self.find_path(draft_id)
        if path is None:
            raise StorageError(f"draft_id {draft_id} 对应的记忆不存在；请不带 draft_id 新建")
        old = self.read(path)
        if old.author != entry.author:
            raise StorageError(
                f"记忆 {draft_id} 的作者是 {old.author}，不能覆盖；请新建一条并在 supersedes 中写 {draft_id}"
            )
        if old.module != entry.module:
            raise StorageError(f"记忆 {draft_id} 属于 {old.module}，不能改到 {entry.module}；请新建一条")
        if not self.vcs.is_uncommitted(path):
            raise StorageError(f"记忆 {draft_id} 已提交到版本库，不能覆盖；请新建一条并在 supersedes 中写 {draft_id}")
        return path

    def write(self, entry: Entry, draft_id: str | None = None) -> WriteResult:
        if draft_id:
            path = self._check_draft(entry, draft_id)
            entry.id = draft_id
            overwritten = True
        else:
            path = self.path_for(entry)
            if path.exists():
                raise StorageError(f"记忆 {entry.id} 已存在")
            overwritten = False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry.to_markdown(), encoding="utf-8", newline="\n")
        if not overwritten and self.svn_auto_add and self.vcs.name == "svn":
            self.vcs.add(path)
        return WriteResult(entry, path, overwritten)
