---
id: 01M5Y1JDADTNC5D188CEECDSX4
module: infra.Common
entity: Docs
kind: feature
status: active
supersedes:
- 01M5CWWXMDQF4K2P94ETXZD6R9
- 01M5HGB8Y725EBWGVCQ5JCS2K3
- 01M5ME04FSNCWZ5ZNCPVRSV1VK
anchors:
- README.md
- docs/pmem-guide.html
- docs/architecture.md
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: README 结构与效果五表、Wiki/嵌入限制、complete 九成八须写进主页手册 Wiki
applies: 改 README、手册、架构或发规格相关版本时
---
需求来源：用户要求主页、手册、Wiki 与效果口径保持一致，并写明规格补全入口。

必须保持：
1) README 顺序：问题→工作原理→接入→日常→维护→效果→已知限制→文档→路线。
   效果里优缺点、速度、token、能省多少、检索有多准五张表分开；
   关键数字只用本仓库实测（检索中位约 7 毫秒、真实题前三 90%、一次修 bug 约 3000～5000 token、记忆丢失 0）。
   上一代下降比例只出现在“能省多少”并写明口径。
2) 已知限制与架构须写明：Wiki 不能写出输出目录；
   wiki.dir 指到项目外时 pmem wiki / pmem map 返回 2；
   嵌入地址只接受本机和 https://api.openai.com，其他要本机 PMEM_EMBED_ALLOW_REMOTE=1，OPENAI_API_KEY 只发给官方地址。
3) 补全模块规格入口是 pmem spec complete（fill 旧名），正文按已实现对外契约写到九成八；README、手册、Wiki（Home/快速接入/日常使用/更新记录）都写明。

入口：README.md、docs/pmem-guide.html、docs/architecture.md；Wiki 另仓维护。

合并自 3 条功能记录。
