"""包之间的依赖方向（docs/architecture.md「分层」一节）。新增依赖先想清楚该放哪一层，再改这里。"""
import ast
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "pmem"

# metrics.events 是谁都能写的事件日志，单独算一层；metrics 的其他文件（report、health）是最上层的汇总
EVENTS = "metrics.events"
ALLOWED = {
    "core": set(),
    EVENTS: {"core"},
    "vcs": {"core"},
    "storage": {"core", "vcs"},
    "scan": {"core", "vcs"},
    "index": {"core", "storage", "vcs"},
    "catalog": {"core", "scan", "storage", "vcs"},
    "generate": {"core", "index"},
    "importers": {"core", "storage", "catalog"},
    "service": {"core", "vcs", "storage", "index", "generate", EVENTS},
    "hooks": {"core", "vcs", "index", EVENTS},
    "server": {"core", "service", EVENTS},
    "metrics": {"core", "vcs", "storage", "scan", "index", "catalog", "service", EVENTS},
    "bench": {"core", "generate"},
}


def _layer(parts: tuple[str, ...]) -> str:
    if parts[:2] == ("metrics", "events"):
        return EVENTS
    return parts[0]


def _imports():
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC).with_suffix("").parts
        if len(rel) == 1:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("pmem."):
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names if a.name.startswith("pmem.")]
            for name in names:
                yield "/".join(rel), _layer(rel), _layer(tuple(name.split(".")[1:]) + ("",))


def test_every_package_has_a_layer():
    packages = {p.name for p in SRC.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
    assert packages - {"cli"} <= set(ALLOWED), "新包要在 ALLOWED 里登记它能依赖哪些包"


def test_hook_process_stays_light():
    """每次工具调用都起一个 Hook 进程，导入 numpy、yaml、服务层会让每次调用多等几百毫秒。"""
    code = ("import sys, pmem.cli.hook_cmd, pmem.hooks.gate; "
            "print(','.join(m for m in ('numpy', 'yaml', 'pmem.service', 'pmem.index.store') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
    assert out == ""


def test_packages_only_depend_downwards():
    bad = sorted(f"{file} -> {target}" for file, layer, target in _imports()
                 if layer != "cli" and target != layer and target not in ALLOWED.get(layer, set()))
    assert not bad, "越层依赖：\n" + "\n".join(bad)
