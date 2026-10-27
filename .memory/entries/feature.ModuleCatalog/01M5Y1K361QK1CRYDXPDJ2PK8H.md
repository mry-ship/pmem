---
id: 01M5Y1K361QK1CRYDXPDJ2PK8H
module: feature.ModuleCatalog
entity: Hierarchy
kind: correction
status: active
supersedes:
- 01M5EN0T1CBZXAGDK8MR5JPT97
anchors:
- src/pmem/core/registry.py#is_module_id
- src/pmem/core/registry.py#ModuleRegistry
- src/pmem/index/store.py#search
revision: git:fffa1ba
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 分层已在 v0.5 落地，旧 plan「尚未实现」作废
verify: pmem search --module feature.ModuleCatalog --entity Hierarchy 只见功能记录不见尚未实现的规划
applies: 看到 Hierarchy 旧规划或文案仍写尚未实现时
---
更正：模块分层（最多 4 段、父子由名字表达、查子模块带祖先教训）已在 v0.5 落地，旧规划文案「尚未实现」作废。

现行以功能记录 01M5EP6GSK1QJAX533ZW1Q9QPE 与设计稿 docs/superpowers/specs/2026-10-21-pmem-module-hierarchy-design.md 为准。
不要再按旧 plan 的 applies「尚未实现」推进。
