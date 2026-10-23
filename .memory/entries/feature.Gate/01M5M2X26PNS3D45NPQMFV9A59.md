---
id: 01M5M2X26PNS3D45NPQMFV9A59
module: feature.Gate
entity: SpecReminder
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/hooks/reminders.py#_pending_specs
revision: git:6096f71
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 规格提醒缺省不响；打开后按目录补美术文件
verify: uv run pytest tests/hooks/test_gate.py -q -k spec
applies: 回合结束判断要不要提醒更新模块规格时
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
更正：结束提醒里 spec.reminder 缺省按关处理，与配置默认值一致。设为 true 且闸门不是 off 时仍提醒一次。
提醒正文改为：目录里还没有美术设计.md 时补上这一份。不再写「插在策划和程序之间」。
仍成立：与功能记录用同一份改了行为的模块名单；声明无需记录、只改免记录文件、已写过四份正文之一的不提醒；目录 index.md 不算更新；每条以 [pmem] 开头。
