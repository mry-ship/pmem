"""给没有关联代码（anchors）的记忆补上：从正文里提到的文件名、“类名.成员”解析到仓库中的文件。

只采用能唯一确定的文件；同名文件有多个时优先取记忆所属模块路径下的，仍不唯一就放弃。
"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path

from pmem.core.config import Config
from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.scan.lite import THIRD_PARTY_NAMES, skip_dir
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs

SOURCE_EXT = ("cs", "lua", "py", "ts", "tsx", "js", "jsx", "go", "java", "kt", "swift", "m", "mm", "cpp", "cc",
              "c", "h", "hpp", "rs", "shader")
DATA_EXT = ("json", "yaml", "yml", "prefab", "asset", "xml", "csv")
UNITY_PACKAGES = "Packages"
MAX_ANCHORS = 5
_EXT = "|".join(SOURCE_EXT + DATA_EXT)
_PATH = re.compile(rf"(?<![A-Za-z0-9_./\\-])([A-Za-z0-9_][A-Za-z0-9_./\\-]*\.(?:{_EXT}))(?![A-Za-z0-9_])")
_MEMBER = re.compile(r"(?<![A-Za-z0-9_.])([A-Z][A-Za-z0-9_]{2,})\.([A-Za-z_][A-Za-z0-9_]{2,})(?![A-Za-z0-9_])")


class FileIndex:
    def __init__(self, root: Path, registry: ModuleRegistry):
        self.root = root
        self.registry = registry
        self.by_name: dict[str, list[str]] = defaultdict(list)
        self.by_stem: dict[str, list[str]] = defaultdict(list)
        for folder, dirs, files in os.walk(root):
            # 第三方代码里的同名类（Menu、Initialize 之类）会被误认成记忆说的那个；com.xxx 是内嵌的 UPM 包
            dirs[:] = [d for d in dirs if not skip_dir(d) and d != UNITY_PACKAGES and not d.startswith("com.")
                       and not THIRD_PARTY_NAMES.match(d)]
            base = Path(folder).relative_to(root).as_posix()
            for name in files:
                ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
                if ext not in SOURCE_EXT and ext not in DATA_EXT:
                    continue
                rel = name if base == "." else f"{base}/{name}"
                if registry.is_excluded(rel):
                    continue
                self.by_name[name.lower()].append(rel)
                if ext in SOURCE_EXT:
                    self.by_stem[name.rsplit(".", 1)[0]].append(rel)

    def _owner(self, rel: str) -> str | None:
        try:
            match = self.registry.module_for_path(rel)
        except RegistryError:
            return None
        return match.module_id if match else None

    def _pick(self, candidates: list[str], module: str) -> str | None:
        if len(candidates) == 1:
            return candidates[0]
        mine = [c for c in candidates if self._owner(c) == module]
        return mine[0] if len(mine) == 1 else None

    def resolve_path(self, raw: str, module: str) -> str | None:
        wanted = raw.replace("\\", "/").lstrip("./")
        candidates = self.by_name.get(wanted.rsplit("/", 1)[-1].lower(), [])
        if "/" in wanted:
            candidates = [c for c in candidates if c.lower().endswith(wanted.lower())]
        return self._pick(candidates, module)

    def resolve_class(self, name: str, module: str) -> str | None:
        return self._pick(self.by_stem.get(name, []), module)


def find_anchors(content: str, module: str, files: FileIndex) -> list[str]:
    anchors: list[str] = []

    def add(anchor: str | None) -> None:
        if anchor and anchor not in anchors and anchor.partition("#")[0] not in [a.partition("#")[0] for a in anchors]:
            anchors.append(anchor)

    for raw in _PATH.findall(content):
        add(files.resolve_path(raw, module))
    for cls, member in _MEMBER.findall(content):
        if member.lower() in SOURCE_EXT + DATA_EXT:
            continue
        rel = files.resolve_class(cls, module)
        if rel is None:
            continue
        text = (files.root / rel).read_text(encoding="utf-8", errors="ignore")
        add(f"{rel}#{member}" if re.search(rf"\b{re.escape(member)}\b", text) else rel)
    return anchors[:MAX_ANCHORS]


def parse_renames(raw: list[str]) -> list[tuple[str, str]]:
    pairs = []
    for item in raw:
        old, sep, new = item.partition("=")
        old, new = old.strip().replace("\\", "/").strip("/"), new.strip().replace("\\", "/").strip("/")
        if not sep or not old or not new:
            raise ValueError(f"--rename {item!r} 格式不对，应为 旧路径=新路径（文件、目录，或 路径#函数名）")
        if ("#" in old) != ("#" in new):
            raise ValueError(f"--rename {item!r}：带 #函数名 时两边都要带")
        pairs.append((old, new))
    return pairs


def rename_anchor(anchor: str, renames: list[tuple[str, str]]) -> str:
    """代码搬家后改写关联代码：路径#函数 精确匹配优先，其次文件，再次目录前缀；匹配不到原样返回。"""
    path, sep, symbol = anchor.replace("\\", "/").partition("#")
    for old, new in renames:
        if "#" in old and anchor.replace("\\", "/") == old:
            return new
    for old, new in renames:
        if "#" in old:
            continue
        if path == old or path.startswith(old + "/"):
            return new + path[len(old):] + sep + symbol
    return anchor


def run_rename(root: Path, raw: list[str], apply: bool) -> int:
    try:
        renames = parse_renames(raw)
    except ValueError as exc:
        print(exc)
        return 1
    config = Config.load(root)
    storage = FilesStorage(root, detect_vcs(root, config.get("vcs")))
    changes: list[tuple[Path, object, list[str]]] = []
    missing: list[str] = []
    for path, entry in storage.iter_all():
        updated = [rename_anchor(a, renames) for a in entry.anchors]
        if updated == entry.anchors:
            continue
        changes.append((path, entry, updated))
        for before, after in zip(entry.anchors, updated):
            if before == after:
                continue
            target, _, symbol = after.partition("#")
            file = root / target
            if not file.is_file():
                missing.append(f"{entry.id}：{after}（文件不存在）")
            elif symbol and not re.search(rf"\b{re.escape(symbol)}\b",
                                          file.read_text(encoding="utf-8", errors="ignore")):
                missing.append(f"{entry.id}：{after}（文件里找不到 {symbol}）")
    for _, entry, updated in changes[:10]:
        moved = [f"{a} → {b}" for a, b in zip(entry.anchors, updated) if a != b]
        print(f"  {entry.module}/{entry.entity} {entry.id}：{'；'.join(moved)}")
    if len(changes) > 10:
        print(f"  ……另有 {len(changes) - 10} 条")
    print(f"关联代码要改写的记忆 {len(changes)} 条（含已替代、已归档的，保持历史可追溯）")
    if missing:
        print("注意，改写后对不上的关联代码（检查新路径或改成 路径#函数名 逐条改）：")
        print("\n".join(f"  {m}" for m in missing[:10]))
    if not changes:
        return 0
    if not apply:
        print("以上为预览；确认无误后加 --apply 写回记忆文件，再提交 .memory/。改写后的记忆会因新文件的提交记录标“需核实”，核对后 pmem confirm")
        return 0
    for path, entry, updated in changes:
        entry.anchors = updated
        path.write_text(entry.to_markdown(), encoding="utf-8", newline="\n")
    print(f"已改写 {len(changes)} 条记忆的关联代码。")
    return 0


def run_anchors(root: Path, module: str | None, apply: bool) -> int:
    config = Config.load(root)
    registry = ModuleRegistry.load(config.modules_path) if config.modules_path.exists() else ModuleRegistry({})
    if module:
        try:
            module = registry.resolve_module(module).id
        except RegistryError as exc:
            print(exc)
            return 1
    storage = FilesStorage(root, detect_vcs(root, config.get("vcs")))
    print("扫描仓库文件…", flush=True)
    files = FileIndex(root, registry)
    scanned = changed = total = 0
    samples: list[str] = []
    for path, entry in storage.iter_all():
        if entry.anchors or (module and entry.module != module):
            continue
        scanned += 1
        found = find_anchors(entry.content, entry.module, files)
        if not found:
            continue
        changed += 1
        total += len(found)
        if len(samples) < 10:
            samples.append(f"  {entry.module}/{entry.entity} {entry.id}: {', '.join(found)}")
        if apply:
            entry.anchors = found
            path.write_text(entry.to_markdown(), encoding="utf-8", newline="\n")
    print(f"没有关联代码的记忆 {scanned} 条，其中 {changed} 条能从正文解析出关联代码，共 {total} 处。示例：")
    print("\n".join(samples) if samples else "  （无）")
    if changed and not apply:
        print("以上为预览；确认无误后加 --apply 写回记忆文件，再提交 .memory/。")
    elif apply:
        print(f"已写回 {changed} 条记忆。")
    return 0
