---
id: 01M6RDYMY1TR0Z653WGV355H3Z
module: feature.Onboarding
entity: TrustConfig
kind: feature
status: active
supersedes:
- 01M6RD77P7902XX1YY86C6WPPF
anchors:
- src/pmem/generate/mcp_enable.py#enable_cursor_project_mcp
- src/pmem/generate/mcp_enable.py#enable_codex_project_mcp
- src/pmem/generate/mcp_enable.py#_claude_project_keys
- src/pmem/cli/doctor_cmd.py#_is_console_python_hook
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 同名 Cursor 不删其他哈希，Codex 单引号走基本字符串
verify: uv run pytest tests/test_mcp_enable.py tests/test_doctor_console_python.py
  -q
applies: pmem init 写本机 Cursor、Claude、Codex 配置，以及 Windows 上的 doctor
aliases:
- Codex单引号
- Cursor同名批准
- doctor单引号
---
需求来源：同名文件夹的 Cursor 批准会互相删掉；Codex 路径里的单引号会把整份 config.toml 写坏；Claude 对每条绝对路径 resolve 可能卡在断网 UNC；doctor 漏掉单引号路径和 cmd /c。

必须保持：
Cursor 批准只去掉没有哈希的旧键，同一 project-序号-文件夹名-pmem 下其它配置哈希留下，重复 init 不追加第二条相同哈希。配置完全相同因而哈希相同时，Cursor 的键不含完整路径，两个同名目录仍共用这一条批准。
Codex 新建信任段时，路径含单引号或控制字符就用 TOML 基本字符串，并转义反斜杠和双引号；已有段按解开转义后的路径识别，不重复追加。没有单引号的路径仍用单引号字面量，反斜杠保持原样。
Claude 匹配本项目时，UNC 和不同盘符不做 resolve，只在规范化字符串相等时命中；同一盘符仍按 resolve 后的真实路径相等。
doctor 把单引号路径、PowerShell 的 &、cmd /c 后面的控制台 python 当成会弹黑框；pythonw 仍然排除。

入口：enable_cursor_project_mcp、enable_codex_project_mcp、_claude_project_keys、_is_console_python_hook。
