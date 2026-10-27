---
id: 01M5YA9ABDH5H5J6TVE3J6K727
module: feature.Gate
entity: ReplyDeclaration
kind: feature
status: active
supersedes:
- 01M5YA61WSK15GKHGQRTW2T0V2
anchors:
- src/pmem/hooks/reminders.py#_pmem_declare_line
- src/pmem/hooks/reminders.py#_declarations
revision: git:18bf3e1
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 声明只认修改行；匹配前去掉「标题」引号
verify: uv run pytest tests/hooks/test_gate.py -k "declar or no_conclusion or title_does_not"
applies: stop Hook 能读到 transcript_path 时
source:
  conversation: d46a2963-0c06-4ad1-a10e-c1d8dca6b5fc
---
在 AnalysisWrap 查阅/排查分流与无新结论分段规则之上，必须保持：
- “无需记录”“无新结论”只从【pmem修改】行与旧写法【pmem】行解析；【pmem检索】【pmem查询】行不参与（标题里可能含相同字样）。
- 分段后先去掉「…」引号内文字再匹配关键字，避免“已写功能记录「无新结论分段逻辑」”误触发。
- 其余：按段点名、任一段无点名则查阅/排查全不发、不挡功能记录与 review，同 ReplyDeclaration 上一版。
入口：hooks/reminders.py _pmem_declare_line、_segment_plain、_declarations。
