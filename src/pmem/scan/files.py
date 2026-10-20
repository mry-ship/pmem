"""仓库代码文件索引：按文件名、类名（文件名去扩展名）查文件，供补全关联代码与清理候选判断正文提到的代码还在不在。"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path

from pmem.core.registry import ModuleRegistry, RegistryError
from pmem.scan.lite import THIRD_PARTY_NAMES, kept_dirs

SOURCE_EXT = ("cs", "lua", "py", "ts", "tsx", "js", "jsx", "go", "java", "kt", "swift", "m", "mm", "cpp", "cc",
              "c", "h", "hpp", "rs", "shader")
DATA_EXT = ("json", "yaml", "yml", "prefab", "asset", "xml", "csv")
UNITY_PACKAGES = "Packages"
_EXT = "|".join(SOURCE_EXT + DATA_EXT)
# 正文里提到的文件（带扩展名）与“类名.成员”
PATH_MENTION = re.compile(rf"(?<![A-Za-z0-9_./\\-])([A-Za-z0-9_][A-Za-z0-9_./\\-]*\.(?:{_EXT}))(?![A-Za-z0-9_])")
MEMBER_MENTION = re.compile(r"(?<![A-Za-z0-9_.])([A-Z][A-Za-z0-9_]{2,})\.([A-Za-z_][A-Za-z0-9_]{2,})(?![A-Za-z0-9_])")


class FileIndex:
    def __init__(self, root: Path, registry: ModuleRegistry):
        self.root = root
        self.registry = registry
        self.by_name: dict[str, list[str]] = defaultdict(list)
        self.by_stem: dict[str, list[str]] = defaultdict(list)
        for folder, dirs, files in os.walk(root):
            # 第三方代码里的同名类（Menu、Initialize 之类）会被误认成记忆说的那个；com.xxx 是内嵌的 UPM 包
            dirs[:] = [d for d in kept_dirs(dirs) if d != UNITY_PACKAGES and not d.startswith("com.")
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

    def candidates(self, raw: str) -> list[str]:
        wanted = raw.replace("\\", "/").lstrip("./")
        found = self.by_name.get(wanted.rsplit("/", 1)[-1].lower(), [])
        if "/" in wanted:
            found = [c for c in found if c.lower().endswith(wanted.lower())]
        return found

    def resolve_path(self, raw: str, module: str) -> str | None:
        return self._pick(self.candidates(raw), module)

    def resolve_class(self, name: str, module: str) -> str | None:
        return self._pick(self.by_stem.get(name, []), module)

    def present_symbols(self, names: set[str]) -> set[str]:
        """names 里哪些在源码里还出现（整词）。类名等于文件名的直接算；其余读一遍源码文件，全部找到就提前结束。
        Python、TS 这类类名和文件名不对应的语言靠这一步，否则正文提到的类都会被当成已删除。"""
        found = {n for n in names if n in self.by_stem}
        rest = names - found
        if not rest:
            return found
        pattern = re.compile(r"\b(" + "|".join(sorted(map(re.escape, rest), key=len, reverse=True)) + r")\b")
        for rels in self.by_stem.values():
            for rel in rels:
                try:
                    text = (self.root / rel).read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                hits = set(pattern.findall(text)) & rest
                if hits:
                    found |= hits
                    rest -= hits
                    if not rest:
                        return found
                    pattern = re.compile(r"\b(" + "|".join(sorted(map(re.escape, rest), key=len, reverse=True)) + r")\b")
        return found


_PRODUCT_NAME = re.compile(r"^[A-Z][a-z]+\.js$")


def _is_code_path(raw: str) -> bool:
    # 不带目录的 config.yaml、hooks.json 多是运行时生成或别的项目里的文件，Next.js 这类是产品名
    if _PRODUCT_NAME.match(raw):
        return False
    return "/" in raw.replace("\\", "/") or raw.rsplit(".", 1)[-1].lower() in SOURCE_EXT


def code_mentions(content: str) -> list[tuple[str, str]]:
    """正文提到的代码：("path", 文件) 与 ("class", 类名)，去重。只认源码文件和带目录的路径。"""
    found = [("path", raw) for raw in PATH_MENTION.findall(content) if _is_code_path(raw)]
    found += [("class", cls) for cls, member in MEMBER_MENTION.findall(content)
              if member.lower() not in SOURCE_EXT + DATA_EXT]
    return list(dict.fromkeys(found))
