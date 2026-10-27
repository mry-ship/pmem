---
id: 01M59R05JVPBPEWZMB0MZYCB2P
module: feature.Tools
entity: SearchLog
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/service/search.py#search
- src/pmem/metrics/health.py#_misses
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 检索落空
- 路径未登记
- 按路径检索没结果
- miss
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:14.279+08:00'
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：search_memory 写入的 search 事件增加 path 字段（转成项目内相对路径；项目外的绝对路径原样保留），只在调用时带了 path 才写。
原因：按路径检索但路径没登记到任何模块时，事件里没有模块、议题和关键词，健康报告只能显示“（按路径检索：路径未登记到模块）”，事后查不出是哪个文件，也就没法补 modules.yaml。
影响：健康报告的检索落空热点现在按路径分别计数，显示为“路径 X（未登记到模块）”；早期没有 path 的日志仍按旧文字归为一行。事件日志只在本机缓存目录，不进版本库。
