---
id: 01M59KHKZWJB4PPHKWARBQSSFH
module: feature.Curation
entity: Seed
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/seed_cmd.py#seed_plan
revision: git:407c1fd
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 种子记忆
- 常改模块
- 热度排序
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：pmem seed 挑“常改、记忆少”的模块时，模块热度改用 catalog 的 module_heat(include_candidates=False)，文件热度经 service.vcs 读取，不再自己遍历文件匹配模块。

原因：同一套“文件热度汇到模块”在 seed、report、sync 各有一份，候选模块算不算、冲突文件怎么归属各写各的；种子只给正式模块提炼，所以显式不算候选。

影响：行为不变，全量测试通过。
