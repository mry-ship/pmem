from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from pathlib import Path

MEMORY_DIR = ".memory"
CONFIG_FILE = "config.yaml"

DEFAULTS: dict = {
    "schema_version": 1,
    "project": {"name": "", "type": "generic", "language": "zh"},
    "vcs": "auto",
    "svn_auto_add": True,
    "embedding": {"backend": "auto", "model": "", "model_path": "", "base_url": ""},
    "gate": {
        "mode": "block",
        "watch": [],
        "ignore": ["**/*.md", "docs/**", ".memory/**", ".cursor/**", ".claude/**", ".codex/**", ".agents/**"],
        "skip_markers": ["跳过记忆", "skip-memory"],
        "resume_markers": ["恢复记忆", "resume-memory"],
        "stop_reminder": True,
        "analysis_reminder": False,
        "read_digest": True,
        "question_review": True,
        # 只改了这些文件的模块，结束时不提醒写功能记录（改前的记忆检查照旧）
        "record_exempt": [
            "**/test/**", "**/tests/**", "**/__tests__/**", "**/test_*.*", "**/*_test.*", "**/*.test.*",
            "**/*.spec.*", "**/generated/**", "**/*.generated.*", "**/*.g.cs", "**/*_pb2.py", "**/*.pb.*",
            "**/*.json", "**/*.yaml", "**/*.yml", "**/*.toml", "**/*.ini", "**/*.cfg", "**/*.lock", "**/*.meta",
            "**/*.md", "**/docs/**",
        ],
        "analysis_markers": [
            "为什么", "原因", "根因", "排查", "定位", "分析", "怎么回事", "复现", "报错", "崩溃", "闪退",
            "卡死", "不生效", "异常", "bug", "why", "debug", "investigate",
        ],
    },
    "write": {
        "default_status": "active",
        "content_min": 20,
        "content_max": 5000,
        "recommend_max": 600,
        "max_per_day_per_entity": 5,
        "secret_patterns": [],
    },
    "search": {"limit": 5, "max_per_batch": 2, "recency_half_life_days": 90, "feature_limit": 3, "inherit_max": 2},
    "wiki": {"auto": True, "dir": ".memory/wiki"},
    "spec": {"dir": ".memory/specs", "reminder": True, "read_before_edit": True},
    "server": {"watchdog": True, "request_timeout": 120},
    # 自动发现没登记的代码目录：改到这类文件时立即、会话开始时按间隔在后台扫描；full_hours 内至少一次带提交热度的完整扫描
    "sync": {"auto": "apply", "interval_minutes": 30, "full_hours": 24},
    # 实验：没有记忆也能给的改前提示（常一起改的文件、近期修复提交、规格必须保持）与回合结束的漏改/未验证检查；off 时行为与以前完全一致
    "harness": {"mode": "off", "window_days": 180, "min_pair": 3, "min_ratio": 0.3, "max_files": 3,
                "refresh_hours": 24, "verify_commands": []},
    # v0.7：健康报告「可以写成规则的教训」阈值
    "health": {"rule_min": 3, "rule_searches": 5},
    # v0.7：结构化适用条件维度；空 = 未启用 when
    "facets": {},
}

_LIST_KEYS = ("harness.verify_commands", "gate.watch", "gate.ignore", "gate.skip_markers", "gate.resume_markers",
              "gate.analysis_markers", "gate.record_exempt")
# 数值配置项：（最小值, 类型）；写成字符串或负数会在写入、检索时才抛异常栈
_NUMBERS = {
    "write.content_min": (0, int), "write.content_max": (1, int), "write.recommend_max": (1, int),
    "write.max_per_day_per_entity": (1, int), "search.limit": (1, int), "search.max_per_batch": (1, int),
    "search.recency_half_life_days": (1, float), "search.feature_limit": (0, int), "search.inherit_max": (0, int),
    "server.request_timeout": (1, float), "sync.interval_minutes": (0, float), "sync.full_hours": (1, float),
    "harness.window_days": (1, int), "harness.min_pair": (1, int), "harness.min_ratio": (0, float),
    "harness.max_files": (1, int), "harness.refresh_hours": (1, float),
    "health.rule_min": (1, int), "health.rule_searches": (1, int),
}
_CHOICES = {
    "vcs": ("auto", "git", "svn", "none"),
    "gate.mode": ("off", "warn", "block"),
    "write.default_status": ("active", "draft"),
    "embedding.backend": ("auto", "onnx", "ollama", "openai", "none"),
    "sync.auto": ("off", "remind", "apply"),
    "harness.mode": ("off", "hint", "check"),
}


class ConfigError(ValueError):
    pass


_CONFIG_PATH = f"{MEMORY_DIR}/{CONFIG_FILE}"
# facets 维度超过此数时 doctor 提醒（设计稿风险：写记忆负担变重）
FACETS_SOFT_MAX = 4


def _known_config_keys() -> dict[str, set[str] | None]:
    """DEFAULTS 推导：节 → 允许的子键；标量顶层键的子键表为 None。facets 维度名自由，不查子键。"""
    known: dict[str, set[str] | None] = {}
    for key, value in DEFAULTS.items():
        if key == "facets":
            known[key] = None
        elif isinstance(value, dict):
            known[key] = set(value)
        else:
            known[key] = None
    return known


def _merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def find_root(start: str | Path) -> Path | None:
    """从 start 向上查找包含 .memory/config.yaml 的目录。"""
    current = Path(start).resolve()
    for candidate in (current, *current.parents):
        if (candidate / MEMORY_DIR / CONFIG_FILE).is_file():
            return candidate
    return None


def user_cache_base() -> Path:
    if env := os.environ.get("PMEM_CACHE_DIR"):
        return Path(env)
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "pmem"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "pmem"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "pmem"


def load_yaml(path: Path, encoding: str = "utf-8"):
    """读 YAML；解析结果按文件修改时间缓存成 JSON，钩子这类短进程命中时不必导入 yaml（约 30 毫秒）。"""
    stat = path.stat()
    stamp = [stat.st_mtime_ns, stat.st_size]
    key = hashlib.sha1(str(path.resolve()).lower().encode("utf-8")).hexdigest()[:16]
    cache = user_cache_base() / "parsed" / f"{key}.json"
    try:
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if cached.get("stamp") == stamp:
            return cached.get("value")
    except (OSError, ValueError, AttributeError):
        pass
    import yaml

    value = yaml.safe_load(path.read_text(encoding=encoding))
    try:
        text = json.dumps({"stamp": stamp, "value": value}, ensure_ascii=False)
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, cache)
    except (OSError, TypeError, ValueError):
        pass
    return value


class Config:
    def __init__(self, root: Path, data: dict, *, warnings: list[str] | None = None):
        from pmem.core.schema import SchemaError, expect_list, expect_mapping, expect_number, expect_one_of

        self.root = root
        self.data = data
        self.warnings: list[str] = list(warnings or [])
        for section in ("gate", "write", "search", "server", "embedding", "wiki", "project", "sync", "spec",
                        "harness", "health", "facets"):
            try:
                expect_mapping(data.get(section), f"{_CONFIG_PATH}：{section}")
            except SchemaError as exc:
                raise ConfigError(str(exc)) from exc
        from pmem.core.facets import FacetError, parse_facets

        try:
            self.facets = parse_facets(data.get("facets"))
        except FacetError as exc:
            raise ConfigError(f"{_CONFIG_PATH}：{exc}") from exc
        if len(self.facets) > FACETS_SOFT_MAX:
            self.warnings.append(
                f"{_CONFIG_PATH}：facets 已声明 {len(self.facets)} 个维度，建议不超过 {FACETS_SOFT_MAX} 个，"
                "否则写记忆负担变重")
        gate = data["gate"]
        if isinstance(gate.get("mode"), bool):
            gate["mode"] = "warn" if gate["mode"] else "off"
        # YAML 把不加引号的 off / on 读成布尔值
        if isinstance(data["sync"].get("auto"), bool):
            data["sync"]["auto"] = "apply" if data["sync"]["auto"] else "off"
        # 同样，不加引号的 harness.mode: off 会被读成 False
        if isinstance(data["harness"].get("mode"), bool):
            data["harness"]["mode"] = "hint" if data["harness"]["mode"] else "off"
        for key, allowed in _CHOICES.items():
            try:
                expect_one_of(self.get(key), f"{_CONFIG_PATH}：{key}", allowed)
            except SchemaError as exc:
                raise ConfigError(str(exc)) from exc
        for key in _LIST_KEYS:
            section, name = key.split(".")
            value = data[section].get(name)
            if value is None:
                continue
            try:
                data[section][name] = expect_list(value, f"{_CONFIG_PATH}：{key}")
            except SchemaError as exc:
                raise ConfigError(str(exc)) from exc
        for key, (low, kind) in _NUMBERS.items():
            try:
                number = expect_number(self.get(key), f"{_CONFIG_PATH}：{key}", minimum=low)
            except SchemaError as exc:
                raise ConfigError(str(exc)) from exc
            if kind is int and number != int(number):
                raise ConfigError(f"{_CONFIG_PATH}：{key} 应是整数，实际是 {self.get(key)!r}")
        content_max = float(self.get("write.content_max") or 0)
        content_min = float(self.get("write.content_min") or 0)
        if content_max < content_min:
            raise ConfigError(f"{_CONFIG_PATH}：write.content_max 不能小于 write.content_min")
        # secret_patterns 不把单个字符串升成列表：那会变成按字符匹配的一串「正则」
        patterns = self.get("write.secret_patterns") or []
        if not isinstance(patterns, list):
            raise ConfigError(f"{_CONFIG_PATH}：write.secret_patterns 应是正则表达式列表")
        for pattern in patterns:
            try:
                re.compile(str(pattern))
            except re.error as exc:
                raise ConfigError(
                    f"{_CONFIG_PATH}：write.secret_patterns 里的 {pattern!r} 不是有效的正则：{exc}") from exc

    @classmethod
    def load(cls, root: str | Path) -> Config:
        from pmem.core.schema import unknown_key_warnings

        root = Path(root).resolve()
        path = root / MEMORY_DIR / CONFIG_FILE
        try:
            raw = load_yaml(path) if path.exists() else None
        except Exception as exc:
            raise ConfigError(f"{_CONFIG_PATH} 无法解析：{exc}") from exc
        if raw is not None and not isinstance(raw, dict):
            raise ConfigError(f"{_CONFIG_PATH} 的顶层应是键值对，当前为 {type(raw).__name__}")
        warnings = unknown_key_warnings(raw or {}, _known_config_keys(), file_path=_CONFIG_PATH)
        data = _merge(DEFAULTS, raw or {})
        # YAML 写「facets:」或 facets: null 会盖掉默认 {}；按设计空=未启用 when
        if data.get("facets") is None:
            data["facets"] = {}
        return cls(root, data, warnings=warnings)

    def get(self, dotted: str, default=None):
        node = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    @property
    def memory_dir(self) -> Path:
        return self.root / MEMORY_DIR

    @property
    def entries_dir(self) -> Path:
        return self.memory_dir / "entries"

    @property
    def modules_path(self) -> Path:
        return self.memory_dir / "modules.yaml"

    @property
    def cache_dir(self) -> Path:
        digest = hashlib.sha1(str(self.root).lower().encode("utf-8")).hexdigest()[:12]
        name = self.get("project.name") or self.root.name
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:32]
        return user_cache_base() / f"{safe}-{digest}"
