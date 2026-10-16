---
id: 01M4ZD0C7VYS755CHE1TKQ82M9
module: feature.Gate
entity: GateDefaults
kind: decision
status: active
supersedes:
- 01M4Z7DC744RSMPA76TMNN1BWW
anchors:
- src/pmem/hooks/gate.py
- src/pmem/core/config.py
revision: git:d0b4727
author: 1002378395@qq.com
note_date: '2026-10-15'
---
决定：闸门默认改为强制模式（gate.mode: block），结束提醒默认覆盖“只查了记忆的对话”（gate.analysis_reminder: true）。推翻了之前“默认 warn、排查类对话默认不提醒”的决定。

依据：本仓库开发对话里，改代码涉及 10 个“对话×模块”，只有 1 个是 Agent 主动先查；
warn 只拦一次，Agent 不理也能改，规则文件本身几乎约束不了“先查再改”。
用户明确要求与 TileMatch 原有 hook 同样严格。

强制模式的兜底（避免卡死/死锁）：只要尝试过检索就放行，成败不论——MCP 的 search_memory 在执行前（preToolUse / beforeMCPExecution）就记为已查；
终端 pmem search 同理。
拦截提示写明这两条以及“跳过记忆”。
查哪个模块只放行哪个模块，比 TileMatch“查任意模块全放行”更严。

结束提醒：整个对话只查了记忆、既没改代码也没写记忆时，对查过的模块各提醒一次，可回“无需记录”。写代码的对话里为参考顺带查的模块不提醒，避免噪音；不再要求提问含排查类用语（这些用语只用于 report 统计）。

风险：TileMatch 数据显示写入本就偏多（54% 轮次有写入），提醒可能引出应付式记忆，需在 pmem report 里观察“提醒后写了”的内容质量。
