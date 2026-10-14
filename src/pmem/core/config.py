from __future__ import annotations

import copy
import hashlib
import os
import sys
from pathlib import Path

import yaml

MEMORY_DIR = ".memory"
CONFIG_FILE = "config.yaml"

DEFAULTS: dict = {
    "schema_version": 1,
    "project": {"name": "", "type": "generic", "language": "zh"},
    "vcs": "auto",
    "svn_auto_add": True,
    "embedding": {"backend": "auto", "model": "", "model_path": "", "base_url": ""},
    "gate": {
        "mode": "warn",
        "watch": [],
        "ignore": ["**/*.md", "docs/**", ".memory/**", ".cursor/**"],
        "skip_markers": ["跳过记忆", "skip-memory"],
    },
    "write": {
        "default_status": "active",
        "content_min": 20,
        "content_max": 1200,
        "max_per_day_per_entity": 5,
        "secret_patterns": [],
    },
    "search": {"limit": 5, "max_per_batch": 2, "recency_half_life_days": 90},
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


class Config:
    def __init__(self, root: Path, data: dict):
        self.root = root
        self.data = data
        for key, allowed in _CHOICES.items():
            value = self.get(key)
            if value not in allowed:
                raise ConfigError(f"配置项 {key} 只能是 {' / '.join(allowed)}，当前为 {value!r}")

    @classmethod
    def load(cls, root: str | Path) -> Config:
        root = Path(root).resolve()
        path = root / MEMORY_DIR / CONFIG_FILE
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None
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
