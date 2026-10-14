---
id: 01M4XF770TCRKHWCK45QAKNC1V
module: feature.Metrics
entity: Report
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/metrics/report.py
- src/pmem/vcs/svn.py
revision: git:a0936e7
author: 1002378395@qq.com
note_date: '2026-10-14'
---
根因：收益报告里的“新写记忆”原先只统计事件日志中的 record 事件。Agent 在终端里带 PMEM_NO_EVENTS=1 跑 pmem record 时不记事件，本仓库实测 17 条记忆，报告只显示其中一部分；“结束提醒后写了几次”同样漏算。

处理：
- “新写记忆”改为直接统计记忆文件：作者是本机用户、且 ULID 时间在统计期内的条目，类型分布也取自文件；
- 提醒转化同时认 MCP 写入事件、Hook 侧的 record_call 事件（终端写入），以及记忆文件里的 source_conversation。

口径变化：“新写记忆”只算本机作者，队友同步过来的记忆不计入（它们算在知识资产的“本期新增”里）。

另外：报告和 doctor 都会提示本机未提交的记忆数。坑：SVN 下如果 .memory 目录本身未加入版本库，`svn status <子目录>` 只给 W155010 警告、退出码为 0、列表为空，计数会是 0。必须先用 svn info 判断目录是否已纳入版本库，未纳入时其中的 .md 全部算未提交。
