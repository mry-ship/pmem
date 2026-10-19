"""记忆的生命周期：核对（confirm）、归档与恢复、种子转正与退回。只改 YAML 头，正文与替代关系不变。"""
from __future__ import annotations

from datetime import date

from pmem.index.graph import preview
from pmem.service.base import ServiceBase, returns_errors

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
        today = date.today().isoformat()
        confirmed, missing = [], []
        for entry_id in dict.fromkeys(i for i in ids or [] if i):
            path = self.storage.find_path(entry_id)
            if path is None:
                missing.append(entry_id)
                continue
            entry = self.storage.read(path)
            entry.verified = today
            path.write_text(entry.to_markdown(), encoding="utf-8", newline="\n")
            confirmed.append(entry_id)
        self._log("confirm", conv=source_conversation, ids=confirmed)
        response: dict = {"ok": bool(confirmed) or not missing, "confirmed": confirmed, "verified": today}
        if missing:
            response["missing"] = missing
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
        changed, missing, skipped = [], [], []
        statuses: dict[str, str] = {}
        for entry_id in dict.fromkeys(i for i in ids or [] if i):
            path = self.storage.find_path(entry_id)
            if path is None:
                missing.append(entry_id)
                continue
            entry = self.storage.read(path)
            if entry.status not in allowed:
                skipped.append({"id": entry_id, "status": entry.status})
                continue
            if target == "archived":
                entry.archived_on, entry.archived_from, entry.archived_by = today, entry.status, self.user
                entry.status = target
            else:
                entry.status = (entry.archived_from or target) if action == "restore" else target
                entry.archived_on = entry.archived_from = entry.archived_by = None
            path.write_text(entry.to_markdown(), encoding="utf-8", newline="\n")
            changed.append(entry_id)
            statuses[entry_id] = entry.status
        self._log("status", action=action, ids=changed)
        # restore 回到各自归档前的状态，不一定是 target；状态不一致时 status 为 mixed，逐条见 statuses
        distinct = set(statuses.values()) or {target}
        response: dict = {"ok": bool(changed) or not (missing or skipped), "action": action,
                          "status": next(iter(distinct)) if len(distinct) == 1 else "mixed", "changed": changed}
        if len(distinct) > 1:
            response["statuses"] = statuses
        if missing:
            response["missing"] = missing
        if skipped:
            response["skipped"] = skipped
        if changed:
            self.index.refresh(force=True)
            self._refresh_wiki(response)
        return response

    @returns_errors
    def seeds(self, module: str | None = None) -> dict:
        """待确认的种子记忆，按模块、议题排列。"""
        module = self._module_id(module) if module else None
        rows = [
            {"id": e.id, "module": e.module, "entity": e.entity, "kind": e.kind, "date": e.note_date,
             "author": e.author, "preview": preview(e.content)}
            for e in sorted(self.index.visible(), key=lambda e: (e.module, e.entity.lower(), e.id))
            if e.status == "seed" and (module is None or e.module == module)
        ]
        return {"ok": True, "module": module, "seeds": rows}
