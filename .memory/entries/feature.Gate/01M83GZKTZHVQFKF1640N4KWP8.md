---
id: 01M83GZKTZHVQFKF1640N4KWP8
module: feature.Gate
entity: SpecRead
kind: risk
status: archived
supersedes: []
anchors:
- src/pmem/hooks/guard.py#_guard_spec
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 文档写读完才放行，block 实际可二次放行
verify: 对照 docs/pmem-guide.html 与 _guard_spec 二次放行分支
applies: gate.mode=block 且本对话尚未记到任何 spec_read 时
archived:
  'on': '2026-11-23'
  from: active
  by: 1002378395@qq.com
source:
  kind: code
---
风险：手册写「block 读完才放行」，代码在 pending 均已 spec_offered 且 spec_read 仍空时二次放行。
功能记忆已写明该豁免（Cursor/quiet/Codex 观测不到 Read），但用户文档与设计稿未同步，Claude full 也可走同路径敷衍绕过。
建议文档写明豁免前提；
可观测 Read 的环境坚持读完再放行。
