"""把各 Agent 的「项目级」pmem MCP 在本机自动启用（不写用户级 mcpServers）。

Cursor：写入应用存储里的 approvedProjectMcpServers（哈希与 Cursor 一致）。
Claude Code：在 ~/.claude.json 对应项目里把 pmem 放进 enabledMcpjsonServers。
Codex：在 ~/.codex/config.toml 里把本项目标为 trusted（项目 .codex/config.toml 里已有 mcp_servers.pmem）。
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

from pmem.generate.templates import MCP_SERVER

_CURSOR_APPROVED_KEY = "cursor/approvedProjectMcpServers"
_CURSOR_DISABLED_KEY = "disabledMcpServers"
_CURSOR_KNOWN_KEY = "mcpService.knownServerIds"


def _skip_local_enable() -> bool:
    """单测/CI 不写本机 Cursor/Claude/Codex 状态，避免污染用户配置。"""
    if os.environ.get("PMEM_SKIP_MCP_ENABLE", "").strip() in {"1", "true", "yes"}:
        return True
    # pytest 运行时会设置；显式单测可用 PMEM_SKIP_MCP_ENABLE=0 覆盖
    if os.environ.get("PMEM_SKIP_MCP_ENABLE", "").strip() in {"0", "false", "no"}:
        return False
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _i32(n: int) -> int:
    n &= 0xFFFFFFFF
    return n - 0x100000000 if n >= 0x80000000 else n


def _mix(e: int, t: int) -> int:
    return _i32((t << 5) - t + e)


def _hash_string(text: str, seed: int = 0) -> int:
    t = _mix(149417, seed)
    for ch in text:
        t = _mix(ord(ch), t)
    return t


def cursor_server_config_hash(cfg: dict) -> str:
    """与 Cursor MCPService.computeServerConfigHash 一致（未解析变量的原始配置）。"""
    keys = ("command", "args", "env", "envFile", "url", "headers", "auth")
    obj = {k: cfg[k] for k in keys if k in cfg}
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return format(_hash_string(payload), "x")[:16]


def cursor_approval_key(identifier: str, cfg: dict) -> str:
    return f"{identifier}:{cursor_server_config_hash(cfg)}"


def cursor_state_db() -> Path | None:
    home = Path.home()
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "Cursor"
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support" / "Cursor"
    else:
        base = home / ".config" / "Cursor"
    path = base / "User" / "globalStorage" / "state.vscdb"
    return path if path.is_file() else None


def _folder_indexes(root: Path, known: list[str]) -> list[int]:
    """单根工作区一般是 0；若本机已知过其它 index，一并批准。"""
    name = root.name
    indexes = {0}
    pat = re.compile(rf"^project-(\d+)-{re.escape(name)}-pmem(?::|$)")
    for item in known:
        m = pat.match(item)
        if m:
            indexes.add(int(m.group(1)))
    return sorted(indexes)


def _load_cursor_pmem_cfg(root: Path, cfg: dict | None) -> dict:
    if cfg is not None:
        return dict(cfg)
    path = root / ".cursor" / "mcp.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig") or "{}")
            server = (data.get("mcpServers") or {}).get("pmem")
            if isinstance(server, dict) and server.get("command"):
                return dict(server)
        except json.JSONDecodeError:
            pass
    return dict(MCP_SERVER)


def enable_cursor_project_mcp(root: Path, cfg: dict | None = None) -> str:
    """批准项目 .cursor/mcp.json 里的 pmem。返回说明；失败时带原因。"""
    if _skip_local_enable():
        return "Cursor：测试环境跳过本机 MCP 批准"
    cfg = _load_cursor_pmem_cfg(root, cfg)
    db = cursor_state_db()
    if db is None:
        return "Cursor：未找到本机状态库，无法自动批准；打开设置 → MCP 手动启用 pmem"
    try:
        con = sqlite3.connect(db, timeout=5)
        cur = con.cursor()

        def _get(key: str):
            row = cur.execute("SELECT value FROM ItemTable WHERE key=?", (key,)).fetchone()
            if not row or row[0] in (None, ""):
                return []
            try:
                data = json.loads(row[0])
            except json.JSONDecodeError:
                return []
            return data if isinstance(data, list) else []

        known = [str(x) for x in _get(_CURSOR_KNOWN_KEY)]
        approved = [str(x) for x in _get(_CURSOR_APPROVED_KEY)]
        disabled = [str(x) for x in _get(_CURSOR_DISABLED_KEY)]

        keys: list[str] = []
        for index in _folder_indexes(root, known + approved + disabled):
            identifier = f"project-{index}-{root.name}-pmem"
            key = cursor_approval_key(identifier, cfg)
            keys.append(key)
            approved = [
                x for x in approved
                if not (x == identifier or x.startswith(f"{identifier}:"))
            ]
            approved.append(key)
            if identifier in disabled:
                disabled = [x for x in disabled if x != identifier]
            if identifier not in known:
                known.append(identifier)

        cur.execute(
            "INSERT INTO ItemTable(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (_CURSOR_APPROVED_KEY, json.dumps(approved, ensure_ascii=False, separators=(",", ":"))),
        )
        cur.execute(
            "INSERT INTO ItemTable(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (_CURSOR_DISABLED_KEY, json.dumps(disabled, ensure_ascii=False, separators=(",", ":"))),
        )
        cur.execute(
            "INSERT INTO ItemTable(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (_CURSOR_KNOWN_KEY, json.dumps(known, ensure_ascii=False, separators=(",", ":"))),
        )
        con.commit()
        con.close()
    except sqlite3.Error as exc:
        return f"Cursor：写入批准失败（{exc}）；请在设置 → MCP 手动启用 pmem"
    shown = "、".join(keys[:2]) + ("…" if len(keys) > 2 else "")
    return f"Cursor：已项目级批准 pmem（{shown}；若本窗口仍断开请 Reload Window）"


def _claude_project_keys(root: Path, projects: dict) -> list[str]:
    resolved = root.resolve()
    candidates = [
        str(resolved).replace("\\", "/"),
        str(resolved),
        resolved.as_posix(),
        str(root).replace("\\", "/"),
        str(root),
    ]
    target = root.name
    for key in projects:
        norm = key.replace("\\", "/").rstrip("/")
        # 只认路径最后一段恰好是项目目录名，避免 Art 误匹配 Cursor-Pmem-Art
        if Path(norm).name == target:
            candidates.append(key)
    # 去重且保持顺序
    seen: set[str] = set()
    ordered: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    existing = [c for c in ordered if c in projects]
    return existing or [ordered[0]]


def enable_claude_project_mcp(root: Path) -> str:
    if _skip_local_enable():
        return "Claude Code：测试环境跳过本机 MCP 启用"
    path = Path.home() / ".claude.json"
    if not path.is_file():
        return "Claude Code：未找到 ~/.claude.json，首次打开项目时再批准 .mcp.json 的 pmem"
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as exc:
        return f"Claude Code：~/.claude.json 不是合法 JSON（{exc}）"
    if not isinstance(data, dict):
        return "Claude Code：~/.claude.json 结构异常"
    projects = data.setdefault("projects", {})
    if not isinstance(projects, dict):
        return "Claude Code：~/.claude.json 的 projects 结构异常"
    touched: list[str] = []
    for key in _claude_project_keys(root, projects):
        proj = projects.get(key) if isinstance(projects.get(key), dict) else {}
        enabled = [str(x) for x in (proj.get("enabledMcpjsonServers") or [])]
        disabled = [str(x) for x in (proj.get("disabledMcpjsonServers") or [])]
        if "pmem" not in enabled:
            enabled.append("pmem")
        disabled = [x for x in disabled if x != "pmem"]
        proj = {
            **proj,
            "enabledMcpjsonServers": enabled,
            "disabledMcpjsonServers": disabled,
            "hasTrustDialogAccepted": True,
        }
        projects[key] = proj
        touched.append(key)
    data["projects"] = projects
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f"Claude Code：已项目级启用 .mcp.json 的 pmem（{touched[0]}）"


_CODEX_PROJECT_HEADER = re.compile(
    r"(?m)^\[projects\.(?P<q>'|\")(?P<path>.*?)(?P=q)\]\s*$"
)


def _codex_path_variants(root: Path) -> list[str]:
    resolved = root.resolve()
    raw = [
        str(resolved),
        str(resolved).replace("\\", "/"),
        str(resolved).lower(),
        str(resolved).replace("\\", "/").lower(),
        str(root),
        str(root).replace("\\", "/"),
    ]
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def enable_codex_project_mcp(root: Path) -> str:
    """把本项目标为 trusted，让 Codex 加载项目 .codex/（含 mcp_servers.pmem）。"""
    if _skip_local_enable():
        return "Codex：测试环境跳过本机项目信任"
    cfg = Path.home() / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    text = cfg.read_text(encoding="utf-8-sig") if cfg.exists() else ""
    variants = _codex_path_variants(root)
    # 已有任一路径的 trust_level=trusted 则只补漏
    for match in _CODEX_PROJECT_HEADER.finditer(text):
        path = match.group("path")
        if path.lower().replace("\\", "/") not in {
            v.lower().replace("\\", "/") for v in variants
        }:
            continue
        # 取该段到下一 [ 之前
        start = match.end()
        nxt = re.search(r"(?m)^\[", text[start:])
        block = text[start : start + nxt.start()] if nxt else text[start:]
        if re.search(r'(?m)^\s*trust_level\s*=\s*"trusted"\s*$', block):
            return f"Codex：项目已信任（{path}），会加载 .codex/config.toml 的 pmem"
        # 段在但未信任：改成 trusted
        new_block, n = re.subn(
            r'(?m)^\s*trust_level\s*=\s*".*?"\s*$',
            'trust_level = "trusted"',
            block,
            count=1,
        )
        if n == 0:
            new_block = '\ntrust_level = "trusted"\n' + block.lstrip("\n")
        end = start + len(block)
        cfg.write_text(text[:start] + new_block + text[end:], encoding="utf-8", newline="\n")
        return f"Codex：已将项目标为 trusted（{path}）"

    # 新建段：Codex 常见小写 Windows 路径
    preferred = str(root.resolve())
    if sys.platform == "win32":
        preferred = preferred.lower()
    block = f"\n[projects.'{preferred}']\ntrust_level = \"trusted\"\n"
    separator = "" if not text or text.endswith("\n") else "\n"
    cfg.write_text(text + separator + block, encoding="utf-8", newline="\n")
    return f"Codex：已项目级信任并启用 pmem（{preferred}）"


def enable_project_mcp(agent: str, root: Path) -> str:
    if agent == "cursor":
        return enable_cursor_project_mcp(root, MCP_SERVER)
    if agent == "claude":
        return enable_claude_project_mcp(root)
    if agent == "codex":
        return enable_codex_project_mcp(root)
    return f"{agent}：无自动启用逻辑"
