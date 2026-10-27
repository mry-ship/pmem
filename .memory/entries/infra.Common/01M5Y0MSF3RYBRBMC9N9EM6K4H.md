---
id: 01M5Y0MSF3RYBRBMC9N9EM6K4H
module: infra.Common
entity: GapAudit
kind: conclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/memories.py#memory_lines
- src/pmem/hooks/shell.py
- README.md
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: v0.6 全库体检：闸门提示注入与终端写目标识别仍是主风险；记忆库有过时规划与待核对债
verify: pmem doctor；pmem health；对照 01M5CW5XMYVMYF3M4QA28BMAG2 与 memory_lines 是否仍原样注入标题
applies: 排查漏补缺优先级或复盘 0.6 健康度时
aliases:
- 漏洞
- 查漏补缺
- 缺口分析
- 全库体检
source:
  conversation: 4068463b-7fe6-4bd0-9bad-7c80998fc889
---
现象：2026-10-27 对 pmem 0.6.0 做全项目查漏补缺（doctor + health + 风险记忆 + 规格目录 + 代码对照），先分析不改代码。
结论分四层：
1) 安全/闸门类（仍开放）：记忆标题注入 Agent（01M5CW5XMYVMYF3M4QA28BMAG2）未把摘要标成资料；
   终端写目标认不出时只能事后提醒；
   Hook 出错默认放行；
   编码 PowerShell / 变量路径 / foreach 模块名仍绕过事前拦截。
   闸门不是沙箱。
2) 记忆库债：约 29 条需核实；Docs/Config 议题可合并；Hierarchy、RebuildSpec、旧类型安全 plan 文案仍写“尚未实现”但功能已落地，易误导。doctor 报 3 条未提交记忆、2 个议题≥5 条。
3) 规格：14 模块都有目录；feature.Spec 标首稿未完成；多数模块策划仍留空（设计允许）。
4) 产品路线：下一正式缺口是 v0.7 类型安全（Issue #15）；团队汇总/中心服务长期搁置。Claude/Codex 未真实会话验收仍是已知限制。
影响：优先处理注入标注与过时 plan 收口，其余属维护债与路线项，不是现网崩溃类 bug。
