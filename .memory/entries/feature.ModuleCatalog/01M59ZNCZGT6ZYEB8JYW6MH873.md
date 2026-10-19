---
id: 01M59ZNCZGT6ZYEB8JYW6MH873
module: feature.ModuleCatalog
entity: Migrate
kind: correction
status: active
supersedes:
- 01M52G7EX9CY11D3KM9B0HF9D9
anchors:
- src/pmem/catalog/migrate.py#_plan_merge_unregistered
- src/pmem/catalog/migrate.py#merge_moves
- src/pmem/catalog/migrate.py#plan_merge
- src/pmem/cli/migrate_cmd.py#run_migrate
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 笔误模块名
- 拼错模块名
- 别名污染
- --alias
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
更正：migrate merge A B 中 A 是未登记模块时，原先自动把 A 登记为 B 的别名。未登记模块多半是笔误（economy.Shopp），登记后会一直留在模块目录，以后同样的笔误被悄悄收进来。
现在默认只搬记忆、不登记别名，预览里问“A 是以后还会这样写的叫法吗？”，加 --alias 才登记。
不登记别名时 stray_moves 认不出这些记忆，由 merge_moves 按模块名直接列出要搬的文件。
冷候选模块（sync 扫出的正式名字）仍自动登记别名并并入路径；
A 是已登记模块时加 --alias 报错（并入后 merged_into 本就会转发）。

仍有效：
- rename A B：A 的完整名（及只被 A 用的短名）登记为别名；B 已被占用时拒绝，B 是冷候选时提示改用 merge；指向 A 的 merged_into 和 parent 一并改。
- merge 已登记模块：A 的 paths/aliases/entities/components/variants 并入 B，A 只留 description 和 merged_into:B。
- tidy：模块名解析后不等于自身的记忆搬到正式目录；重复 id 在预览时就拒绝。
- 默认只预览，--apply 才写；先写 modules.yaml 再搬文件，中途失败用 pmem migrate tidy --apply 补完；--root/--apply 写在子命令之后。
风险：不登记别名时，队友本地还在用这个笔误名写入会再新建未登记模块，需要再 merge 一次（pmem health 会列出）。
