---
id: 01M83HMRYNTQCKH8EA8P4BCSVQ
module: feature.Gate
entity: SpecRead
kind: correction
status: active
supersedes:
- 01M83GZKTZHVQFKF1640N4KWP8
anchors:
- src/pmem/hooks/guard.py#_guard_spec
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 文档已写明 block 摘录后可二次放行
verify: docs/pmem-guide.html 与 2026-10-23 规格设计稿含再改放行
source:
  kind: document
---
旧风险写手册「block 读完才放行」与代码二次放行不一致。
已按产品决定只改文档、不改 Claude full 行为：手册、模块规格设计稿与 architecture 已写明——Cursor/quiet/Codex 往往看不到 Read 时，摘录给过且本对话尚未记到任何成功读取则再改放行；
一旦记到过读取，未读完继续拦。
功能记忆「已读只认成功 Read」仍成立。
