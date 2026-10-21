---
id: 01M5EJPMMH2ANPBY1MNDV2P7ZV
module: feature.Metrics
entity: Report
kind: conclusion
status: active
supersedes:
- 01M4XF770TCRKHWCK45QAKNC1V
- 01M59KNQYHWQ5NEQ2G0YP6GH5A
- 01M5CFK17EASJ4YNGJTNPJM71V
- 01M5CJXN5NNXPBW37X52QC9KMS
anchors:
- src/pmem/metrics/report.py
- src/pmem/vcs/svn.py
- src/pmem/metrics/report.py#_link_cli_searches
- src/pmem/metrics/report.py#build_report
- src/pmem/metrics/report.py#_repeats
- src/pmem/metrics/report.py#_compactions
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 收益报告统计口径：新写记忆数文件、检索按前后 30 秒关联、重复按压缩切分
verify: uv run pytest tests/metrics/test_metrics.py
aliases:
- 收益报告
- 统计偏低
---
结论：收益报告（pmem report）各项统计口径的现行规则和踩过的坑。
1) “新写记忆”直接统计记忆文件：作者是本机用户、ULID 时间在统计期内的条目，类型分布也取自文件。
   原先只数事件日志里的 record 事件，终端带 PMEM_NO_EVENTS=1 写入的全漏。
   只算本机作者，队友同步来的算在知识资产“本期新增”里。
2) 提醒转化认三种来源：MCP 写入事件、Hook 侧 record_call（终端写入）、记忆文件里的 source_conversation。
   “被提醒先查、随后真的查了”按 search_call 和 mcp_search 两种事件算：MCP 检索只在 afterMCPExecution 写 mcp_search，只看 search_call 会漏掉。
3) 终端检索的 search_call（via=cli）在命令执行之后才写，看不到输出时写 search_call_unseen（也算检索跑了）；
   无对话 id 的 search 事件取前后 30 秒内时间最近的一条关联（原先只看之前 30 秒，顺序颠倒后全部丢对话 id）。
4) “打开 gate.analysis_reminder”的建议要读实际配置：只有存在“查过但没写”的对话、且提醒未生效（analysis_reminder 为假或 gate.mode 为 off）时才给。
   目前只测了开启情况（tests/metrics/test_metrics.py），关闭情况没有用例。
5) 对话内重复要按压缩切分：2026-10-20 本机 30 天整体 15%（不切分 50%）；
   v0.3 后 MCP 1%、终端合计约 4%，达到 <5% 目标（上线前终端 30%、MCP 7%）。
   曾以为 v0.3 后仍约 41%，实为把压缩后合理重发也算成了重复。
   余量主要来自循环里用变量写模块名的终端检索。
   防错类占比（v0.3 后新写教训）43%，已达标。
坑：SVN 下 .memory 未加入版本库时 svn status <子目录> 只给 W155010 警告、退出码 0、列表为空，未提交计数会是 0；
必须先 svn info 判断，未纳入时其中的 .md 全算未提交（报告和 doctor 都提示本机未提交记忆数）。
合并自 4 条记忆。
