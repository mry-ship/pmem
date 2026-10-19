---
id: 01M52G7P3FMY0VYA8HHKYWF9WX
module: feature.Onboarding
entity: Skills
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/init_cmd.py#_write_skills
- src/pmem/cli/doctor_cmd.py#run_doctor
revision: git:4672c28
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 技能
- skill
- 种子记忆
- 接入流程
verified: '2026-10-19'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：pmem init 生成的项目技能增加 pmem-seed（模板 SEED_SKILL），与 bootstrap、compact、normalize 一起写到 .cursor/skills 和 .claude/skills；pmem-bootstrap 最后一步提示接着“按 pmem-seed 技能提炼种子记忆”。README 接入步骤加第 6 步（建议），可选操作表加 migrate、archive、health。

原因：模块划分完记忆库是空的，种子记忆是接入流程的自然下一步，放在 bootstrap 结尾提示比让用户自己翻文档可靠。

影响：已接入项目重新运行 pmem init 才会得到新技能；本仓库的 .cursor/skills 已用 _write_skills 重新生成。doctor 计算现行条数时，归档记忆的替代关系同样生效（与检索口径一致）。
