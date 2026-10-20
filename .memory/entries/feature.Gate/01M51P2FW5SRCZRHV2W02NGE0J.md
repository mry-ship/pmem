---
id: 01M51P2FW5SRCZRHV2W02NGE0J
module: feature.Gate
entity: GateDefaults
kind: decision
status: active
supersedes:
- 01M4ZD0C7VYS755CHE1TKQ82M9
anchors:
- src/pmem/hooks/reminders.py#on_stop
- src/pmem/generate/templates.py
revision: git:6d89f59
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 无需记录
- 自动写记忆
- 结束提醒
---
决定：闸门默认用强制模式（gate.mode: block）；结束提醒默认也覆盖“整个对话只查了记忆”的情况（gate.analysis_reminder: true）。记忆由 Agent 自动写，不再提供“回复无需记录”的出口。

依据：
- 本仓库的开发对话里，改代码一共涉及 10 个“对话×模块”，只有 1 个是 Agent 主动先查的；warn 档只拦一次，规则文件本身几乎约束不了“先查再改”。
- 结束提醒原先允许回复“无需记录”。
  实际出现过 Agent 把真实的设计决定（模块名匹配阈值、新开关默认值、init 新增的 Hook）判成“机械改动”而跳过。
  用户明确要求自动写记忆：靠人留意提醒，漏掉就没了；
  followup_message 在 Cursor 里显示为一条用户消息，看起来像在要用户回复。

现行做法：
- 改了模块的代码却没写记忆：stop 的 followup 要求 Agent 直接为每个模块写一条（为什么这样改、影响范围、风险；已有记忆说的就是这件事时用 supersedes 更新），不要询问用户。
- 只查了记忆：有新结论就写，没有就说明“已核对，无新结论”。
- 规则模板写明：到了时机直接写，结束回答前每个改过的模块写一条，只有纯格式化、改错别字可以不写。

强制模式的兜底：只要尝试过检索就放行（MCP 在执行前记为已查，终端 pmem search --module 同理）；查了哪个模块只放行哪个模块。

风险：提醒可能引出应付式记忆，需要在 pmem report 里观察“提醒后写下”的记忆质量。
