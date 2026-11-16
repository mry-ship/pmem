---
id: 01M7JH5AWE3R8VBPSRK3ZQ4XZB
module: feature.Onboarding
entity: AgentSetup
kind: correction
status: active
supersedes: []
anchors:
- README.md
- docs/pmem-guide.html
- docs/architecture.md
- src/pmem/generate/integrations.py
revision: git:974e245
author: 1002378395@qq.com
note_date: '2026-11-16'
summary: 更正：Claude Code 与 Codex 已在真实会话验证可用，文档不再写只做过模拟测试
verify: rg 模拟测试 README.md docs/pmem-guide.html docs/architecture.md
applies: 读 README/手册/Wiki 里关于 Claude、Codex 成熟度时
---
更正：文档与 Wiki 里「Claude Code、Codex 的接入只做过模拟测试」已过时。
负责人已深度适配并在真实会话验证可用；
README、使用手册、架构说明与 Wiki「闸门与 Hooks」改为「Cursor / Claude Code / Codex 均已在真实会话验证可用」。
仍成立：Cursor 纯问答要等回合结束才核对；
Claude / Codex 可在提问时附摘要；
Windows+Cursor 同开时 Claude hooks 为空是预期。
细节以 pmem init 与 pmem doctor 为准。
