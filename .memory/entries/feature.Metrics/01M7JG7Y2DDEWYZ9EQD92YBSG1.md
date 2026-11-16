---
id: 01M7JG7Y2DDEWYZ9EQD92YBSG1
module: feature.Metrics
entity: Citation
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py#_citations
- src/pmem/metrics/cite.py
revision: git:8455451
author: 1002378395@qq.com
note_date: '2026-11-16'
summary: 更正：采用缓存 stamp 须含正文与标题材料摘要，改 summary 也要重算
verify: uv run pytest tests/metrics/test_metrics.py -k title_citation
---
更正：采用判定改为「够长标题与正文取较大覆盖率」后，cites.json 若只按对话记录 mtime 与记忆 id 做 stamp，改 summary/正文不会重算，报表会沿用旧 verdict。
现行：stamp 形如 v3:对话记录mtime:记忆id列表:材料摘要；材料摘要对每条 id 的标题与正文做 sha1；判定规则变更时递增 cite.py 里的 CITE_CACHE_VERSION。
阈值仍为 0.15；不按采用率调检索排序。
