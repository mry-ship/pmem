---
id: 01M7YZVGQFCG2MSN88S0BBG25Y
module: feature.Onboarding
entity: Roadmap
kind: decision
status: active
supersedes: []
anchors: []
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: 路线冻结为使用效果验证：P1 无误用不加机制，P2 无收益不进 P3
scope: project
verify: 后续改动仍落在 Gate、检索短提示、pmem-minimal、pmem-review、spec closed；没有新的失效判定或采用率算法
applies: 接着做记忆时效、证据使用或规格对照，或想在这条路线上加机制、指标、排序或检查器时
aliases:
- 路线图
- 使用效果验证
- 冻结
source:
  conversation: d2865e0a-9495-4cc9-8dbf-24314389d186
---
决定：这条路线冻结为使用效果验证。原因：时效、证据和规格机制已经在，缺的是 Agent 会不会用。再加判定器或指标，会把「有没有误用」量成别的东西，每次检索也更贵。

排除：从零再建失效或可信度；用字面采用率证明遵守了需核实；把阅读顺序写进 pmem-quality 或记忆规则正文。前者问答不会执行，后者会进 bench 的有记忆一组。

P0 三态不能互相代替：模板已在仓库；旧项目重新 init 才有文件；是否遵循只看真实对话。P1 只抽查需核实之后有没有先对照代码，问答和编码都看。不加指标，不改采用率，不做版本触发。没有这种误用，不改提示、不加机制。

入口：查没查过看 Gate；
需核实、适用条件和来源只写检索短提示；
最小方案用 pmem-minimal；
规格和质量用 pmem-review；
闭集用 spec closed。
P2 没有减少误用就不进 P3。
P3 只加未触及、符合、违反、待核实；
待核对预填不能当违反。
暂缓影响分析、结果反馈、版本触发和可信度排序。
