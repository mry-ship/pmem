---
id: 01M6N83TNKSKKP14JFGFDTME01
module: feature.Onboarding
entity: Hooks
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/templates.py#codex_hooks
- src/pmem/generate/integrations.py#setup_codex
revision: git:4d776a5
author: 1002378395@qq.com
note_date: '2026-11-05'
summary: Windows quiet 也收窄 Codex：无 prompt/stop/compact
verify: pytest tests/test_integrations.py -k quiet -q
applies: Windows；pmem init --hooks quiet|auto
---
功能：pmem init --hooks quiet/auto(Windows) 时 Codex 只写 PreToolUse+PostToolUse，去掉 UserPromptSubmit/Stop/PreCompact，避免再被 init 合回全套狂弹窗。
Cursor quiet 仍只闸门+afterMCP；
与 Cursor 同开时 Claude Hooks 清空。
美术仓另用 pyw 起 pmem_art hook。
验证：pytest tests/test_integrations.py -k quiet。
