---
id: 01M83QECKMTSG2WR391MQR5DFX
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes:
- 01M7Z7W2V2WGHM5Z7A2CEVGKTP
- 01M83HMQ2PEK00SYCKRTGNZWC1
anchors:
- README.md
- docs/pmem-guide.html
- docs/architecture.md
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 首页、手册和架构已同步到 0.7.4，二次放行口径仍在
verify: README 与手册含「当前版本 0.7.4」；architecture 文首含 0.7.4；路线表 v0.6 不含规格提醒默认不提示
applies: 改 README/手册/架构/设计路线或发版同步时
source:
  conversation: 913a2b7e-59bf-4672-aac5-d3572e39cc75
  kind: document
---
需求来源：发 0.7.4 时同步首页、手册和架构，并接上 0.7.3 文档里仍要保持的口径。

必须保持：
1) README「效果」与手册「收益与适用场景」开头有「当前版本 0.7.4」表，并写明效果数字沿用 2026-11-21 报告（本版不改排序和采用判定）。
   表里保留 v0.7 到 v0.7.3 能力行，并加 v0.7.4 能力行。
   手册页眉页脚、README 版本徽章为 0.7.4。
   路线表当前版本是 0.7.4。
2) docs/architecture.md 文首写明当前安装包 0.7.4 相对 0.7.3 的增量，并写明 0.7.3 的工程质量技能、规格默认先读、reading_hint 与二次放行仍然成立。
3) 设计稿 §14 路线表含 v0.7.2 / v0.7.3 / v0.7.4 行；§14.7 注明后续补丁。v0.6 行不再写「规格提醒默认不提示」，README 路线表 v0.6 行写明规格提醒后来在 0.7.3 改为默认开启。
4) 手册 v0.7.3 能力行仍含「记忆闸门优先于规格闸门」；spec 命令说明写明 block 摘录后再改放行的前提。模块规格设计稿写明二次放行与已读只认成功 Read。
5) Wiki 另仓：Home 的当前版本和更新记录要写到 0.7.4，须单独推 pmem.wiki。只推 origin/master 不会更新 Wiki。

入口：README 效果栏；docs/pmem-guide.html；docs/architecture.md。
