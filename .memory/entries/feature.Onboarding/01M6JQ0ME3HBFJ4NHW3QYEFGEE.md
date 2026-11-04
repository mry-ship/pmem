---
id: 01M6JQ0ME3HBFJ4NHW3QYEFGEE
module: feature.Onboarding
entity: WindowsConsole
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py#_CURSOR_HOOK_EXTRA
- .cursor/hooks.json
revision: git:f034aa1
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: 排除：只换 pmemw 不能止疯狂弹窗
verify: full hooks 下每次 Read 仍可能弹；quiet 后 hooks 无 postToolUse
applies: Windows + Cursor 跑项目 Hooks
---
排除：单靠把 Hook 命令换成 pmemw（GUI 子系统）不能解决“疯狂弹 shell”。
根因是触发频率：full 模板的 postToolUse 匹配 Read|Grep|…，一轮对话可读文件十几次，每次 Cursor 若经 cmd/PowerShell 起进程就会弹一次；
命令里写 python3 … || py … 更是必经 cmd。
正确产品侧做法是 Windows 默认去掉高频 Hook（quiet），并禁止 hooks.json 里用 || / 包装脚本。
