"""记忆的生命周期：核对（confirm）、归档与恢复、种子转正与退回。只改 YAML 头，正文与替代关系不变。"""
from __future__ import annotations

from datetime import date, datetime

from pmem.service.base import ServiceBase, fail, returns_errors
from pmem.storage.files import StorageError

# 动作 → (允许的原状态, 新状态)；记忆文件写入后只有这些状态变更由负责人通过命令行发起。
# restore 回到归档前的状态，没记录时才用 active
STATUS_ACTIONS = {
    "archive": (("active", "seed", "draft"), "archived"),
    "restore": (("archived",), "active"),
    "accept": (("seed",), "active"),
    "reject": (("seed",), "archived"),
}


class StatusOps(ServiceBase):
    # ---- confirm_memory ----

    def confirm(self, ids: list[str], source_conversation: str | None = None) -> dict:
        """核对过关联代码、仍然成立的记忆：把核对日期记为今天，之后不再因更早的代码改动标为 stale。"""
        now = datetime.now().astimezone()
        today = now.date().isoformat()
        confirmed, missing, invalid = [], [], []
        for entry_id in dict.fromkeys(i for i in ids or [] if i):
            path = self.storage.find_path(entry_id)
            if path is None:
                missing.append(entry_id)
                continue
            try:
                entry = self.storage.read(path)
                entry.verified = today
                entry.verified_at = now.isoformat(timespec="milliseconds")
                self.storage.rewrite(path, entry)
            except StorageError as exc:
                invalid.append({"id": entry_id, "error": str(exc)})
                continue
            confirmed.append(entry_id)
        self._log("confirm", conv=source_conversation, ids=confirmed)
        response: dict = {"ok": bool(confirmed) or not (missing or invalid), "confirmed": confirmed,
                          "verified": today}
        if missing:
            response["missing"] = missing
        if invalid:
            response["invalid"] = invalid
        if confirmed:
            self.index.refresh(force=True)
            self._refresh_wiki(response)
        return response

    # ---- archive / seed ----

    def change_status(self, ids: list[str], action: str) -> dict:
        """归档、恢复、种子转正或退回。只改 YAML 头的状态，正文与替代关系不变。
        归档时记下日期和原状态：按日期回看时那天之后才归档的仍算有效，恢复时回到原状态。"""
        allowed, target = STATUS_ACTIONS[action]
        today = date.today().isoformat()
        changed, missing, skipped, invalid = [], [], [], []
        statuses: dict[str, str] = {}
        for entry_id in dict.fromkeys(i for i in ids or [] if i):
            path = self.storage.find_path(entry_id)
            if path is None:
                missing.append(entry_id)
                continue
            try:
                entry = self.storage.read(path)
            except StorageError as exc:
                invalid.append({"id": entry_id, "error": str(exc)})
                continue
            if entry.status not in allowed:
                skipped.append({"id": entry_id, "status": entry.status})
                continue
            if target == "archived":
                entry.archived_on, entry.archived_from, entry.archived_by = today, entry.status, self.user
                entry.status = target
            else:
                entry.status = (entry.archived_from or target) if action == "restore" else target
                entry.archived_on = entry.archived_from = entry.archived_by = None
                # 恢复撤销过的合并产物 = 重做这次合并，它替代的记忆重新隐藏
                entry.reverted_on = entry.reverted_by = None
            try:
                self.storage.rewrite(path, entry)
            except StorageError as exc:
                invalid.append({"id": entry_id, "error": str(exc)})
                continue
            changed.append(entry_id)
            statuses[entry_id] = entry.status
        self._log("status", action=action, ids=changed)
        # restore 回到各自归档前的状态，不一定是 target；状态不一致时 status 为 mixed，逐条见 statuses
        distinct = set(statuses.values()) or {target}
        response: dict = {"ok": bool(changed) or not (missing or skipped or invalid), "action": action,
                          "status": next(iter(distinct)) if len(distinct) == 1 else "mixed", "changed": changed}
        if len(distinct) > 1:
            response["statuses"] = statuses
        if missing:
            response["missing"] = missing
        if skipped:
            response["skipped"] = skipped
        if invalid:
            response["invalid"] = invalid
        if changed:
            self.index.refresh(force=True)
            self._refresh_wiki(response)
        return response

    @returns_errors
    def revert(self, entry_id: str) -> dict:
        """撤销一次合并（或替代）：这条归档并标为已撤销，它替代的原记忆重新现行。
        只归档不能做到这一点：归档记忆的替代关系仍然算数（归档表示整条演进线过时）。"""
        path = self.storage.find_path(entry_id)
        if path is None:
            return fail(f"找不到记忆 {entry_id}")
        entry = self.storage.read(path)
        if entry.reverted_on:
            return fail(f"{entry_id} 已在 {entry.reverted_on} 撤销过；要重做这次合并用 pmem archive --restore {entry_id}")
        if not entry.supersedes:
            return fail(f"{entry_id} 没有替代任何记忆，不是合并产物；只想停用它用 pmem archive {entry_id}")
        newer = sorted(e.id for e in self.index.entries() if entry.id in e.replaces())
        if newer:
            return fail(f"{entry_id} 已被 {'、'.join(newer)} 替代，撤销它也不会让原记忆复现；先撤销或处理这几条")
        today = date.today().isoformat()
        if entry.status != "archived":
            entry.archived_on, entry.archived_from, entry.archived_by = today, entry.status, self.user
            entry.status = "archived"
        entry.reverted_on, entry.reverted_by = today, self.user
        self.storage.rewrite(path, entry)
        self._log("status", action="revert", ids=[entry_id])
        self.index.refresh(force=True)
        hidden = self.index.superseded()
        restored, kept = [], []
        for old_id in entry.supersedes:
            old = self.index.find(old_id)
            if old is None:
                kept.append({"id": old_id, "reason": "找不到这条记忆"})
            elif old.status == "archived":
                kept.append({"id": old_id, "reason": f"已归档，需要时 pmem archive --restore {old_id}"})
            elif old_id in hidden:
                kept.append({"id": old_id, "reason": "仍被别的记忆替代"})
            else:
                restored.append(old_id)
        response: dict = {"ok": True, "id": entry_id, "status": "archived", "restored": restored}
        if kept:
            response["not_restored"] = kept
        self._refresh_wiki(response)
        return response

    @returns_errors
    def seeds(self, module: str | None = None) -> dict:
        """待确认的种子记忆，按模块、议题排列。"""
        module = self._module_id(module) if module else None
        rows = [
            {"id": e.id, "module": e.module, "entity": e.entity, "kind": e.kind, "date": e.note_date,
             "author": e.author, "preview": e.title}
            for e in sorted(self.index.visible(), key=lambda e: (e.module, e.entity.lower(), e.id))
            if e.status == "seed" and (module is None or e.module == module)
        ]
        return {"ok": True, "module": module, "seeds": rows}
