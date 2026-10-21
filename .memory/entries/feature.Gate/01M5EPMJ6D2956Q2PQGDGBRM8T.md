---
id: 01M5EPMJ6D2956Q2PQGDGBRM8T
module: feature.Gate
entity: ReplyDeclaration
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/reminders.py#_declarations
- src/pmem/hooks/reminders.py#on_stop
- src/pmem/hooks/payload.py#turn_reply_text
- src/pmem/core/config.py
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 回复结尾【pmem…】行声明“无需记录”“无新结论”的不再追加结束提醒；只改文档不提醒
verify: uv run pytest tests/hooks/test_gate.py -k "declar or docs_only"
applies: stop Hook 能读到 transcript_path 时；读不到就按旧规则提醒
aliases:
- 结束提醒
- 无需记录
- 【pmem修改】
- 弹框提醒
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：用户（2026-10-21）反感回合结束又弹一条“[pmem] 本轮修改了 X”的新消息，要求在当次回复里用【pmem检索】【pmem查询】【pmem修改】行说清楚。
必须保持的行为：
- stop 从 transcript 读本轮 Agent 的回复文字（payload.turn_reply_text），只认以【pmem…】开头的行（正则 【pmem[^】]{0,6}】，新写法【pmem修改】和旧写法【pmem】都认）。
- 行内按“；”分段：段里有“无需记录”时只免提醒该段点了名的模块；段里有“无新结论”时不发“只查了记忆”的提醒。
- 没有前缀的普通文字里写“无需记录”不算；既没写记忆也没声明的模块照旧追加提醒兜底。“提问涉及的模块没查过”的提醒不受声明影响。
- gate.record_exempt 默认含 **/*.md、**/docs/**：只改文档的模块不要求写功能记录。
入口：src/pmem/hooks/reminders.py（_declarations、on_stop）、hooks/payload.py（turn_reply_text）、core/config.py。
