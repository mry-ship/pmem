---
id: 01M59NWMRPAEH9DPNTBFZ51032
module: feature.Metrics
entity: Health
kind: conclusion
status: active
supersedes:
- 01M52G7M64F0DZAHG0HMQS5RQ4
- 01M52J05PZZF9K0HN64KSYPKJ9
- 01M59E3TT9Q3QN38D8EDM6HFTB
- 01M59JBB0KQFARQZPTG3GNAPA1
- 01M59KHGZYNTH7DNWJZJW21RWE
anchors:
- src/pmem/metrics/health.py#build_health
- src/pmem/metrics/health.py#render
- src/pmem/metrics/report.py#build_report
- src/pmem/metrics/health.py#reject_reason
- src/pmem/catalog/migrate.py#stray_moves
- src/pmem/metrics/events.py#MIN_SEARCHES_FOR_IDLE
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 健康报告
- pmem health
- 体检
- 记忆库巡检
- health report
---
结论：健康报告是独立命令 pmem health（metrics/health.py），不并进 pmem report。
report 是收益报告（命中、采用、对照），两者读者和频率不同，合在一起太长。
默认统计 60 天，只列有问题的段落，每段附处理办法。

各节：未登记模块（附相近登记模块；写成别名或已并入模块名的不算，归到“记忆还在旧模块名下”）、疑似重复模块、记忆还在旧模块名下、记忆文件重复、没有归属模块的代码目录（复用 doctor 覆盖率）、检索落空热点（按 模块×议题/关键词 计数）、可能过时的记忆（全部现行记忆做锚点核对）、疑似互相矛盾的记忆、统计期内没检索过的模块（本机检索少于 20 次不列）、被拒绝的写入、MCP 服务被看门狗重启、待确认的种子、零碎记忆可合并、名字相近的议题。

要点：
- 记忆文件重复：同一 id 出现在新旧两个模块目录（拆分/迁移中途失败或手工拷贝），按 id 查找会不确定（confirm、draft_id 可能改到另一份）。
  由 catalog.stray_moves 抛 MigrateError 时作为一节列出，不让整份报告异常；
  处理：删旧目录那份再 pmem migrate tidy --apply。
- 被拒绝的写入按 record_rejected 事件的错误码归类（REJECT_CODES），改提示措辞不影响统计；
  没有 code 的旧事件才按文字匹配（REJECT_REASONS）。
  新增拒绝类型要同时加错误码和 REJECT_CODES 的中文名，否则归为“其他”。
- 看门狗重启只算崩溃和超时，代码更新触发的 reload 不计；原因文字带返回码和方法名，同类问题可能分成几行。
- 闲置阈值 MIN_SEARCHES_FOR_IDLE=20 只在 metrics/events.py 定义，report 和 health 共用，避免两份报告判断不一致。
- 顺带修正：report 的知识资产原用 status != "deprecated" 过滤（不存在该状态），改为只算 active/seed/draft。

风险/局限：
- 检索、拒绝、重启数据只来自本机事件日志 events.jsonl，团队全貌要各人分别看。
- 检索落空里“路径 X（未登记到模块）”依赖 search 事件的 path 字段；早期日志没有该字段，只显示“（按路径检索：路径未登记到模块）”。
- “整模块浏览：当时模块里还没有记忆”是检索当时的状态，后来补了记忆也会在统计期内继续出现。
合并自 5 条记忆。
