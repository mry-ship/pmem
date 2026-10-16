---
id: 01M4ZFGA60PXFPYPF65R9ZTGV9
module: feature.Gate
entity: Agents
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/hooks/agents.py
- src/pmem/cli/hook_cmd.py
revision: git:fc9f6d8
author: 1002378395@qq.com
note_date: '2026-10-15'
aliases:
- Claude Code
- Codex
- 多工具
- 其他大模型
verified: '2026-10-16'
---
决定：兼容 Claude Code、Codex 等其他 Agent 工具时，不另写闸门，而是让三家共用同一套闸门逻辑。
各工具的 Hook 都调用 `pmem hook <事件> --agent <cursor|claude|codex>`，由适配层先把输入转换成 Cursor 的格式，处理完再按目标工具的协议输出。
pmem init --agents 负责生成各工具的配置：Claude Code 是 CLAUDE.md 段落、.claude/settings.json、.mcp.json；
Codex 是 AGENTS.md 段落、.codex/hooks.json、.codex/config.toml。

协议上的坑：
- Claude Code / Codex 的 PreToolUse 返回 permissionDecision:"allow" 会直接批准这次工具调用，等于跳过用户确认。
  所以只有 pmem 自己的 MCP 工具需要 updatedInput（注入草稿 id）时才返回 allow；
  其余放行一律返回 {}，否则 Bash 等命令会被自动批准。
- Codex 改文件走 apply_patch，tool_input.command 是补丁文本，被改的文件要从 "*** Update/Add/Delete File:" 和 "*** Move to:" 行解析。
- 结束提醒：Claude Code 用 hookSpecificOutput.additionalContext，Codex 用 {"decision":"block","reason"} 续跑一轮。
- 项目根依次从 cwd、workspace_roots、payload 的 cwd、CLAUDE_PROJECT_DIR 查找。
- Codex 需要先信任项目、再在 /hooks 里信任 Hook，否则项目里的 .codex/ 不加载。

验证：单元测试，加上用命令行管道模拟 Claude 的 Edit、Codex 的 apply_patch、Claude 的 Bash 三种输入。
未查过的模块被拒绝，Bash 返回 {}。
尚未在真实的 Claude Code / Codex 会话里跑过。
