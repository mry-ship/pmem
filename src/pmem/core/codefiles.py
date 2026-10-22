"""哪些文件算代码、哪些目录不扫描。目录扫描（scan）和 Hook 判断“改到了没登记的目录”共用这一份。"""
from __future__ import annotations

import os

CODE_EXTS = {
    ".cs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".vue", ".svelte", ".py", ".go", ".java", ".kt", ".kts",
    ".swift", ".m", ".mm", ".c", ".cc", ".cpp", ".h", ".hpp", ".rs", ".rb", ".php", ".lua", ".dart",
    ".scala", ".gd", ".shader", ".hlsl", ".sql", ".proto",
}
SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "obj", "bin", "build", "dist", "out",
    ".venv", "venv", "__pycache__", ".idea", ".vs", ".vscode", ".cursor", ".memory", "target", ".gradle",
    ".next", ".nuxt", "coverage", ".pytest_cache", ".ruff_cache",
    # Go / PHP 依赖、iOS 依赖与构建产物、.NET 测试结果、Python 安装目录
    "vendor", "Pods", "Carthage", "DerivedData", "TestResults", "site-packages",
}
SKIP_SUFFIXES = (".egg-info",)


def skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".") or name.endswith(SKIP_SUFFIXES)


def is_code_file(rel: str) -> bool:
    """项目内相对路径是否是扫描会计入的代码文件（不在依赖、构建产物、隐藏目录里）。"""
    parts = rel.replace("\\", "/").split("/")
    return os.path.splitext(parts[-1])[1].lower() in CODE_EXTS and not any(skip_dir(p) for p in parts[:-1])
