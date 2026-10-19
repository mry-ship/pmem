---
id: 01M5A0PBG6VWB16K23TWNRFXT0
module: feature.ModuleCatalog
entity: Migrate
kind: correction
status: active
supersedes:
- 01M59ZNCZGT6ZYEB8JYW6MH873
anchors:
- src/pmem/cli/migrate_cmd.py#_print_recovery
- src/pmem/catalog/migrate.py#pending_moves
- src/pmem/catalog/migrate.py#merge_moves
revision: git:4e8ab24
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 迁移失败
- 搬一半
- 恢复
- 收尾
- migrate recovery
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
更正：migrate --apply 搬记忆文件中途失败时，原先一律提示“运行 pmem migrate tidy --apply 搬完剩下的”。
tidy 只认得模块名已改名或并入（merged_into）的记忆；
split、move 分走的记忆原模块仍登记着，未登记模块不加 --alias 合并时旧名也解析不到目标，tidy 都搬不动，照提示做会以为修好了。
现在失败后逐条核对（文件已移走但模块名没改写也算没搬完），tidy 能处理的提示 tidy，其余按目标模块列出可直接运行的 pmem migrate move <id>... --to <模块> --apply，并提醒 modules.yaml 已更新、不要重跑这次迁移。

仍有效：
- merge 未登记模块默认只搬记忆、不登记别名，加 --alias 才登记；冷候选照旧登记别名；已登记模块加 --alias 报错。
- rename A B：A 的完整名（及只被 A 用的短名）登记为别名；B 被占用时拒绝，B 是冷候选时提示改用 merge。
- merge 已登记模块：A 的 paths/aliases/entities/components/variants 并入 B，A 只留 description 和 merged_into:B。
- 默认只预览，--apply 才写；先写 modules.yaml 再搬文件；--root/--apply 写在子命令之后。
风险：不登记别名时，队友还用笔误名写入会再新建未登记模块，需要再 merge（pmem health 会列出）。
