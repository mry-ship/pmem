---
id: 01M5MBG7P7CNEESH27MGF9210Q
module: feature.Spec
entity: SourceDenom
kind: exclusion
status: active
supersedes: []
anchors:
- .cursor/skills/pmem-spec/SKILL.md
revision: git:077798b
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 排除：用源码行数或未落地策划稿当九成分母
verify: 技能写明源码行数和代码里没有的策划不计入分母
applies: 给规格复现率打分、或想靠粘贴源码提高完成度时
aliases:
- 源码行数
- 凑九成
source:
  conversation: 70760b3a-0dd4-4cc7-a429-f7c5252b5a05
---
排除：把「能复现百分之多少原始内容」按源码行数、内部函数、测试夹具来算。
排除：为把分数凑到九成，去掉独立策划稿的 design-gap，或把模板全文粘进规格。
证据：用户要求至少 90% 才算有用，同时规格设计明确不拷源码、看不到的完整策划不要编。
处理：九成只衡量已实现对外契约；策划留空不计入分母。
