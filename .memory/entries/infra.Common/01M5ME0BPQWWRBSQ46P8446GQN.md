---
id: 01M5ME0BPQWWRBSQ46P8446GQN
module: infra.Common
entity: Docs
kind: conclusion
status: active
supersedes: []
anchors:
- README.md
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: GitHub Wiki 是独立仓库，推 master 不会更新 Wiki 首页
verify: git remote of pmem.wiki.git；推主仓库后 wiki 仍是上一版本，另 clone 并 push 后 Wiki Home 才变
applies: 用户要求更新 GitHub 首页或 Wiki 时
aliases:
- Wiki首页
- pmem.wiki
source:
  conversation: 70760b3a-0dd4-4cc7-a429-f7c5252b5a05
---
确认的坑：GitHub Wiki 不在主仓库里。
仓库首页是 README.md；
产品手册是 GitHub Pages（homepageUrl 指向 docs/pmem-guide.html，源是 master 的 /docs）；
Wiki 是独立仓库 https://github.com/mry-ship/pmem.wiki.git。
推 origin/master 只更新 README 和 Pages，Wiki Home 仍停在旧版。要改 Wiki 须另 clone 该仓库、改 Home/快速接入/日常使用/更新记录后单独 push。
