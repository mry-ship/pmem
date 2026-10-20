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
        "analysis_reminder": True,
        "read_digest": True,
        "question_review": True,
        # 只改了这些文件的模块，结束时不提醒写功能记录（改前的记忆检查照旧）
        "record_exempt": [
            "**/test/**", "**/tests/**", "**/__tests__/**", "**/test_*.*", "**/*_test.*", "**/*.test.*",
            "**/*.spec.*", "**/generated/**", "**/*.generated.*", "**/*.g.cs", "**/*_pb2.py", "**/*.pb.*",
            "**/*.json", "**/*.yaml", "**/*.yml", "**/*.toml", "**/*.ini", "**/*.cfg", "**/*.lock", "**/*.meta",
        ],
        "analysis_markers": [
            "为什么", "原因", "根因", "排查", "定位", "分析", "怎么回事", "复现", "报错", "崩溃", "闪退",
            "卡死", "不生效", "异常", "bug", "why", "debug", "investigate",
        ],
    },
    "write": {
        "default_status": "active",
        "content_min": 20,
        "content_max": 1200,
        "recommend_max": 600,
        "max_per_day_per_entity": 5,
        "secret_patterns": [],
    },
    "search": {"limit": 5, "max_per_batch": 2, "recency_half_life_days": 90, "feature_limit": 3},
    "wiki": {"auto": True, "dir": ".memory/wiki"},
    "server": {"watchdog": True, "request_timeout": 120},
}

_LIST_KEYS = ("gate.watch", "gate.ignore", "gate.skip_markers", "gate.resume_markers", "gate.analysis_markers",
              "gate.record_exempt")
# 数值配置项：（最小值, 类型）；写成字符串或负数会在写入、检索时才抛异常栈
_NUMBERS = {
    "write.content_min": (0, int), "write.content_max": (1, int), "write.recommend_max": (1, int),
    "write.max_per_day_per_entity": (1, int), "search.limit": (1, int), "search.max_per_batch": (1, int),
    "search.recency_half_life_days": (1, float), "search.feature_limit": (0, int), "server.request_timeout": (1, float),
}
_CHOICES = {
    "vcs": ("auto", "git", "svn", "none"),
    "gate.mode": ("off", "warn", "block"),
    "write.default_status": ("active", "draft"),
    "embedding.backend": ("auto", "onnx", "ollama", "openai", "none"),
}


class ConfigError(ValueError):
    pass


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
    def __init__(self, root: Path, data: dict):
        self.root = root
        self.data = data
        for section in ("gate", "write", "search", "server", "embedding", "wiki", "project"):
            if not isinstance(data.get(section), dict):
                raise ConfigError(f"配置项 {section} 应是键值对，当前为 {data.get(section)!r}")
        gate = data["gate"]
        if isinstance(gate.get("mode"), bool):
            gate["mode"] = "warn" if gate["mode"] else "off"
        for key, allowed in _CHOICES.items():
            value = self.get(key)
            if value not in allowed:
                raise ConfigError(f"配置项 {key} 只能是 {' / '.join(allowed)}，当前为 {value!r}")
        for key in _LIST_KEYS:
            section, name = key.split(".")
            value = data[section].get(name)
            if isinstance(value, str):
                # 只写了一项时常写成字符串；按字符逐个匹配会让闸门静默失效
                data[section][name] = [value]
            elif value is not None and not isinstance(value, list):
                raise ConfigError(f"配置项 {key} 应是列表，当前为 {value!r}")
        for key, (low, kind) in _NUMBERS.items():
            value = self.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or (kind is int and value != int(value)):
                raise ConfigError(f"配置项 {key} 应是{'整数' if kind is int else '数字'}，当前为 {value!r}")
            if value < low:
                raise ConfigError(f"配置项 {key} 不能小于 {low}，当前为 {value!r}")
        if self.get("write.content_max") < self.get("write.content_min"):
            raise ConfigError("配置项 write.content_max 不能小于 write.content_min")
        patterns = self.get("write.secret_patterns") or []
        if not isinstance(patterns, list):
            raise ConfigError("配置项 write.secret_patterns 应是正则表达式列表")
        for pattern in patterns:
            try:
                re.compile(str(pattern))
            except re.error as exc:
                raise ConfigError(f"配置项 write.secret_patterns 里的 {pattern!r} 不是有效的正则：{exc}") from exc

    @classmethod
    def load(cls, root: str | Path) -> Config:
        root = Path(root).resolve()
        path = root / MEMORY_DIR / CONFIG_FILE
        try:
            raw = load_yaml(path) if path.exists() else None
        except Exception as exc:
            raise ConfigError(f"{MEMORY_DIR}/{CONFIG_FILE} 无法解析：{exc}") from exc
        if raw is not None and not isinstance(raw, dict):
            raise ConfigError(f"{MEMORY_DIR}/{CONFIG_FILE} 的顶层应是键值对，当前为 {type(raw).__name__}")
        return cls(root, _merge(DEFAULTS, raw or {}))

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
