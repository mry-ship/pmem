---
id: 01M6QWT5NCH8X2XDBKDQNR370N
module: feature.Metrics
entity: Health
kind: feature
status: active
supersedes: []
anchors:
- scripts/pmem-biweekly-health.ps1
- README.md
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 双周 health 脚本失败也会气球提示，并写入 README
verify: README 定期体检含 pmem-biweekly-health；脚本 catch 调 Show-Balloon
applies: Windows 上用脚本跑 pmem health 时
---
需求来源：巡检脚本未文档化，失败时只抛异常无通知。
必须保持：scripts/pmem-biweekly-health.ps1 成功/有问题/失败都会气球提示（无托盘环境跳过）；
有问题写 .memory/cache/health-action-needed.txt；
不注册计划任务，双周调度由用户自配。
入口：README「定期体检」表；本机可直接运行该脚本。
