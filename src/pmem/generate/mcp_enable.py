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

from pmem.core.fileio import write_atomic
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
    """与 Cursor MCPService.computeServerConfigHash 一致（未解析变量的原始配置）。
    Cursor（JS）用有符号 (hash).toString(16)，负数带前导负号（实测其自写的 project-0-TileMatch-playwright:-433220a0），
    所以这里保留有符号十六进制，不要改成无符号。"""
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


def cursor_running() -> bool:
    """Cursor 是否正在运行。运行时它把批准名单读进内存，退出或改设置时整体写回 state.vscdb，
    会覆盖外部进程（pmem）刚写的批准，所以运行中不能假装已自动批准。查不出来时返回 False（宁可写，别误报拦住）。"""
    import subprocess

    from pmem.core.winproc import no_window_kwargs

    try:
        if sys.platform == "win32":
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Cursor.exe", "/NH"],
                                 check=False, capture_output=True, timeout=5, **no_window_kwargs())
            return b"Cursor.exe" in out.stdout
        # macOS / Linux：pgrep 命中即在跑（-x 整词，macOS 进程名为 Cursor）
        names = ("Cursor", "cursor") if sys.platform == "darwin" else ("cursor", "Cursor")
        for name in names:
            if subprocess.run(["pgrep", "-x", name], check=False, capture_output=True, timeout=5).returncode == 0:
                return True
        return False
    except (OSError, subprocess.SubprocessError):
        return False


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
    if cursor_running():
        # Cursor 运行时写进去的批准会被它退出/改设置时的内存副本覆盖，等于没写
        return ("Cursor：检测到正在运行，此时写入的批准会被 Cursor 覆盖；请完全退出 Cursor 后重跑 pmem init，"
                "或在 设置 → MCP 手动启用 pmem 后 Reload Window")
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
            # Cursor 的键只有序号和文件夹名，没有完整路径。两个都叫 MyApp 的目录共用
            # project-0-MyApp-pmem。配置哈希不同时，删掉旧哈希会把另一个项目的批准冲掉；
            # 只去掉没有哈希的旧记录，其它哈希留下。配置完全相同时哈希相同，Cursor 仍会当成同一条批准。
            approved = [x for x in approved if x != identifier]
            if key not in approved:
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


def _defer_path_resolve(candidate: Path, resolved: Path) -> bool:
    """断网的 UNC，或和本项目不在同一盘符上的路径，Path.resolve() 可能一直不返回。"""
    text = str(candidate)
    if text.startswith("\\\\") or text.startswith("//"):
        return True
    if candidate.drive and resolved.drive and candidate.drive.lower() != resolved.drive.lower():
        return True
    return False


def _claude_project_keys(root: Path, projects: dict) -> list[str]:
    """~/.claude.json 里本项目对应的 key。Claude 可能用正斜杠/反斜杠、resolve 前后等不同写法存同一路径，
    所以按“解析后的真实路径相等”认，而不是按目录名——同名不同路径（~/a/pmem 与 ~/b/pmem）绝不能一起批准。"""
    resolved = root.resolve()
    forms = [
        str(resolved).replace("\\", "/"),
        str(resolved),
        resolved.as_posix(),
        str(root).replace("\\", "/"),
        str(root),
    ]
    # 已有的项目 key 里，解析后与本项目同一真实路径的才算命中（含大小写/斜杠差异）。
    # 只认绝对路径 key：相对/短路径的 resolve() 会按当前 cwd 解析，可能误命中别的项目（Claude 实际写绝对路径）
    matched = []
    for key in projects:
        try:
            candidate = Path(key)
            if not candidate.is_absolute():
                continue
            if _defer_path_resolve(candidate, resolved):
                # 不 resolve：断网 UNC / 别的盘符可能卡死。字符串相同才算同一个项目。
                if os.path.normcase(os.path.normpath(key)) == os.path.normcase(os.path.normpath(str(resolved))):
                    matched.append(key)
                continue
            if candidate.resolve() == resolved:
                matched.append(key)
        except (OSError, ValueError):
            continue
    # 去重保序：真实路径命中的已有 key 优先，否则用规范写法新建一条
    seen: set[str] = set()
    ordered: list[str] = []
    for c in [*matched, *forms]:
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
    # 原子写：写一半崩溃不会毁掉用户全局的 ~/.claude.json（先写 .tmp 再 os.replace）
    write_atomic(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return f"Claude Code：已项目级启用 .mcp.json 的 pmem（{touched[0]}）"


def _codex_quote(path: str) -> str:
    """TOML 键。没有单引号时用字面量（反斜杠保持原样，和 Codex 现有配置一致）；
    路径里有单引号或控制字符时字面量不合法，改用基本字符串并转义。"""
    if "'" in path or any(ord(ch) < 32 for ch in path):
        escaped = (
            path.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'
    return f"'{path}'"


def _codex_path_key(path: str) -> str:
    return path.lower().replace("\\", "/")


def _parse_toml_string(text: str, start: int) -> tuple[int, str] | None:
    """从 start 处的引号解析一个 TOML 字符串，返回（结束后的下标, 解开转义的值）。"""
    if start >= len(text) or text[start] not in "'\"":
        return None
    if text[start] == "'":
        end = text.find("'", start + 1)
        if end < 0:
            return None
        return end + 1, text[start + 1:end]
    chars: list[str] = []
    index = start + 1
    while index < len(text):
        char = text[index]
        if char == "\\":
            if index + 1 >= len(text):
                return None
            nxt = text[index + 1]
            chars.append({"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"'}.get(nxt, nxt))
            index += 2
            continue
        if char == '"':
            return index + 1, "".join(chars)
        if char == "\n":
            return None
        chars.append(char)
        index += 1
    return None


def _iter_codex_projects(text: str):
    """已有的 [projects.<路径>]：返回（段头起点, 段头结束后的下标, 解开后的路径）。"""
    for match in re.finditer(r"(?m)^\[projects\.", text):
        parsed = _parse_toml_string(text, match.end())
        if parsed is None:
            continue
        end, path = parsed
        if end < len(text) and text[end] == "]":
            yield match.start(), end + 1, path


def _codex_body_start(text: str, header_end: int) -> int:
    index = header_end
    if index < len(text) and text[index] == "\r":
        index += 1
    if index < len(text) and text[index] == "\n":
        index += 1
    return index


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
    wanted = {_codex_path_key(item) for item in _codex_path_variants(root)}
    # 已有任一路径的 trust_level=trusted 则只补漏。路径按解开转义后的值比对，
    # 这样带单引号的基本字符串不会被当成另一条再追加。
    for _header_at, header_end, path in _iter_codex_projects(text):
        if _codex_path_key(path) not in wanted:
            continue
        start = _codex_body_start(text, header_end)
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
        write_atomic(cfg, text[:start] + new_block + text[end:])
        return f"Codex：已将项目标为 trusted（{path}）"

    # 新建段：Codex 常见小写 Windows 路径。单引号放进字面量会把整份 config.toml 写坏。
    preferred = str(root.resolve())
    if sys.platform == "win32":
        preferred = preferred.lower()
    block = f"\n[projects.{_codex_quote(preferred)}]\ntrust_level = \"trusted\"\n"
    separator = "" if not text or text.endswith("\n") else "\n"
    write_atomic(cfg, text + separator + block)
    return f"Codex：已项目级信任并启用 pmem（{preferred}）"


def enable_project_mcp(agent: str, root: Path) -> str:
    if agent == "cursor":
        return enable_cursor_project_mcp(root, MCP_SERVER)
    if agent == "claude":
        return enable_claude_project_mcp(root)
    if agent == "codex":
        return enable_codex_project_mcp(root)
    return f"{agent}：无自动启用逻辑"
