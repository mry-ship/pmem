---
id: 01M6QWTZRW93JBR5MWFCHB8RSG
module: feature.Onboarding
entity: Hooks
kind: feature
status: active
supersedes: []
anchors:
- README.md
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: README 写明 Windows+Cursor 时 Claude hooks 为空是预期
verify: README 含 hooks 写成 {} 与「不是漏配」；claude_hooks(paired_with_cursor=True) 在 win32
  为空
applies: 读 README 或查 .claude/settings.json 时
---
需求来源：读者看到默认 Hooks=full，又看到 .claude/settings.json hooks:{}，易当成漏配。
必须保持：Cursor 默认 full；Windows 与 Cursor 同开时 Claude hooks 清空为 {}；单独 Claude / 非 Windows 仍可完整 Hooks。
入口：README 接入段与已知限制；行为仍由 pmem init / claude_hooks 实现。
