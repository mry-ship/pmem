---
id: 01M5CAVH8YBS1P63AJ88KJNTRG
module: feature.Gate
entity: FeatureReminder
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/reminders.py#on_stop
- src/pmem/hooks/reminders.py#_record_required
- src/pmem/hooks/guard.py#_pitfalls
revision: git:f340df3
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 结束提醒按模块要功能记录，免记录文件不提醒，拦截列文件功能记录
aliases:
- 结束提醒
- 功能记录
- 免记录
---
用户要求（2026-10-19）：正常做功能要有完整记录，结束提醒不能只问教训；用户要求的行为在改文件前就要被看到。
必须保持：结束提醒要求每个改过的模块写一条功能记录（需求来源、必须保持的行为、applies、入口），另有教训再写对应类型；
确实不需要时回复“无需记录：原因”。
只改了 gate.record_exempt 里文件的模块不提醒（_record_required），stop 事件记下 required 供报告算覆盖率。
改前拦截除排除项、风险、更正外，列出锚点就是目标文件的功能记录。
入口：hooks/gate.py 的 on_stop、_record_required、_pitfalls。
