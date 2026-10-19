---
id: 01M59JBB0KQFARQZPTG3GNAPA1
module: feature.Metrics
entity: Health
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/metrics/health.py#build_health
- src/pmem/catalog/migrate.py#stray_moves
revision: git:df9b06c
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 重复记忆
- 同 id 两份
- 迁移残留
- 健康报告
verified: '2026-10-19'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
结论：健康报告（pmem health）新增“记忆文件重复”一节。同一个 id 出现在两个模块目录（多半是拆分、迁移中途失败或手工拷贝留下的）时列出来，并提示用 pmem migrate 的同类收尾处理。
原因：这种重复会让按 id 查找的结果不确定（confirm/draft_id 可能改到另一份），而且原先只有 migrate 自己能发现。
health 现在直接用 catalog 包（stray_moves、MigrateError），不再反向导入 cli。已知不足（见 GitHub issue）：部分判断仍在匹配中文错误文案，改文案会让统计失效。
