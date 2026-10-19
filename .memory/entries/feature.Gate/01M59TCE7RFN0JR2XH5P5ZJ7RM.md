---
id: 01M59TCE7RFN0JR2XH5P5ZJ7RM
module: feature.Gate
entity: Agents
kind: correction
status: active
supersedes:
- 01M4ZFGA60PXFPYPF65R9ZTGV9
anchors:
- src/pmem/hooks/agents.py#render
- src/pmem/hooks/agents.py#normalize
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 结束提醒不生效
- Stop hook
- Claude 不提醒写记忆
- additionalContext
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
更正：Claude Code 的结束提醒原先返回 hookSpecificOutput.additionalContext，在 2.1.163 之前的版本里不生效。
Claude Code 更新日志写明 Stop/SubagentStop 从 2.1.163 才支持 additionalContext，更早版本直接忽略（本机 2.1.71 实测：Stop hook 被调用、stop_hook_active=false，但因账号额度不足没能跑完整回合）。
现在 Claude 和 Codex 都返回 {"decision":"block","reason":提醒文字}，各版本都认；
代价是界面上标为 hook 反馈。
没有两个字段一起返回，避免旧版本校验不认识的 Stop hookSpecificOutput。

仍有效：三家共用一套闸门，pmem hook <事件> --agent <cursor|claude|codex> 先把输入转成 Cursor 格式。
- PreToolUse 返回 permissionDecision:"allow" 会替用户批准工具调用，只有 pmem 自己的 MCP 工具需要 updatedInput 时才返回 allow，其余放行返回 {}。
- Codex 改文件走 apply_patch，从 "*** Update/Add/Delete File:" 和 "*** Move to:" 行解析文件。
- UserPromptSubmit、PostToolUse 的 additionalContext 只对 Claude 返回。
- 项目根依次从 cwd、workspace_roots、payload 的 cwd、CLAUDE_PROJECT_DIR 查找。
- Codex 需先信任项目、再在 /hooks 里信任 Hook。
风险：仍未在真实 Claude Code / Codex 会话里跑完整流程。
