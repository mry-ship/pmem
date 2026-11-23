---
id: 01M83NHQDK74GY82GTTTDGGDME
module: feature.Onboarding
entity: Hooks
kind: feature
status: active
supersedes:
- 01M6QT918T2GA7VMHBD2JH106D
- 01M6QWTZRW93JBR5MWFCHB8RSG
anchors:
- src/pmem/generate/templates.py#CURSOR_HOOKS_FULL
- src/pmem/generate/integrations.py#setup_cursor
- README.md
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: init 默认 full；Windows 同开时 Claude hooks 故意为空
source:
  kind: document
---
需求来源：恢复最有效的 Hooks=full，同时避免读者把「Windows 上 Claude hooks 为空」当成漏配。

必须保持：
- pmem init --hooks auto|full 写入完整 CURSOR_HOOKS_FULL；Codex 同步完整。默认 auto 即 full。
- Windows 与 Cursor 同开时 Claude hooks 清空为 {}；单独 Claude 或非 Windows 仍可完整 Hooks。
- 防弹窗：Hook=pmemw、MCP=pmem、无 .cmd/||、无双开 Claude、doctor 告警控制台 python。不要靠拆闸门或读码摘要消黑框。

入口：pmem init（默认 auto→full）；可选 --hooks quiet。README 接入段与已知限制须写明 Claude hooks 为空是故意的。

合并自 2 条功能记录。
