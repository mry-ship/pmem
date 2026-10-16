from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from wcmatch import glob as wglob

DEFAULT_CATEGORIES = ("activity", "gameplay", "economy", "infra")

_CATEGORY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_GLOB_FLAGS = wglob.GLOBSTAR | wglob.BRACE | wglob.DOTGLOB | wglob.FORCEUNIX | wglob.IGNORECASE
_WILDCARD = re.compile(r"\*\*|\*|\?|\[[^\]]*\]|\{[^}]*\}")
_MERGED_PREFIX = "merged_into:"
MIN_ASCII_NAME = 4


class RegistryError(ValueError):
    pass


@dataclass
class Module:
    id: str
    paths: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    variants: list[str] = field(default_factory=list)
    parent: str | None = None
    status: str = "active"
    description: str = ""

    @property
    def category(self) -> str:
        return self.id.split(".", 1)[0]

    @property
    def name(self) -> str:
        return self.id.split(".", 1)[1]

    @property
    def merged_into(self) -> str | None:
        if self.status.startswith(_MERGED_PREFIX):
            return self.status[len(_MERGED_PREFIX):].strip()
        return None

    @classmethod
    def from_dict(cls, module_id: str, data: dict | None) -> Module:
        data = data or {}
        return cls(
            id=module_id,
            paths=[str(p) for p in data.get("paths") or []],
            aliases=[str(a) for a in data.get("aliases") or []],
            entities=[str(e) for e in data.get("entities") or []],
            components=[str(c) for c in data.get("components") or []],
            variants=[str(v) for v in data.get("variants") or []],
            parent=data.get("parent"),
            status=str(data.get("status") or "active"),
            description=str(data.get("description") or ""),
        )


@dataclass
class ResolvedModule:
    id: str
    category: str
    name: str
    known: bool
    candidate: bool = False
    redirected_from: str | None = None


@dataclass
class PathMatch:
    module_id: str
    pattern: str
    candidate: bool = False


def glob_specificity(pattern: str) -> tuple[int, int]:
    """越具体越大：先比字面字符数，再比通配符个数（少者优先）。"""
    literal = _WILDCARD.sub("", pattern)
    return len(literal), -len(_WILDCARD.findall(pattern))


def _normalise_path(path: str) -> str:
    normalised = path.replace("\\", "/")
    while normalised.startswith("./"):
        normalised = normalised[2:]
    return normalised.lstrip("/")


def _matches(pattern: str, path: str) -> bool:
    pattern = _normalise_path(pattern).rstrip("/")
    if not _WILDCARD.search(pattern):
        lp, lpath = pattern.lower(), path.lower()
        return lpath == lp or lpath.startswith(lp + "/")
    return wglob.globmatch(path, pattern, flags=_GLOB_FLAGS)


def _item_path(item) -> str:
    return str(item["path"]) if isinstance(item, dict) else str(item)


class ModuleRegistry:
    def __init__(self, data: dict | None):
        data = data or {}
        self.categories: list[str] = list((data.get("categories") or {}).keys()) or list(DEFAULT_CATEGORIES)
        self.modules: dict[str, Module] = {
            mid: Module.from_dict(mid, body) for mid, body in (data.get("modules") or {}).items()
        }
        self.candidates: dict[str, Module] = {
            mid: Module.from_dict(mid, body) for mid, body in (data.get("candidates") or {}).items()
        }
        self.third_party: list[str] = [_item_path(x) for x in data.get("third_party") or []]
        self.ignored: list[str] = [_item_path(x) for x in data.get("ignored") or []]

        self.synonyms: list[list[str]] = [
            [str(t).strip() for t in group if str(t).strip()]
            for group in data.get("synonyms") or []
            if isinstance(group, list) and len(group) >= 2
        ]

        self._entity_vocab: dict[str, str] = {}
        for canonical, aliases in (data.get("entities") or {}).items():
            self._entity_vocab[str(canonical).lower()] = str(canonical)
            for alias in aliases or []:
                self._entity_vocab[str(alias).lower()] = str(canonical)

        self._full_index: dict[str, str] = {}
        self._bare_index: dict[str, set[str]] = {}
        for mid, module in self.modules.items():
            self._full_index[mid.lower()] = mid
            self._bare_index.setdefault(module.name.lower(), set()).add(mid)
            for alias in module.aliases:
                if "." in alias:
                    self._full_index.setdefault(alias.lower(), mid)
                else:
                    self._bare_index.setdefault(alias.lower(), set()).add(mid)
        self._candidate_index = {mid.lower(): mid for mid in self.candidates}

    @classmethod
    def load(cls, path: str | Path) -> ModuleRegistry:
        try:
            data = yaml.safe_load(Path(path).read_text(encoding="utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise RegistryError(f"{Path(path).name} 不是 UTF-8 编码，请用 UTF-8 保存") from exc
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            where = f"第 {mark.line + 1} 行" if mark is not None else ""
            problem = getattr(exc, "problem", None) or str(exc)
            raise RegistryError(f"{Path(path).name} {where}格式错误：{problem}") from exc
        return cls(data)

    # ---- 名称解析 ----

    def _follow_merge(self, mid: str) -> str:
        seen = {mid}
        while (target := self.modules[mid].merged_into) is not None:
            target_id = self._full_index.get(target.lower(), target)
            if target_id in seen or target_id not in self.modules:
                raise RegistryError(f"模块 {mid} 的 merged_into 指向无效或成环：{target}")
            seen.add(target_id)
            mid = target_id
        return mid

    def _resolved(self, mid: str, original: str | None = None) -> ResolvedModule:
        final = self._follow_merge(mid)
        category, name = final.split(".", 1)
        redirected = original if original and original != final else None
        return ResolvedModule(final, category, name, known=True, redirected_from=redirected)

    def resolve_module(self, raw: str) -> ResolvedModule:
        text = (raw or "").strip()
        if not text:
            raise RegistryError("模块名不能为空，格式为 category.Name")
        key = text.lower()
        if key in self._full_index:
            mid = self._full_index[key]
            return self._resolved(mid, mid if self.modules[mid].merged_into else None)

        if "." not in text:
            ids = self._bare_index.get(key)
            if not ids:
                raise RegistryError(f"未知模块 {text!r}，请使用 category.Name 格式，或先用 list_modules 查看")
            if len(ids) > 1:
                raise RegistryError(f"模块名 {text!r} 有歧义：{', '.join(sorted(ids))}，请写全 category.Name")
            mid = next(iter(ids))
            return self._resolved(mid, mid if self.modules[mid].merged_into else None)

        category, name = text.split(".", 1)
        category = category.lower()
        if category not in self.categories:
            raise RegistryError(f"未知大类 {category!r}，只允许：{' / '.join(self.categories)}")
        if not _NAME_RE.match(name):
            raise RegistryError(f"模块名 {name!r} 不合法，只能包含字母、数字、下划线且以字母开头")
        cand = self._candidate_index.get(f"{category}.{name}".lower())
        if cand:
            return ResolvedModule(cand, category, cand.split(".", 1)[1], known=False, candidate=True)
        return ResolvedModule(f"{category}.{name}", category, name, known=False)

    def name_patterns(self) -> dict[str, re.Pattern]:
        """文字里提到某个模块的匹配式：模块名与不带点的别名，英文至少 4 个字符且按词边界，中文至少 2 个字。"""
        patterns = {}
        for mid, module in self.modules.items():
            names = [n for n in (module.name, *module.aliases) if "." not in n]
            names = [n for n in names if (len(n) >= MIN_ASCII_NAME if n.isascii() else len(n) >= 2)]
            if names:
                alternation = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
                patterns[mid] = re.compile(rf"(?<![A-Za-z0-9_])(?:{alternation})(?![A-Za-z0-9_])")
        return patterns

    def is_global_entity(self, name: str) -> bool:
        return self._entity_vocab.get(name.lower()) == name

    def resolve_entity(self, module_id: str, raw: str) -> str:
        text = (raw or "").strip()
        key = text.lower()
        module = self.modules.get(module_id) or self.candidates.get(module_id)
        if module:
            for name in (*module.entities, *module.components, *module.variants):
                if name.lower() == key:
                    return name
        return self._entity_vocab.get(key, text)

    # ---- 路径映射 ----

    def is_excluded(self, path: str) -> bool:
        p = _normalise_path(path)
        return any(_matches(pat, p) for pat in (*self.third_party, *self.ignored))

    def module_for_path(self, path: str) -> PathMatch | None:
        p = _normalise_path(path)
        if self.is_excluded(p):
            return None
        hits: list[tuple[tuple[int, int], PathMatch]] = []
        for pool, is_candidate in ((self.modules, False), (self.candidates, True)):
            for mid, module in pool.items():
                if module.merged_into:
                    continue
                for pattern in module.paths:
                    if _matches(pattern, p):
                        hits.append((glob_specificity(pattern), PathMatch(mid, pattern, is_candidate)))
        if not hits:
            return None
        best = max(spec for spec, _ in hits)
        top = [m for spec, m in hits if spec == best]
        ids = sorted({m.module_id for m in top})
        if len(ids) > 1:
            raise RegistryError(f"路径 {p} 同时映射到 {', '.join(ids)}，请在 modules.yaml 中消除重叠")
        return top[0]
