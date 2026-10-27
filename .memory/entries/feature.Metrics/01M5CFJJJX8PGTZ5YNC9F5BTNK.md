---
id: 01M5CFJJJX8PGTZ5YNC9F5BTNK
module: feature.Metrics
entity: Health
kind: conclusion
status: active
supersedes:
- 01M59NWMRPAEH9DPNTBFZ51032
anchors:
- src/pmem/metrics/health.py#build_health
- src/pmem/metrics/health.py#render
- src/pmem/metrics/health.py#reject_reason
- src/pmem/metrics/health.py#_skipped
- src/pmem/catalog/migrate.py#stray_moves
- src/pmem/metrics/events.py#MIN_SEARCHES_FOR_IDLE
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: pmem health 独立于 report，默认 60 天，只列有问题的段落并附处理办法
aliases:
- 健康报告
- pmem health
- 体检
- 记忆库巡检
- health report
verified: '2026-10-27'
verified_at: '2026-10-27T15:48:07.123+08:00'
---
结论：健康报告是独立命令 pmem health，不并进 pmem report（收益报告），两者读者和频率不同。默认统计 60 天，只列有问题的段落，每段附处理办法。
各节（更正：旧清单缺了后四节）：未登记模块（附相近模块和转正提示）、疑似重复模块、记忆还在旧模块名下、记忆文件重复、没有归属模块的代码目录、检索落空热点、可能过时的记忆、疑似互相矛盾、没检索过的模块（本机检索少于 20 次不列）、被拒绝的写入、看门狗重启、待确认的种子、零碎记忆可合并、名字相近的议题、同一议题反复更正，以及改了代码却没写功能记录、建议归档、清理待核对、召回偏低。
要点：记忆文件重复由 stray_moves 抛 MigrateError 时作为一节列出，不让整份报告异常；
被拒写入按错误码归类（REJECT_CODES），新增拒绝类型要同时加码和中文名；
看门狗重启只算崩溃和超时；
MIN_SEARCHES_FOR_IDLE=20 只在 events.py 定义。
局限：检索、拒绝、重启数据只来自本机 events.jsonl；早期日志没有 path 字段；“当时模块里还没有记忆”是检索当时的状态。
