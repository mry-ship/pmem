---
id: 01M59KHGZYNTH7DNWJZJW21RWE
module: feature.Metrics
entity: Health
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/metrics/events.py#MIN_SEARCHES_FOR_IDLE
- src/pmem/metrics/report.py#build_report
- src/pmem/metrics/health.py#build_health
revision: git:407c1fd
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 闲置模块阈值
- 热度汇总
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：“检索次数达到多少才判断模块闲置”的阈值 MIN_SEARCHES_FOR_IDLE（20）只在 metrics/events.py 定义一次，report 和 health 都从这里导入。
report 的模块热度改用 catalog 的 module_heat，文件热度经 service.vcs 读取。

原因：原先两个文件各写一个 20，改一处就会让两份报告对“闲置”的判断不一致；热度汇总也和 seed、sync 各自实现。

影响：行为不变，全量测试通过。
