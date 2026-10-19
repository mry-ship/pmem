---
id: 01M59KNQYHWQ5NEQ2G0YP6GH5A
module: feature.Metrics
entity: Report
kind: correction
status: active
supersedes:
- 01M51VN952426K91GQ1ZPANTBR
anchors:
- src/pmem/metrics/report.py#_link_cli_searches
- src/pmem/metrics/report.py#build_report
revision: git:12d69d1
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 提醒后查了
- 终端检索关联对话
- search_call
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
更正（2026-10-19）：闸门改为终端 pmem search 执行完、输出里看得到模块才登记后，search_call（via=cli）在命令执行之后才写，输出里看不到时写 search_call_unseen。
收益报告原先只把无对话 id 的 search 事件关联到它之前 30 秒内的 search_call，顺序颠倒后终端检索会全部丢失对话 id，“对话对照”和命中统计偏低。
现在前后 30 秒内取时间最近的一条，search_call_unseen 也算（检索确实跑了），旧日志照样能关联。

仍有效：“改代码前被提醒先查，随后真的查了”按 search_call 和 mcp_search 两种事件计算。
MCP 检索只在 afterMCPExecution 写 mcp_search（带模块和返回的记忆 id），preToolUse、beforeMCPExecution 不再写 search_call；
只统计 search_call 会漏掉 MCP 检索。
早期日志里一次 MCP 检索记过两条 search_call，不影响这项转化率，因为它只看拦截之后有没有对应检索。

证据：新增用例（search_call 写在检索之后）修前命中对话数为 0，修后为 1。
