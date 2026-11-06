---
id: 01M6QWTWX2HC3H6FYVDNWA3K44
module: infra.Watchdog
entity: Watchdog
kind: feature
status: active
supersedes: []
anchors:
- .memory/modules.yaml
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 别名改为 Watchdog/看门狗，不再用 Server
verify: resolve_module('Watchdog')→infra.Watchdog；resolve_module('Server') 报未知
applies: 用短名写/查看门狗模块时
---
需求来源：别名 Server 易被当成 MCP server/app，短名会解析到看门狗。
必须保持：短名 Watchdog 与中文「看门狗」仍归一到 infra.Watchdog；不再登记 Server。
入口：.memory/modules.yaml aliases。
