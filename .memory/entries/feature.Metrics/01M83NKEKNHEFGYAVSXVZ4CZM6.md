---
id: 01M83NKEKNHEFGYAVSXVZ4CZM6
module: feature.Metrics
entity: Citation
kind: decision
status: active
supersedes:
- 01M4X5HC6TNDY2JAVJZFJKWBT1
- 01M4Z6PF0W0JKGVBCR03Z5RC3S
- 01M7JFG07TK8428FQ6PD44SC5Q
- 01M7JG7Y2DDEWYZ9EQD92YBSG1
- 01M7YZCXJ92SN9GFYNX5A0NR4K
anchors:
- src/pmem/metrics/cite.py#judge
- src/pmem/metrics/report.py
- src/pmem/metrics/report.py#_citations
- src/pmem/metrics/cite.py
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 「记忆被采用」只看字面重合，不用语义相似度
aliases:
- 采用率
- 字面重合
- cites
source:
  kind: document
---
现状：「记忆被采用」只看字面重合，不用语义相似度。

判定：中文 4 字片段 + 标识符，阈值 0.15。
对指纹至少 12 的 summary/title 与正文分别算覆盖率，取较大值。
不降阈值（降到 0.05 会把近失算成采用），也不按本机采用率调检索排序。
换说法不算。
本对话刚写的记忆不算：按记忆文件创建时间，对话首尾各放宽 60 秒，不依赖写入事件是否带对话 id。

它看不出 Agent 有没有先对照需核实的锚点、有没有判断 applies、有没有因证据弱丢掉记忆。
把过期结论写进回复，采用率会反而升高。
被 supersedes 的记忆现行检索不返回，无法观察「有没有正确处理替代」。
健康报告的过期条数是库存不是误用次数。
bench 的 on/off 不加载 Hooks。

报告在离线计算并缓存 cites.json，不放进 stop Hook。
stamp 形如 v3:对话记录mtime:记忆id列表:材料摘要；
材料摘要对标题与正文做 sha1；
改判定规则时递增 cite.py 的 CITE_CACHE_VERSION。
另有「记忆使用」：同一对话只算一次；
返回 3 次以上却没用到的列出；
检索少于 20 次不显示「期内从未被检索」。
数据只来自本机。
验收抽查带 stale 的对话后续回复，不要为验收改算法。

复核阈值：scripts/calibrate_cite.py。合并自 5 条教训（功能记录另条保留必须保持的行为）。
