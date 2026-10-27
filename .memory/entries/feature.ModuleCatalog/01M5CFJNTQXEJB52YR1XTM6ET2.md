---
id: 01M5CFJNTQXEJB52YR1XTM6ET2
module: feature.ModuleCatalog
entity: Split
kind: decision
status: active
supersedes:
- 01M59G7DJEDKRBM992F3QX5706
anchors:
- src/pmem/catalog/migrate.py#plan_split
- src/pmem/catalog/sync.py#plan_sync
- src/pmem/catalog/sync.py#apply_plan
- src/pmem/scan/lite.py#file_heat_windows
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: migrate split 与 sync 默认预览；横跨无关模块的记忆留在原模块且不列出
aliases:
- 拆分模块
- split
- sync
- 目录同步
- 新目录
- 模块同步
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:19.568+08:00'
---
决定：pmem migrate split 和 pmem sync 都默认只预览，--apply 才写 modules.yaml（split 还会搬记忆文件）。
split A --to B=路径[,路径]（可多次；--by entity 按议题拆；--assign id=模块 指定去向）：B 可以是新模块或已有模块，不能拆给 A 自己，同一路径或议题不能分给两个模块；
按路径拆时用新目录逐个代码文件核对，抢到别的模块的文件就拒绝。
记忆分配：--assign 优先；
按议题拆看 entity；
按路径拆看关联代码在新目录里归谁，只落在一个目标就搬过去，落在 A 或其他模块就留下。
更正：只有关联代码涉及某个拆出的目标时才列出；
只横跨 A 和无关模块的，留在 A 但不列出。
没写关联代码的跟随同议题其他记忆的一致去向，不一致就留在 A 并列出。
按议题拆时议题名拼错会报错。
sync：未覆盖代码按第一个没有已覆盖文件的上级目录分组；
≥3 个文件且 180 天内有改动的成为新模块，否则成为冷候选；
冷候选有记忆或改动 ≥5 次时转正；
近 90 天没改动也没记忆的只提示；只追加。
file_heat_windows 读一次历史算多个时间窗。
风险：重写 modules.yaml 只保留文件开头的注释（预览提示丢失行数）。
