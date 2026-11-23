---
id: 01M83NG4RPW8WBK4PMX4W5DYW6
module: feature.Onboarding
entity: WindowsConsole
kind: risk
status: active
supersedes:
- 01M6JK4RFHPGQR7XR563148V77
- 01M6JKKVRJQ96FRGFY65YSV81Z
- 01M6JQ0ME3HBFJ4NHW3QYEFGEE
- 01M6JQ0P2Z063ECDX1Y5PA1K3E
- 01M6QVPQJ90AD239BHVKE20KGC
anchors:
- src/pmem/generate/templates.py#CURSOR_HOOKS
- src/pmem/cli/doctor_cmd.py
- src/pmem/generate/templates.py#MCP_BIN
- src/pmem/server/app.py#resolve_root
- src/pmem/generate/templates.py#_CURSOR_HOOK_EXTRA
- .cursor/hooks.json
- src/pmem/vcs/base.py#run_tool
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: Windows 黑框：Hooks 用 pmemw，MCP 用 pmem，默认 full
aliases:
- 黑框
- 闪框
- 控制台
source:
  kind: document
---
现状（Windows 控制台/黑框/闪框；pmem 本体。出图项目另见同议题 art 条）：

Hooks 用 pmemw（GUI，含 sessionStart，避免 .cmd）。
MCP（Cursor/Claude/Codex）必须用 pmem serve，不要用 pmemw：Windows 上 pmemw/uv trampoline 会掐断 stdio（Connection closed）。
用户级 ~/.cursor/mcp.json 不要再注册同名 pmem。
resolve_root 认 WORKSPACE_FOLDER_PATHS。

hooks.json 里含 ||、或指向 .cmd/.sh，Cursor 在 Windows 上会经 shell 启动，几乎必弹控制台，与是否 pmemw 无关。
doctor 检测 ||。
第三方自建 Hook 也须改成单个可执行/解释器调用。

曾以为 Windows 默认改 quiet、去掉读码摘要就能消黑框。
已过时：默认 auto=full。
quiet 只是显式选项，且不能拆掉 Write/Edit 闸门。
只换 pmemw 也不能保证所有 Cursor 版本都不弹：外层若用未藏窗的 cmd/pwsh 拉 Hook，仍可能按触发次数弹。
缓解：terminal.integrated.windowsUseConptyDll=true 后重启。

Hook 进程内部 git/svn 子进程的黑框，靠 CREATE_NO_WINDOW（feature.Storage RunToolNoWindow），与外层拉起 Hook 不是同一层。不要靠拆闸门或读码摘要消黑框。

合并自 5 条记忆。
