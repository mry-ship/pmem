---
id: 01M7WFT4PHASTFD9YC5BXPPVAD
module: feature.Retrieval
entity: EnforcedBy
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py#_check
- src/pmem/index/graph.py#digest
revision: git:c4144ab
author: 1002378395@qq.com
note_date: '2026-11-20'
summary: enforced_by 参与过期核对；已由规则保障的教训整体靠后排
verify: uv run pytest tests/index/test_anchors.py -k enforced_by tests/index/test_graph.py
  -k enforced
applies: 改过期核对或读码摘要排序时
---
需求来源：v0.7——规则改了记忆要需核实；
已由规则保障的教训少占摘要名额。
必须保持：enforced_by 路径参与过期核对；
规则文件不存在/改过时 check 写「规则文件 …」；
读码摘要 digest、拦截 pitfalls、全项目坑排序时，已由规则保障的整体排在未保障之后（排序键先 e.enforced，再类型序），名额优先给仍需靠记忆防的。
适用：改过期核对或读码摘要/拦截排序时。
入口：index/anchors.py、index/graph.py#digest。
