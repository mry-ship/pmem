---
id: 01M6QWTTTVB7PJ5V1X152QVPGJ
module: feature.ModuleCatalog
entity: Loading
kind: feature
status: active
supersedes: []
anchors:
- .memory/modules.yaml
revision: git:ec9df30
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 成形文件从 Common 兜底挂到对应模块；biweekly 挂 Metrics
verify: module_for_path 对上述路径指向正确模块；overlap=0
applies: 改本仓库 modules.yaml 路径归属时
---
需求来源：排查路径挂靠后，把仍落在 infra.Common 的成形文件改挂到所属模块。
必须保持：schema→infra.Model；
autosync/codefiles 与 test_autosync/test_module_hierarchy→ModuleCatalog；
seen→feature.Gate；
integrations/doctor_console 测试→Onboarding；
pmem-biweekly-health.ps1→Metrics；
Common 仍兜底 src/pmem/** 与 tests/**，并显式保留 main/brief/winproc 与横切测试。
同等具体度重叠仍报错。
