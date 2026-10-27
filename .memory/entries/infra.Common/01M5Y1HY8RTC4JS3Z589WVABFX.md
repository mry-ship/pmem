---
id: 01M5Y1HY8RTC4JS3Z589WVABFX
module: infra.Common
entity: Docs
kind: conclusion
status: active
supersedes:
- 01M59N3GDHK9VRVH2RYC9GW9S6
- 01M5CFJE42APN2HMMBFCZQV20C
- 01M5CXMNFH04SZN8SNCDMN0331
- 01M5ME0BPQWWRBSQ46P8446GQN
anchors:
- README.md
- docs/pmem-guide.html
- docs/architecture.md
- docs/images/pmem-flow.svg
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 用户文档多份各自维护，加命令易漏；Wiki 另仓；流程图五环节分色
verify: 改 README/手册/架构时对照本条清单；Wiki 改 mry-ship/pmem.wiki
verified: '2026-10-27'
verified_at: '2026-10-27T15:15:50.912+08:00'
---
结论：用户文档分多份各自维护，加命令或发版时容易漏改；docs/** 被闸门忽略，改文档不会触发记忆检查。

须同步的位置：README、docs/pmem-guide.html、docs/architecture.md，以及设计文档 pmem-design.md 第 11 节日常维护命令清单（第 14 节是版本规划，勿改错节）。

流程图 docs/images/pmem-flow.svg 按五环节分色带（接手、①改前查、改代码、②写结论、③提交共享）；手册「日常使用」嵌入同一张图。原因：旧图只有箭头旁小圆点，闸门介入与主动步骤混在一起。

search --brief 在种子记忆类型后标“（种子，待确认）”，与闸门摘要一致。

GitHub Wiki 不在主仓库，源是 https://github.com/mry-ship/pmem.wiki.git。
只推 origin/master 只更新 README 与 Pages，Wiki 须另 clone 后单独 push。

合并自 4 条教训（3 决定 + 1 结论）。
