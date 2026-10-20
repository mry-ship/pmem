---
id: 01M5CGYGZ6X3D3Z3T5XJS714VB
module: feature.Metrics
entity: Report
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py#_repeats
- src/pmem/hooks/gate.py#on_compact
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: v0.3 后对话内重复率仍约 41%，压缩未记事件，报告分不清合理重发与去重失效
verify: 按时间切分 events.jsonl 后用 PMEM_CACHE_DIR 指向切分目录跑 pmem report；修复后报告应单列压缩后重发条数
aliases:
- 对话内去重
- 重复返回
- 上下文压缩
- compact
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
2026-10-20 按 v0.3 上线时刻（2026-10-19 23:37，提交 e637c17）切分本机 events.jsonl 重算：上线前对话内重复返回率 50%（936 条中 466），上线后 41%~43%（296 条中 120 条整条重发，只有 23 条折叠成标题），远未达到 v0.3 验收目标 <5%。
无法判断原因：上下文压缩时 Gate.on_compact 会清空 seen/<对话>.txt（压缩后重发全文是设计内行为），但压缩既不写 events.jsonl 也不进 hooks.log，报告的 _repeats 把压缩后的合理重发也算成重复。
证据：长对话 ca2edda2 的 seen 文件只剩 5 行、且不含之前给过全文的 id，实际发生过清空。
要验收去重效果，先让 on_compact 记一条 compact 事件，_repeats 按压缩切分。
同批对比还确认：pmem report 的“本期新增教训防错类占比 20%”混入了 v0.3 前的记忆，只算 v0.3 后新写教训为 43%（22/51），已达标。
