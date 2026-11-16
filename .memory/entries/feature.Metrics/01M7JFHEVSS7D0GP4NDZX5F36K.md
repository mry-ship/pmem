---
id: 01M7JFHEVSS7D0GP4NDZX5F36K
module: feature.Metrics
entity: Citation
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/metrics/cite.py#judge
- src/pmem/metrics/report.py#_citations
revision: git:8455451
author: 1002378395@qq.com
note_date: '2026-11-16'
summary: 采用判定支持够长标题指纹；缓存按版本与正文标题材料重算；不降阈值不按采用排序
verify: uv run pytest tests/metrics/test_metrics.py -k "judge or title_citation"
applies: 改采用判定或收益报告引用统计时
---
需求来源：用户要求优化记忆采用率（查过不用 / 长文漏计）。
必须保持：
1) 采用判定阈值仍为 0.15；对 summary/title 指纹至少 12 的条目与正文覆盖率取 max，不降阈值、不按采用率调检索排序。
2) cites.json stamp 含 CITE_CACHE_VERSION，并纳入正文与标题材料摘要；规则或记忆正文/标题变更后重算。
3) 本对话自写记忆仍按文件创建时间前后各 60 秒排除出返回/采用分母。
入口：metrics/cite.py judge；metrics/report.py _citations。
