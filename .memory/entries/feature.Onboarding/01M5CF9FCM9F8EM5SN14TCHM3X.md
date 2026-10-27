---
id: 01M5CF9FCM9F8EM5SN14TCHM3X
module: feature.Onboarding
entity: AgentSetup
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py#CLAUDE_HOOKS
- src/pmem/generate/integrations.py#setup_codex
- src/pmem/cli/doctor_cmd.py#run_doctor
- src/pmem/cli/doctor_cmd.py#_agent_handlers
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: Claude/Codex 接入要完整：PowerShell 守护、失败放行、Codex 技能、doctor 分家检查
verify: pytest tests/test_cli_flow.py -k "claude or codex"
aliases:
- Claude 适配
- Codex 适配
- 接入
- onFailure
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:19.568+08:00'
source:
  conversation: ca2edda2-f749-419e-aa6d-74617201a8d5
---
需求：用户要求“codex 和 claude 的适配都得做好”。必须保持的行为：
- Claude Code 的 Hook matcher 含 PowerShell（Windows 上与 Bash 并列的终端工具）；
  每个 pmem 处理器带 "onFailure": "continue"：没装 Git Bash 或 pmem 时 Hook 起不来也放行，不卡住所有修改。
  Codex 不加这个字段。
- pmem init --agents codex 把技能写到 .agents/skills（Codex 只从这里读项目技能），Claude 仍写 .claude/skills。
- gate.ignore 默认加 .claude/**、.codex/**、.agents/**，改 Agent 配置不要求查记忆（已有 config.yaml 的项目不受影响）。
- pmem doctor：只接了 Claude/Codex 的项目不检查 .cursor（原先缺 .cursor/mcp.json 报红）；
  Claude 的 Hook 缺 PowerShell 或 onFailure 时提示旧版、重新 pmem init；
  Codex 缺 .agents/skills 时提示；
  提示文字不再写死“在 Cursor 里”。
入口：generate/templates.py 的 CLAUDE_HOOKS、generate/integrations.py 的 setup_codex、cli/doctor_cmd.py。
已接入的老项目要重新运行 pmem init 才生效。
