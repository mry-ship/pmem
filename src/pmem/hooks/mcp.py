"""pmem 工具调用：MCP 的 search/record 与终端里的 pmem 命令，登记查过、写过，写入时补草稿 id 和锚点。"""

from __future__ import annotations

import json
import re

from pmem.core import seen
from pmem.core.entry import RECORD_KINDS
from pmem.core.ids import ULID_PATTERN
from pmem.hooks.payload import tool_input
from pmem.hooks.shell import cli_args, scan
from pmem.hooks.snapshot import MAX_PENDING_SNAPSHOTS, command_key

ALLOW = {"permission": "allow"}
PMEM_TOOLS = ("record_memory", "search_memory", "memory_graph")
MAX_AUTO_ANCHORS = 5
_OUTPUT_FIELDS = ("tool_output", "tool_response", "output")

def tool_response(payload: dict) -> dict | None:
    """pmem 工具的返回 JSON。各家包装不同（Cursor 的 result_json 是多层转义的字符串，
    Claude / Codex 的 tool_response 是内容块列表），逐层解开找带 ok 的对象；tool_input 不看。"""

    def walk(value, level: int):
        if level > 8:
            return None
        if isinstance(value, str):
            text = value.strip().lstrip("\ufeff")
            if text[:1] not in ("{", "["):
                return None
            try:
                return walk(json.loads(text), level + 1)
            except ValueError:
                return None
        if isinstance(value, dict):
            if "ok" in value:
                return value
            children = list(value.values())
        elif isinstance(value, list):
            children = value
        else:
            return None
        for child in children:
            found = walk(child, level + 1)
            if found is not None:
                return found
        return None

    return walk({k: v for k, v in payload.items() if k != "tool_input"}, 0)


def shell_output(payload: dict) -> str | None:
    """终端命令执行后的输出文本（Cursor 的 tool_output、Claude Code / Codex 的 tool_response）；载荷里没有时返回 None。"""
    for key in _OUTPUT_FIELDS:
        value = payload.get(key)
        if value is None:
            continue
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return None


_SERVER_FIELDS = ("server", "server_name", "mcp_server", "url", "command")


def foreign_tool(payload: dict) -> bool:
    """同名的 search_memory 等工具来自别家记忆服务。工具名或载荷里带了服务信息且不是 pmem 时为 True；
    都没带时无法区分，按 pmem 处理。"""
    name = str(payload.get("tool_name") or "").lower()
    if name.startswith("mcp__"):
        return "pmem" not in name
    for key in _SERVER_FIELDS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return "pmem" not in value.lower()
    return False


def draft_key(module: str, entity: str | None, kind: str | None = None) -> str:
    """同一议题下的功能记录和教训是两条记忆，草稿分开登记，否则后写的会覆盖先写的。"""
    key = f"{module}|{(entity or '').strip().lower()}"
    return f"{key}|record" if kind in RECORD_KINDS else key


class McpCalls:
    def _note_cli_calls(self, command: str) -> set[str]:
        """终端里的 pmem search/graph/record 与 MCP 工具等价。都先挂起，命令执行完、看得到结果才登记
        （见 _confirm_cli_calls）；返回这条命令里检索的模块。"""
        searches = cli_args(command, "search") + cli_args(command, "graph")
        records = cli_args(command, "record")
        if self.state is not None and (searches or records):
            for field, calls in (("cli_pending", searches), ("cli_record_pending", records)):
                if calls:
                    pending = self.state.data[field]
                    pending[command_key(command)] = calls
                    self.state.data[field] = dict(list(pending.items())[-MAX_PENDING_SNAPSHOTS:])
            self.save()
        claimed: set[str] = set()
        for args in cli_args(command, "search") + cli_args(command, "graph"):
            module = self.module_from_args(args)
            if module:
                # 命令行检索拿不到对话 id，先登记，让它按模块认领，好做对话内去重
                seen.note_handoff(self.config.cache_dir, self.conversation, [module])
                claimed.add(module)
            elif seen.looks_like_shell_var(args.get("module")) or seen.looks_like_shell_var(args.get("path")):
                # --module $m：通配交接，避免循环检索整段正文反复占上下文
                seen.note_handoff(self.config.cache_dir, self.conversation, [seen.HANDOFF_ANY])
            else:
                # 拼错的模块名、未登记路径：不当通配，避免任意检索认走这个对话
                seen.note_handoff(self.config.cache_dir, self.conversation, [])
        return claimed

    def _pop_cli_pending(self, field: str, command: str, calls: list[dict]) -> list[dict] | None:
        pending = self.state.data[field]
        key = command_key(command)
        if key not in pending and calls:
            # 前后两次拿到的命令文本可能因转码不同（中文检索词）：按命令里的模块名（ASCII，不受转码影响）认领，
            # 认不出时只有一条在等才认作同一条；并行的 ls 这类命令没调 pmem，不能把别的命令挂起的调用拿走。
            # 并行检索留下的没认领的旧条目不能挡住之后的认领
            wanted = sorted(filter(None, map(self.module_from_args, calls)))
            same = [k for k, v in pending.items() if sorted(filter(None, map(self.module_from_args, v))) == wanted]
            if same:
                key = same[-1]
            elif len(pending) == 1:
                key = next(iter(pending))
        return pending.pop(key, None)

    def _confirm_cli_calls(self) -> str | None:
        """命令跑完：挂起的终端检索登记为查过、写入登记为写过。拿得到命令输出时，检索要在输出里看到该模块，
        写入还要看到 draft_id（写入失败、|| 之后没执行的都没有）。
        同一条命令里检索没成功、却已经改了该模块的文件（执行前按“查过再写”放行了）时，返回补查提醒。"""
        if self.state is None:
            return None
        command = str(tool_input(self.payload).get("command") or "")
        searches = self._pop_cli_pending("cli_pending", command, cli_args(command, "search") + cli_args(command, "graph"))
        records = self._pop_cli_pending("cli_record_pending", command, cli_args(command, "record"))
        if searches is None and records is None:
            return None
        self.save()
        output = shell_output(self.payload)
        lowered = output.lower() if output is not None else None
        failed: list[str] = []
        for args in searches or []:
            module = self.module_from_args(args)
            if lowered is not None and (not module or module.lower() not in lowered):
                self.log("search_call_unseen", module=module, via="cli")
                if module:
                    failed.append(module)
                continue
            self._mark_searched(args, via="cli")
        for args in records or []:
            module = self.module_from_args(args)
            if lowered is not None and (not module or module.lower() not in lowered
                                        or "draft_id" not in lowered.replace("-", "_")):
                self.log("record_call_failed", module=module, via="cli")
                continue
            if module:
                self.state.add("cli_recorded", module)
            self.log("record_call", module=module, via="cli")
        self.save()
        if not failed:
            return None
        base = str(tool_input(self.payload).get("cwd") or self.root)
        written = {self.module_of(self.relative(t, base)) for t in scan(command, base)[0]}
        hit = [m for m in dict.fromkeys(failed) if m in written and not self.state.has("searched", m)]
        if not hit:
            return None
        self.log("search_failed_after_write", modules=hit)
        return (f"[pmem] 这条命令里对 {'、'.join(hit)} 的检索没有成功（输出里看不到该模块），但命令随后已经改了它的文件。"
                f"请现在用 search_memory(module=\"{hit[0]}\") 补查，核对改动是否与已有记忆冲突。")

    def _inject(self, args: dict, with_draft: bool) -> dict:
        if not args or self.state is None:
            return dict(ALLOW)
        # Cursor 只回传新增的字段：它给 Hook 的输入在中文 Windows 上会被转码损坏，回传原参数会把乱码写回去
        updated = dict(args) if self.payload.get("replaces_input") else {}
        updated["source_conversation"] = self.conversation
        module = self.module_from_args({"module": args.get("module")}) if with_draft else None
        # 同一模块下的不同议题是不同的记忆，只有议题也相同时才覆盖本对话写过的草稿
        entity = self.registry.resolve_entity(module, str(args.get("entity") or "")) if module else None
        key = draft_key(module, entity, str(args.get("kind") or "")) if module else None
        draft = self.state.data["written"].get(key) if key else None
        if draft and not args.get("draft_id") and self._draft_open(module, draft):
            updated["draft_id"] = draft
        # 覆盖草稿时不补锚点，让服务沿用草稿原有的锚点；
        # 载荷被转码损坏、只按字段抠出了部分参数时，看不到 Agent 写的 anchors，补了会把它覆盖成只到文件
        if module and not args.get("anchors") and not updated.get("draft_id") and not self.payload.get("_partial"):
            files = [item.split("|", 1)[1] for item in self.state.data["edited_files"] if item.startswith(module + "|")]
            if files:
                updated["anchors"] = files[-MAX_AUTO_ANCHORS:]
        return {"permission": "allow", "updated_input": updated}

    def _draft_open(self, module: str, draft: str) -> bool:
        """草稿已提交就不能再覆盖：长对话跨过提交后，注入旧 id 只会让服务拒绝这次写入。"""
        path = self.config.entries_dir / module / f"{draft}.md"
        if not path.exists():
            return True
        try:
            # 判断不了（None 或出错）时按已提交处理：注入了服务也会拒绝
            return self.vcs().is_committed(path) is False
        except Exception:  # noqa: BLE001
            return False

    def _mark_searched(self, args: dict, via: str) -> None:
        module = self.module_from_args(args)
        if module and self.state is not None:
            for key in ("searched", "consulted", "reviewed"):
                self.state.add(key, module)
            self.save()
        self.log("search_call", module=module, via=via)

    def on_before_mcp(self) -> dict:
        """旧版 hooks.json 仍会调用；检索改在返回结果之后登记，这里只放行。"""
        return dict(ALLOW)

    def on_after_mcp(self) -> dict:
        name = str(self.payload.get("tool_name") or "")
        if self.state is None or not any(t in name for t in PMEM_TOOLS) or foreign_tool(self.payload):
            return {}
        response = tool_response(self.payload)
        if not response or response.get("ok") is not True:
            return {}
        module = self.module_from_args({"module": response["module"]}) if response.get("module") else None
        rows = [r for key in ("items", "features", "timeline") for r in response.get(key) or [] if isinstance(r, dict)]
        ids = [str(i) for i in dict.fromkeys([response.get("id"), *(r.get("id") for r in rows)])
               if i and re.fullmatch(ULID_PATTERN, str(i))]
        if "record_memory" not in name and not self._from_pmem(name, response, ids):
            # 别家记忆服务的同名工具，不算查过 pmem 的记忆
            self.log("foreign_search", module=module)
            return {}
        if "record_memory" in name:
            if module and response.get("id") in ids:
                kind = response.get("kind") or tool_input(self.payload).get("kind")
                self.state.data["written"][draft_key(module, response.get("entity"), kind)] = response["id"]
                self.state.add("recorded", response["id"])
            self.log("mcp_record", module=module, ids=ids[:1])
        else:
            if module:
                self.state.add("searched", module)
                self.state.add("consulted", module)
            # 不限模块的检索：结果里出现过的模块也算看过记忆
            for seen in {str(r["module"]) for r in rows if r.get("module")} | ({module} if module else set()):
                self.state.add("reviewed", seen)
            for mid in ids:
                self.state.add("returned", mid)
            self.log("mcp_search", module=module, ids=ids)
        self.save()
        return {}

    def _from_pmem(self, name: str, response: dict, ids: list[str]) -> bool:
        """结果来自 pmem：带 pmem 的来源标记、工具名里有服务名 pmem，或返回的记忆在本仓库。
        没有标记的旧版服务返回空结果时也不算，Agent 可以改用终端 pmem search。"""
        if response.get("server") == "pmem" or "pmem" in name.lower():
            return True
        return bool(ids) and self._has_local(ids)

    def _has_local(self, ids: list[str]) -> bool:
        folder = self.config.entries_dir
        return folder.is_dir() and any(next(folder.glob(f"*/{i}.md"), None) for i in ids)
