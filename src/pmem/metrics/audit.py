"""健康报告里和模块目录有关的两项建议：未登记模块的转正提示、召回审计。只给建议，不改 modules.yaml。"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from pmem.core.entry import RECORD_KINDS
from pmem.core.registry import RegistryError

MAX_SUGGESTED_PATHS = 5
# 召回审计：现行教训至少这么多、本机按模块检索至少这么多次才判断，样本太小时“没被返回”说明不了问题
RECALL_MIN_LESSONS = 10
RECALL_MIN_SEARCHES = 10
RECALL_MAX_SHARE = 0.3
SPLIT_MIN_ENTITIES = 8
TOP = 10


def _anchor_files(root: Path, entries: list) -> list[str]:
    files = {a.partition("#")[0].replace("\\", "/") for e in entries for a in e.anchors}
    return sorted(f for f in files if f and (root / f).is_file())


def _suggest_paths(files: list[str]) -> list[str]:
    """同一目录下有 2 个以上关联文件的登记整个目录，否则登记单个文件。"""
    by_dir: dict[str, list[str]] = defaultdict(list)
    for f in files:
        by_dir[str(PurePosixPath(f).parent)].append(f)
    paths = []
    for folder, items in sorted(by_dir.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(items) >= 2 and folder != ".":
            paths.append(f"{folder}/**")
        else:
            paths.extend(items)
    return paths[:MAX_SUGGESTED_PATHS]


def promotion_hints(root: Path, registry, visible: list, unregistered: list[dict]) -> None:
    """给每个未登记模块补上 paths（建议登记的路径）和 owners（这些关联代码现在归哪个模块），原地修改。"""
    by_module: dict[str, list] = defaultdict(list)
    for e in visible:
        by_module[e.module].append(e)
    for row in unregistered:
        files = _anchor_files(root, by_module[row["module"]])
        owners: Counter = Counter()
        for f in files:
            try:
                match = registry.module_for_path(f)
            except RegistryError:
                match = None
            owners[match.module_id if match else "（未登记）"] += 1
        row["anchored_files"] = len(files)
        row["paths"] = _suggest_paths(files)
        row["owners"] = owners.most_common(3)


def recall_audit(registry, visible: list, searches: list[dict]) -> list[dict]:
    """记忆多、检索也多，但大部分教训从没被检索返回过的模块。searches 是本机成功的 search 事件。
    功能记录在检索里只给标题、不进 ids，所以只看教训。"""
    lessons: dict[str, list] = defaultdict(list)
    for e in visible:
        if e.kind not in RECORD_KINDS:
            lessons[e.module].append(e)
    asked = Counter(e.get("module") for e in searches if e.get("module"))
    returned = {i for e in searches for i in e.get("ids") or []}
    rows = []
    for mid, items in lessons.items():
        module = registry.modules.get(mid)
        if module is None or module.deprecated or module.merged_into:
            continue
        if len(items) < RECALL_MIN_LESSONS or asked[mid] < RECALL_MIN_SEARCHES:
            continue
        hit = [e for e in items if e.id in returned]
        if len(hit) / len(items) >= RECALL_MAX_SHARE:
            continue
        never = Counter(e.entity for e in items if e.id not in returned)
        rows.append({
            "module": mid, "lessons": len(items), "searches": asked[mid], "returned": len(hit),
            "entities": len({e.entity.lower() for e in items}),
            "never": never.most_common(3),
        })
    rows.sort(key=lambda r: (r["returned"] / r["lessons"], -r["lessons"]))
    return rows[:TOP]


def render_unregistered(u: dict) -> str:
    text = f"{u['module']}：{u['memories']} 条"
    if u["candidate"]:
        return text + "（冷候选，pmem sync --apply 可转正）"
    if u["similar"]:
        text += f"，相近：{'、'.join(u['similar'])}"
    if not u.get("paths"):
        return text + "；记忆没有关联代码，推断不出路径"
    owners = "、".join(f"{m} {n} 个" for m, n in u["owners"])
    return text + f"；关联代码 {u['anchored_files']} 个文件，现在归 {owners}；建议 paths: [{', '.join(u['paths'])}]"


def render_recall(r: dict) -> str:
    never = "、".join(f"{name}（{n} 条）" for name, n in r["never"])
    text = (f"{r['module']}：现行教训 {r['lessons']} 条、{r['entities']} 个议题，本机按模块检索 {r['searches']} 次，"
            f"被返回过的只有 {r['returned']} 条；从没返回的议题多是 {never}")
    if r["entities"] >= SPLIT_MIN_ENTITIES:
        text += "；议题较杂，可考虑拆模块"
    return text
