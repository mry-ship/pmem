---
id: 01M6JKKVRJQ96FRGFY65YSV81Z
module: feature.Onboarding
entity: WindowsConsole
kind: correction
status: active
supersedes:
- 01M6GYRHJPWRY23DXEE3BC9CFZ
- 01M6GYR0H7GVJBCT87HYN9T30T
- 01M6GYRK76VFYC7ZW3F8Z72A1Z
anchors:
- src/pmem/generate/templates.py#MCP_BIN
- src/pmem/server/app.py#resolve_root
- src/pmem/cli/doctor_cmd.py
revision: git:e51a54a
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: MCP 必须用 pmem；Hook 才用 pmemw
verify: mcp.json command=pmem；hooks 仍为 pmemw hook；doctor 对 pmemw MCP 告警
applies: pmem init 生成的接入配置
aliases:
- Connection closed
- user-pmem
---
更正：先前决定 Hook 与 MCP 都用 pmemw。
实测 Windows 上 pmemw/uv trampoline 会掐断 MCP stdio，Cursor 报 Connection closed / live tool discovery failed；
Agent 改跑终端 pmem，Terminal 面板被顶出。
现行：Hooks 继续 pmemw（减黑框）；
MCP（Cursor/Claude/Codex）用 pmem serve --root \。
用户级 ~/.cursor/mcp.json 不要再注册同名 pmem，以免盖住项目配置。
resolve_root 已认 WORKSPACE_FOLDER_PATHS，Temp 启动也能找回工程。
