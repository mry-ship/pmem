---
id: 01M5CJXN5NNXPBW37X52QC9KMS
module: feature.Metrics
entity: Report
kind: correction
status: active
supersedes:
- 01M5CGYGZ6X3D3Z3T5XJS714VB
anchors:
- src/pmem/metrics/report.py#_repeats
- src/pmem/metrics/report.py#_compactions
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 按压缩切分后 v0.3 上线后对话内重复约 4%，去重有效；余量来自变量模块名的终端检索
verify: uv run pmem report --days 30，看“对话内重复”一行和“期间上下文压缩 N 次”的拆分
aliases:
- 去重失效
- 重复率
- 验收
- 上下文压缩
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
更正：旧结论说 v0.3 后对话内重复仍约 41%，那是把压缩后合理重发的全文也算成了重复。
2026-10-20 按压缩切分重算本机 events.jsonl（30 天）：整体重复 15%（不切分时 50%），其中 20 多次压缩靠读代码摘要推断。
只看 v0.3 上线后：MCP 检索 3/287（1%），带对话 id 的终端检索 12/70，按时间归到对话的终端检索 0/14，合计 15/371 约 4%，达到 <5% 的验收目标。
上线前同口径：终端 30%、MCP 7%。
余量主要来自一次循环里用变量写模块名的 6 次终端 pmem search：Hook 认不出模块，没有交接对话 id，全文没写进去重记录，之后字面模块名的检索又给了全文（即“模块名要写字面值”的已知限制）。
剩下几条可能是推断看不到的压缩，以后有 compact 事件就能分清。
仍成立：防错类占比只算 v0.3 后新写教训为 43%，已达标。
