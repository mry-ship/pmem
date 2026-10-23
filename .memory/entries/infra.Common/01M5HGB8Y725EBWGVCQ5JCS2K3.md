---
id: 01M5HGB8Y725EBWGVCQ5JCS2K3
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes: []
anchors:
- README.md
revision: git:b6bdaf8
author: 1002378395@qq.com
note_date: '2026-10-22'
summary: README 按“问题→工作原理→接入→日常→维护→效果→限制→文档→路线”组织，效果五张表保持分开
verify: 打开 README：顶部有版本徽章和锚点导航，效果一节五张表分开，已知限制里有 Wiki 与嵌入两条
applies: 改 README 结构或发新版本时
verified: '2026-10-23'
verified_at: '2026-10-23T21:03:55.369+08:00'
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：用户 2026-10-22 要求“主页用专业的角度再改造一下”。
必须保持的结构：README 顺序为 解决什么问题（含四个特性表和关键数字一行）→ 工作原理（流程图 + 时机/自动行为表 + 6 条设计要点）→ 快速接入（含环境要求和升级）→ 日常使用（只放对 AI 说的话）→ 维护（按模块目录、记忆、定期体检三张表分组）→ 效果 → 已知限制（折叠）→ 文档索引表 → 路线表（版本、内容、状态）。
必须保持的内容约束：关键数字一行只放本仓库实测数（检索中位 7 毫秒、真实题前三 90%、一次修 bug 3000～5000 token、记忆丢失 0），上一代的下降比例只出现在“能省多少”并写明口径；
效果里优缺点、速度、token、能省多少、检索有多准五张表分开，v0.5 对 v0.3 放折叠块；
已知限制保留 Wiki 不能写出目录、嵌入地址限制两条，并含自动登记只追加的说明；
徽章里的版本号随发版更新。
入口：README.md。
