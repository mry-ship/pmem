---
id: 01M6R9DR77D8KD12TV59ASFZ1M
module: feature.Onboarding
entity: CursorIndex
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/generate/mcp_enable.py#_folder_indexes
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: Cursor 多根工作区首次以非 0 index 打开时，init 只批 project-0 可能对不上
aliases:
- 多根工作区
- project-0
- index 对不上
---
风险：enable_cursor_project_mcp 用 _folder_indexes 决定批准哪些 project-<index>-<名>-pmem，默认只种 {0}，其余 index 靠 known/approved/disabled 里已出现过的记录补。

多根工作区里 pmem 所在文件夹不是第 0 个时，Cursor 用的是 project-N-<名>-pmem（N 不等于 0）；
若该项目从没以这个 index 打开过、known 里也没留痕，init 只批了 project-0，Cursor 实际加载的 project-N 仍未批准，MCP 不认。

为什么没在 init 里修：init 时拿不到 Cursor 给这个工作区分配的真实 index（那是 Cursor 内部状态，随打开顺序变）。
可选缓解：批准时对 0..K 多种几个 index，或在 doctor 里检测 known 里的非 0 index 并提示手动开。
场景窄（多根 + 首开非 0），暂记风险，留待真实多根环境验证。

入口：src/pmem/generate/mcp_enable.py 的 _folder_indexes 与 enable_cursor_project_mcp。
