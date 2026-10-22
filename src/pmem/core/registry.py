from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from wcmatch import glob as wglob

from pmem.core.config import load_yaml

DEFAULT_CATEGORIES = ("feature", "infra")

_CATEGORY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_GLOB_FLAGS = wglob.GLOBSTAR | wglob.BRACE | wglob.DOTGLOB | wglob.FORCEUNIX | wglob.IGNORECASE
WILDCARD = re.compile(r"\*\*|\*|\?|\[[^\]]*\]|\{[^}]*\}")
MERGED_PREFIX = "merged_into:"
DEPRECATED = "deprecated"
MIN_ASCII_NAME = 4
# 大类 + 最多三层名字；再深多半是把平台、渠道这类交叉维度编进了模块树
MAX_MODULE_DEPTH = 4
DEPTH_HINT = ("模块名最多 4 段（大类.模块.子模块.子模块）；渠道、平台、变体用 entity、applies 或 variants 表达，"
              "确实需要更深就把某一层提升为独立模块")


class RegistryError(ValueError):
    """code 供统计归类（如 pmem health 的被拒写入），提示文字可以随意改。"""

    def __init__(self, message: str, code: str = "modules_yaml"):
        super().__init__(message)
        self.code = code


def is_module_id(text: str) -> bool:
    """category.Name[.Sub[.Sub]]：大类小写、每段字母开头，总共不超过 MAX_MODULE_DEPTH 段。"""
    category, dot, rest = str(text).partition(".")
    parts = rest.split(".")
    return bool(dot and _CATEGORY_RE.match(category) and len(parts) < MAX_MODULE_DEPTH
                and all(_NAME_RE.match(p) for p in parts))


def module_depth(module_id: str) -> int:
    return str(module_id).count(".") + 1


def parent_module(module_id: str) -> str | None:
    """父模块由名字推出：去掉最后一段；两段的模块没有父模块。"""
    return module_id.rsplit(".", 1)[0] if module_depth(module_id) > 2 else None


def ancestor_modules(module_id: str) -> list[str]:
    """由近到远的祖先模块名（不论是否登记）。"""
    found, current = [], parent_module(module_id)
    while current:
        found.append(current)
        current = parent_module(current)
    return found


def is_descendant(module_id: str, ancestor: str) -> bool:
    """module_id 在 ancestor 之下（不含自身，不区分大小写）。"""
    return module_id.lower().startswith(ancestor.lower() + ".")


def is_lineage(a: str, b: str) -> bool:
    """a 与 b 是同一个模块，或一个是另一个的祖先（不区分大小写）。"""
    la, lb = a.lower(), b.lower()
    return la == lb or la.startswith(lb + ".") or lb.startswith(la + ".")


@dataclass
class Module:
    id: str
    paths: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    variants: list[str] = field(default_factory=list)
    # 旧版的 parent 字段已不生效（父子关系由名字表达），只留着给健康检查提示改名
    legacy_parent: str | None = None
    related: list[dict] = field(default_factory=list)
    status: str = "active"
    description: str = ""

    @property
    def category(self) -> str:
        return self.id.split(".", 1)[0]

    @property
    def name(self) -> str:
        """短名：最后一段。"""
        return self.id.rsplit(".", 1)[1]

    @property
    def path_name(self) -> str:
        """去掉大类的部分，如 Ads.AdMob。"""
        return self.id.split(".", 1)[1]

    @property
    def parent_id(self) -> str | None:
        return parent_module(self.id)

    @property
    def depth(self) -> int:
        return module_depth(self.id)

    @property
    def deprecated(self) -> bool:
        return self.status.strip() == DEPRECATED

    @property
    def merged_into(self) -> str | None:
        if self.status.startswith(MERGED_PREFIX):
            return self.status[len(MERGED_PREFIX):].strip()
        return None

    @classmethod
    def from_dict(cls, module_id: str, data: dict | None) -> Module:
        category, dot, name = str(module_id).partition(".")
        if not dot or not category or not name:
            raise RegistryError(f"modules.yaml 里的模块名 {module_id!r} 应写成 大类.模块名（如 feature.Login）")
        data = data or {}
        if not isinstance(data, dict):
            raise RegistryError(f"modules.yaml 里 {module_id} 的内容应是键值对（paths、aliases 等）")

        def words(key: str) -> list[str]:
            value = data.get(key) or []
            # 手写成 paths: src/shop 时不能按字符拆开，否则永远匹配不上、单个字母还会被当成别名
            if isinstance(value, str):
                return [value]
            if not isinstance(value, list):
                raise RegistryError(f"modules.yaml 里 {module_id}.{key} 应是列表")
            return [str(v) for v in value]

        return cls(
            id=module_id,
            paths=words("paths"),
            aliases=words("aliases"),
            entities=words("entities"),
            components=words("components"),
            variants=words("variants"),
            legacy_parent=str(data["parent"]) if data.get("parent") else None,
            related=_related_items(module_id, data.get("related")),
            status=str(data.get("status") or "active"),
            description=str(data.get("description") or ""),
        )


def _related_items(module_id: str, value) -> list[dict]:
    """related: [infra.Build] 或 [{module: infra.Build, reason: ...}]，统一成 {module, reason}。"""
    if not value:
        return []
    if isinstance(value, (str, dict)):
        value = [value]
    if not isinstance(value, list):
        raise RegistryError(f"modules.yaml 里 {module_id}.related 应是列表")
    items = []
    for item in value:
        if isinstance(item, dict):
            target, reason = str(item.get("module") or "").strip(), str(item.get("reason") or "").strip()
        else:
            target, reason = str(item).strip(), ""
        if target:
            items.append({"module": target, "reason": reason})
    return items


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
    literal = WILDCARD.sub("", pattern)
    return len(literal), -len(WILDCARD.findall(pattern))


def _normalise_path(path: str) -> str:
    normalised = path.replace("\\", "/")
    while normalised.startswith("./"):
        normalised = normalised[2:]
    return normalised.lstrip("/")


@lru_cache(maxsize=4096)
def _compiled(pattern: str):
    # globmatch 每次调用都重新编译（展开花括号），几千个文件 × 几十个模式时占扫描耗时的八成
    return wglob.compile(pattern, flags=_GLOB_FLAGS)


def _matches(pattern: str, path: str) -> bool:
    pattern = _normalise_path(pattern).rstrip("/")
    if not WILDCARD.search(pattern):
        lp, lpath = pattern.lower(), path.lower()
        return lpath == lp or lpath.startswith(lp + "/")
    if _compiled(pattern).match(path):
        return True
    # Next.js 的 app/[id]、app/{slug} 这类目录名本身带方括号、花括号，也按字面匹配一次
    literal = re.sub(r"([\[\]{}])", r"\\\1", pattern)
    if literal == pattern:
        return False
    if not re.search(r"[*?]", pattern):
        lp, lpath = pattern.lower(), path.lower()
        return lpath == lp or lpath.startswith(lp + "/")
    return _compiled(literal).match(path)


def _item_path(item) -> str:
    return str(item["path"]) if isinstance(item, dict) else str(item)


class ModuleRegistry:
    def __init__(self, data: dict | None):
        data = data or {}
        if not isinstance(data, dict):
            raise RegistryError("modules.yaml 的顶层应是键值对（categories、modules 等）")
        for key in ("modules", "candidates", "categories", "entities"):
            if data.get(key) is not None and not isinstance(data[key], dict):
                raise RegistryError(f"modules.yaml 里的 {key} 应是键值对")
        # 没写 categories（文件为空或被删）时按已登记模块的大类推断，都没有时用通用预设；
        # 原先固定回落到游戏项目的四个大类，非游戏项目已有的 feature.* 记忆全部报“未知大类”
        declared = list((data.get("categories") or {}).keys())
        inferred = [mid.split(".", 1)[0] for mid in [*(data.get("modules") or {}), *(data.get("candidates") or {})]
                    if "." in str(mid)]
        self.categories: list[str] = declared or list(dict.fromkeys(inferred)) or list(DEFAULT_CATEGORIES)
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
            # 末尾几段也能当短名：AdMob.Android、Ads.AdMob.Android
            parts = module.path_name.split(".")
            for start in range(len(parts) - 1):
                self._bare_index.setdefault(".".join(parts[start:]).lower(), set()).add(mid)
            for alias in module.aliases:
                if "." in alias:
                    self._full_index.setdefault(alias.lower(), mid)
                else:
                    self._bare_index.setdefault(alias.lower(), set()).add(mid)
        self._candidate_index = {mid.lower(): mid for mid in self.candidates}

    @classmethod
    def load(cls, path: str | Path) -> ModuleRegistry:
        try:
            data = load_yaml(Path(path), encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise RegistryError(f"{Path(path).name} 不是 UTF-8 编码，请用 UTF-8 保存") from exc
        except Exception as exc:
            import yaml

            if not isinstance(exc, yaml.YAMLError):
                raise
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
            raise RegistryError("模块名不能为空，格式为 category.Name", "module_invalid")
        key = text.lower()
        if key in self._full_index:
            mid = self._full_index[key]
            return self._resolved(mid, mid if self.modules[mid].merged_into else None)

        # 不带大类的短名：最后一段（AdMob）或去掉大类的部分（Ads.AdMob）
        first = text.split(".", 1)[0].lower()
        if "." not in text or (first not in self.categories and key in self._bare_index):
            ids = self._bare_index.get(key)
            if not ids:
                raise RegistryError(f"未知模块 {text!r}，请使用 category.Name 格式，或先用 list_modules 查看",
                                    "module_invalid")
            if len(ids) > 1:
                raise RegistryError(f"模块名 {text!r} 有歧义：{', '.join(sorted(ids))}，请写全 category.Name",
                                    "module_invalid")
            mid = next(iter(ids))
            return self._resolved(mid, mid if self.modules[mid].merged_into else None)

        category, name = text.split(".", 1)
        category = category.lower()
        if category not in self.categories:
            raise RegistryError(f"未知大类 {category!r}，只允许：{' / '.join(self.categories)}", "category_unknown")
        parts = name.split(".")
        if len(parts) >= MAX_MODULE_DEPTH:
            raise RegistryError(f"模块名 {text!r} 超过 {MAX_MODULE_DEPTH} 段。{DEPTH_HINT}", "module_invalid")
        bad = next((p for p in parts if not _NAME_RE.match(p)), None)
        if bad is not None:
            raise RegistryError(f"模块名 {name!r} 不合法，每段只能包含字母、数字、下划线且以字母开头", "module_invalid")
        cand = self._candidate_index.get(f"{category}.{name}".lower())
        if cand:
            return ResolvedModule(cand, category, cand.split(".", 1)[1], known=False, candidate=True)
        if len(parts) > 1:
            # 未登记的子模块挂在已登记的父模块下，名字跟随父模块的写法；父模块也没登记就拒绝，免得随手造出一棵树
            parent_key = f"{category}.{'.'.join(parts[:-1])}".lower()
            if parent_key not in self._full_index:
                raise RegistryError(f"{text} 的父模块 {category}.{'.'.join(parts[:-1])} 未登记：先在 modules.yaml "
                                    "登记父模块，或写到已有模块（list_modules 查看）", "module_invalid")
            parent = self._follow_merge(self._full_index[parent_key])
            mid = f"{parent}.{parts[-1]}"
            if module_depth(mid) > MAX_MODULE_DEPTH:
                raise RegistryError(f"{text} 的父模块已并入 {parent}，挂上去会超过 {MAX_MODULE_DEPTH} 段。{DEPTH_HINT}",
                                    "module_invalid")
            mid_category, mid_name = mid.split(".", 1)
            return ResolvedModule(mid, mid_category, mid_name, known=False)
        return ResolvedModule(f"{category}.{name}", category, name, known=False)

    def name_patterns(self) -> dict[str, re.Pattern]:
        """文字里提到某个模块的匹配式：模块名与不带点的别名，英文至少 4 个字符且按词边界，中文至少 2 个字。"""
        patterns = {}
        for mid, module in self.modules.items():
            # 不同分支下同名的末段（两个 SDK 下都有 Android）认不出指的是哪个，只认全名
            names = [n for n in (module.name, *module.aliases)
                     if "." not in n and (module.depth <= 2 or len(self._bare_index.get(n.lower(), ())) <= 1)]
            names = [n for n in names if (len(n) >= MIN_ASCII_NAME if n.isascii() else len(n) >= 2)]
            if names:
                alternation = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
                patterns[mid] = re.compile(rf"(?<![A-Za-z0-9_])(?:{alternation})(?![A-Za-z0-9_])")
        return patterns

    # ---- 父子关系 ----

    def registered_ancestors(self, module_id: str) -> list[str]:
        """由近到远、已登记且未并入别处的祖先模块。"""
        return [a for a in (self._full_index.get(x.lower()) for x in ancestor_modules(module_id))
                if a is not None and not self.modules[a].merged_into]

    def children(self, module_id: str) -> list[str]:
        """已登记的直接子模块（并入别处的不算）。"""
        key = module_id.lower()
        return sorted(mid for mid, m in self.modules.items()
                      if not m.merged_into and (m.parent_id or "").lower() == key)

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
