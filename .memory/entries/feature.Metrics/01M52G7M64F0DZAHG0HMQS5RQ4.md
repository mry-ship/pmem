---
id: 01M52G7M64F0DZAHG0HMQS5RQ4
module: feature.Metrics
entity: Health
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/metrics/health.py#build_health
- src/pmem/metrics/health.py#render
- src/pmem/metrics/report.py#build_report
revision: git:4672c28
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 健康报告
- 体检
- health
- 检索落空
- 知识资产
verified: '2026-10-19'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：设计里的“健康报告”做成独立命令 pmem health（src/pmem/metrics/health.py），不并进 pmem report。原因：pmem report 已经是收益报告（命中、采用、对照），两者读者和频率不同，合在一起太长。

内容（只列有问题的段落，每段附处理办法）：未登记模块（写入时自动新建，附相近的登记模块；写成别名或已并入模块名的记忆不算未登记，归到“仍在旧模块名下”）、疑似重复模块（短名相同跨大类，或按实体名相近规则判定，同一组只列一次）、仍在旧模块名下的记忆、没有归属模块的代码目录（复用 doctor 的覆盖率统计）、检索落空热点（没返回任何记忆，或按议题没找到退回整模块，按 模块×议题/关键词 计数）、可能过时的记忆（对全部现行记忆做锚点核对）、统计期内没检索过的模块（本机检索少于 20 次时不算）、被拒绝的写入（按 record_rejected 事件的错误文字归类）、待确认的种子、可合并议题、相近议题名。默认统计 60 天。

同时修正 pmem report：知识资产原来用 status != "deprecated" 过滤（并不存在这个状态），归档记忆会被算进有效记忆，改为只算 active/seed/draft。

局限：检索与拒绝数据只来自本机事件日志，团队全貌需要各人分别看；过时核对和目录覆盖统计对大库可能要几秒。落空项“整模块浏览：当时模块里还没有记忆”是检索发生时的状态，后来补了记忆也会留在统计期内。
