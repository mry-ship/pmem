---
id: 01M5CF95TGB794Z9Z2XKNBMTEM
module: feature.Gate
entity: Agents
kind: correction
status: active
supersedes:
- 01M59TCE7RFN0JR2XH5P5ZJ7RM
anchors:
- src/pmem/hooks/agents.py#normalize
- src/pmem/hooks/agents.py#render
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: Codex 也返回 additionalContext；Claude 的 PowerShell 工具按终端命令拦截
verify: pytest tests/hooks/test_agents.py -k "codex_prompt or powershell"
aliases:
- Codex 适配
- Claude 适配
- PowerShell 工具
- additionalContext
source:
  conversation: ca2edda2-f749-419e-aa6d-74617201a8d5
---
更正：旧记忆说 UserPromptSubmit、PostToolUse 的 additionalContext 只对 Claude 返回。
Codex 官方 Hook 文档写明这两个事件也认 hookSpecificOutput.additionalContext，原先 Codex 提问时拿不到模块摘要、Hook 出错提醒也送不到。
现在两家都返回，prompt_context 对 Claude、Codex 都开。
新增：Claude Code 在 Windows 上另有 PowerShell 工具（与 Bash 并列），原先 matcher 和 normalize 都只认 Bash，PowerShell 里 Set-Content 写守护模块不受闸门检查。
现在按终端命令处理（转成 Shell），pre/post matcher 都加 PowerShell。
仍有效：三家共用一套闸门，pmem hook <事件> --agent 先转成 Cursor 形状；
PreToolUse 只在 pmem 自己的 MCP 工具需要 updatedInput 时回 allow，其余放行回 {}；
Codex 的 apply_patch 从 *** Update/Add/Delete File 与 *** Move to 行解析文件；
Stop 两家都回 decision:block（Claude 2.1.163 前不认 Stop 的 additionalContext）；
项目根依次从 cwd、workspace_roots、payload cwd、CLAUDE_PROJECT_DIR 找；
Codex 需先信任项目、再在 /hooks 信任 Hook。
风险：仍未在真实 Claude Code / Codex 会话里跑完整流程。
