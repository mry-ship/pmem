---
id: 01M5Y5AH2568RGGRVK84NJN5SH
module: feature.Curation
entity: WriteHints
kind: feature
status: active
anchors:
- src/pmem/service/record.py
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 缺 summary 时提示写可直接复述的结论句，利于采用统计
verify: rg 可直接复述 src/pmem/service/record.py
applies: 改写入 summary 提示时
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
需求来源：记忆被采用偏低（字面重合保守下限），摘要不可复述时 Agent 换说法复述会漏计。
必须保持：
1) 写入未填 summary 的提示要求补一句可直接复述的结论（限 SUMMARY_MAX）。
2) 功能记录仍检查需求来源与必须保持的行为（见同议题既有功能记录，本条不替代它）。
入口：src/pmem/service/record.py SUMMARY_HINT。
