from __future__ import annotations

import importlib.util
from pathlib import Path

from pmem.catalog.yamlfile import ModulesFile
from pmem.core.config import Config
from pmem.importers.lancedb import catalog_from_reference, import_rows, read_rows
from pmem.storage.files import FilesStorage
from pmem.vcs.detect import detect_vcs


def _merge_catalog(modules_path: Path, catalog: dict | None, table_modules: set[str]) -> int:
    """模块目录还没有模块时，用参考目录与源库中出现的模块填充；返回新增模块数。"""
    file = ModulesFile.read(modules_path)
    data = file.data or {"schema_version": 1}
    if data.get("modules"):
        return 0
    modules = dict((catalog or {}).get("modules") or {})
    categories = dict(data.get("categories") or {})
    categories.update((catalog or {}).get("categories") or {})
    for module in table_modules:
        modules.setdefault(module, {})
        categories.setdefault(module.split(".", 1)[0], {})
    data["categories"], data["modules"] = categories, dict(sorted(modules.items()))
    file.write(data)
    return len(modules)


def run_import(root: Path, lancedb_dir: Path, catalog: Path | None, author: str, dry_run: bool,
               infer_kind: bool) -> int:
    if importlib.util.find_spec("lancedb") is None:
        print("缺少 lancedb：uv tool install 'pmem[embed,import]' 或在当前环境 pip install lancedb")
        return 2
    if not lancedb_dir.is_dir():
        print(f"找不到 LanceDB 目录：{lancedb_dir}")
        return 2
    config = Config.load(root)
    rows, tables = read_rows(lancedb_dir)
    modules = {r["module"] for r in rows}
    if not dry_run:
        added = _merge_catalog(config.modules_path, catalog_from_reference(catalog) if catalog else None, modules)
        if added:
            print(f"模块目录为空，已按源库与参考目录写入 {added} 个模块（没有路径，按文件检索前请补 paths）")
    storage = FilesStorage(root, detect_vcs(root, config.get("vcs")), bool(config.get("svn_auto_add")))
    report = import_rows(rows, storage, author, dry_run=dry_run, infer_kind=infer_kind,
                         secret_patterns=config.get("write.secret_patterns") or [])
    verb = "将导入" if dry_run else "已导入"
    print(f"读取 {tables} 张表、{len(rows)} 条记忆；{verb} {sum(report.written.values())} 条，"
          f"覆盖 {len(report.written)} 个模块")
    if report.kinds:
        print("  类型：" + "、".join(f"{k} {n}" for k, n in report.kinds.most_common()))
    if report.skipped_existing:
        print(f"  跳过已导入过的 {report.skipped_existing} 条")
    if report.skipped_empty:
        print(f"  跳过正文为空的 {report.skipped_empty} 条")
    if report.skipped_secret:
        print(f"  疑似含敏感信息而跳过 {len(report.skipped_secret)} 条：" + "、".join(report.skipped_secret[:10]))
    return 0
