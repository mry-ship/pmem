---
id: 01M5YA61WSK15GKHGQRTW2T0V2
module: feature.Gate
entity: ReplyDeclaration
kind: feature
status: active
supersedes:
- 01M5EPMJ6D2956Q2PQGDGBRM8T
anchors:
- src/pmem/hooks/reminders.py#_declarations
- src/pmem/hooks/reminders.py#on_stop
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 【pmem】行分段：无新结论只挡查阅/排查，不挡功能记录与提问审查
verify: uv run pytest tests/hooks/test_gate.py -k "declar or docs_only or no_conclusion"
applies: stop Hook 能读到 transcript_path 时
source:
  conversation: d46a2963-0c06-4ad1-a10e-c1d8dca6b5fc
---
需求来源：用户要求在当次回复【pmem修改】行自检，减少结束 followup。
必须保持：
- stop 从 transcript 读本轮 Agent 回复（turn_reply_text），只认以【pmem…】开头的行（正则 【pmem[^】]{0,6}】）。
- 行内按“；”分段。“无需记录”只免同段点名的模块的功能记录与规格提醒。
- “无新结论”：各段点名的模块取并集，只放过这些模块的查阅/排查提醒（analysis_pending、consulted_pending）；
  任一段没点名则查阅/排查提醒全部不发，与段顺序无关。
  无新结论不放过改了代码的功能记录提醒；
  提问审查（review）不受声明影响。
- 普通文字里写“无需记录”不算。
- gate.record_exempt 默认含文档路径：只改文档的模块不要求功能记录。
入口：hooks/reminders.py _declarations、on_stop；hooks/payload.py turn_reply_text。
