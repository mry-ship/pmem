---
id: 01M59YER88RFBGZSS50K1ZX6B8
module: feature.Onboarding
entity: Init
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/init_cmd.py#run_init
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 重复 init
- --gate 不生效
- --type 不生效
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：pmem init 重复运行时，显式给了 --gate（config.yaml 已存在）或 --type（config.yaml 与 modules.yaml 都已存在）却没生效，在输出里单列“以下参数没有生效”，并说明该改 config.yaml 的 gate.mode / project.type 和 categories。
仍然不覆盖已有配置。
为区分“没传”和“传了默认值”，--gate 默认值改为 None，在 run_init 里再取 block。
原因：原先静默忽略，用户以为闸门力度或项目类型已改（issue #11）。
不自动改配置的理由：config.yaml 可能有团队手工调整和注释，init 的约定是只替换自己生成的 Hook 和规则。
