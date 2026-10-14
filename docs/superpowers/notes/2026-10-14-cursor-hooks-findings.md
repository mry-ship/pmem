# Cursor Hooks 实测结论（M0）

环境：Cursor 3.9.16，Windows 11 中文版（ANSI 代码页 936），PowerShell 5。
方法：用 `spike/cursor_hooks/record.py` 把每个事件的原始标准输入落盘（`captures/`，已在 .gitignore 中排除），再在本仓库的日常开发中观察 pmem 闸门的实际效果。脱敏后的样本在 `tests/fixtures/hook_payloads/`。

## 输入

| 结论 | 说明 |
|---|---|
| 公共字段 | 每个事件都带 `conversation_id`（与 `session_id` 相同）、`generation_id`、`hook_event_name`、`cursor_version`、`workspace_roots`（形如 `/c:/Users/...`）、`user_email`、`transcript_path` |
| 工作目录 | Hook 进程的 cwd 是工作区根目录 |
| 编辑类工具 | StrReplace 在 preToolUse 中也显示为 `tool_name: "Write"`，`tool_input` 里是修改后的完整文件内容 |
| 终端 | `tool_name: "Shell"`，`tool_input.command` 是完整命令，`tool_input.cwd` 通常为空字符串 |
| matcher | 按 `tool_name` 做正则匹配；修改 `hooks.json` 后立即生效，不需要重启 |
| beforeSubmitPrompt | 带 `prompt`（中文可能乱码）和 `composer_mode` |
| stop | 带 `status`（completed / aborted / error）、`loop_count`，以及 `input_tokens`、`output_tokens`、`cache_read_tokens`、`cache_write_tokens`。token 是本轮的值，不是对话累计；`input_tokens` 已包含缓存读取部分 |
| 对话记录 | `transcript_path` 指向 JSONL：`{role, message: {content: [{type: "text", text}]}}` 与 `{type: "turn_ended", status}`。不含工具调用，也不带逐行时间戳 |

## 编码（Windows 中文系统）

Cursor 经 PowerShell 转发标准输入时，先把 UTF-8 字节按 GBK 解码，再以带 BOM 的 UTF-8 写出。只要 payload 里有中文（例如写入的文件内容），JSON 就常被破坏。改用 `cmd /c` 或 `.cmd` 包装都无效。

对策：只依赖 ASCII 字段；解析时依次尝试原样、GBK 回转、正则提取三级兜底；中文标记词按误解码后的形态匹配；Hook 输出一律 `ensure_ascii`。开启 Windows“使用 Unicode UTF-8 提供全球语言支持”可从根本上避免。

## 输出

| 结论 | 说明 |
|---|---|
| preToolUse 拒绝 | `permission: "deny"` 时，Agent 只收到 `user_message`（作为工具报错，并附“不要建议绕过”的说明）；`agent_message` 不会送达。可执行的指引必须写在 `user_message` 里 |
| stop 追加消息 | `followup_message` 会作为一条新的用户消息送达，并触发 Agent 继续；中文以 `\u` 转义输出即可正常显示。配合 `loop_limit: 1` 防止循环 |
| 并行工具调用 | Agent 一次发出的多个编辑由 Cursor 逐个执行，每个单独走 preToolUse；拒绝其中一个不影响其余的 |
| 上下文压缩 | 压缩前触发 preCompact，可以用来重置“本对话已查过”之类的状态 |
| 失败处理 | pmem 的 Hook 捕获所有异常并输出放行，错误写入 `hook-errors.log`；`hooks.json` 中同时设置了 `failClosed: false`。Hook 进程本身崩溃或超时时 Cursor 的表现未单独实测 |
| 延迟 | 经 `pmem.exe` 调用，每个 Hook 约 230 毫秒，日常使用感觉不到 |

## 尚未验证（需要在 Cursor 设置里启用项目 MCP 后实测）

1. preToolUse 对 MCP 工具返回 `updated_input` 时，修改后的参数是否真的传给 MCP 服务（pmem 用它注入对话 id 和 `draft_id`）。
2. beforeMCPExecution / afterMCPExecution，以及 MCP 工具在 preToolUse 中的 payload 格式（`tool_name` 是否带 `MCP:` 前缀、结果字段名）。目前的解析是按“结果里出现 `"ok": true` 和 ULID”的宽松正则写的。
3. 项目级 `mcp.json` 中的 `${workspaceFolder}` 是否会被替换。pmem 已做兜底：没替换时改用 `PMEM_ROOT` 或工作目录向上查找。
4. sessionStart 事件。
