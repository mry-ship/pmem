---
id: 01M59YEY70YTTPSRNXRJK2ER2Q
module: feature.Curation
entity: Seed
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/seed_cmd.py#unused_options
- src/pmem/cli/seed_cmd.py#run_seed
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- seed 参数被忽略
- 参数冲突
- 种子确认
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
决定：pmem seed 遇到会被悄悄忽略的参数组合时报错退出（返回 2），而不是照常执行另一个动作：
- --plan 不能同时给记忆 id、--module、--accept、--reject、--all；
- --top 只配合 --plan（默认值改为 None，用时取 10）；
- --all 只配合 --accept，且不能再给 id 或 --module；
- 给了 id 不能再给 --module，且必须配 --accept 或 --reject。
原因：原先例如 pmem seed <id>（没带 --accept）只列出待确认清单，--accept <id> --module X 忽略 --module，用户以为已经确认或按模块处理了（issue #11）。
风险：脚本里原本能跑通的冗余参数写法现在会报错；技能和健康报告里给出的命令（--accept --module、--reject <id>、--plan）均不受影响。
