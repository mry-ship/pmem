---
id: 01M51ZHM28NFFYA6V0V4NH7VMC
module: feature.Onboarding
entity: Rule
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py
- src/pmem/cli/init_cmd.py#write_hook_wrappers
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 规则
- 未安装
- 找不到pmem
- 静默失效
- 包装脚本
- sessionStart
verified: '2026-10-19'
---
决定：pmem init 生成的 Hooks 不再直接调用 pmem，改为经 .memory/bin/pmem-hook 包装脚本调用（sh 版无扩展名、LF；Windows 版 pmem-hook.cmd、CRLF、纯 ASCII；附 .gitattributes 固定换行，Git 下登记可执行位）。
包装脚本找得到 pmem 就转交；
找不到时：sessionStart 返回 additional_context 提示 Agent 告诉用户安装 pmem，preToolUse 返回 allow，beforeSubmitPrompt 返回 continue，其余返回 {}，不报错不卡住。
hooks.json 新增 sessionStart 事件。
规则（pmem.mdc / AGENTS.md）的“何时查”里同时保留一条：工具必须来自 pmem；
MCP 不可用或只有别的服务的同名工具时，改用终端 pmem search --module <模块> --brief / pmem record；
pmem 命令也找不到时告诉用户先安装。

原因：原来 hooks.json 直接调用 pmem，队友没装 pmem 时 Hook 起不来，按 failClosed=false 静默放行，闸门和审查全部失效，用户和 Agent 都不知道。

证据：本机 PowerShell 下同时存在无扩展名和 .cmd 文件时会解析到 .cmd；单测在去掉 pmem 的 PATH 下跑包装脚本，各事件输出符合预期。

风险：未在真实 Cursor 里验证 sessionStart 的提示确实送达（sessionStart 只在新对话触发一次）；
已接入的项目要重新运行 pmem init 才会生成包装脚本，pmem doctor 会对旧版 Hooks 报警告。
