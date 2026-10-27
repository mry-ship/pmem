---
id: 01M5ME04FSNCWZ5ZNCPVRSV1VK
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes: []
anchors:
- README.md
- docs/pmem-guide.html
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: GitHub 首页、手册和 Wiki 都要写明 complete 是补全入口、正文写到九成八
verify: 打开 README 快速接入第 4 步、日常使用表、路线 v0.6；手册「看模块现在的完整设计」行；Wiki Home 「模块规格可拿走」一条，都能看到
  pmem spec complete 和九成八
applies: 发规格相关版本，或改补全入口、验收口径时
aliases:
- GitHub首页
- GitHub Pages
- GitHub Wiki
- 使用手册
source:
  conversation: 70760b3a-0dd4-4cc7-a429-f7c5252b5a05
---
需求来源：用户要求「提交git、提交github、更新github首页」。
必须保持：仓库首页 README、GitHub Pages 手册 docs/pmem-guide.html、GitHub Wiki（Home、快速接入、日常使用、更新记录）都写明补全模块规格的入口是 pmem spec complete（fill 是旧名），正文按已实现对外契约写到九成八。
README 结构不改：只改快速接入第 4 步、日常使用「补全模块规格」行、「看模块现在是什么样」行、路线 v0.6 一行。
入口：README.md；手册 https://mry-ship.github.io/pmem/pmem-guide.html；Wiki https://github.com/mry-ship/pmem/wiki。
