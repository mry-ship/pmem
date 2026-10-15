---
id: 01M4Z9R2MF226TQJSCJJ2YG4YM
module: feature.Gate
entity: DraftOverwrite
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/hooks/gate.py
- src/pmem/storage/files.py
revision: git:b4da2dc
author: 1002378395@qq.com
note_date: '2026-10-15'
---
风险：同一对话里对同一模块写第二条记忆，会覆盖第一条（记忆被覆盖/丢失/前一条没了）。

原因：闸门按“模块”记录本对话写过的记忆 id（state.written 以模块为键），record_memory 的 preToolUse 只要发现 Agent 没带 draft_id，就自动注入这个 id；存储层覆盖前只校验作者、模块、未提交，不校验 entity。所以一次对话处理了同一模块下两个无关议题（例如 Reward 和 Config）时，第二条会覆盖第一条；Agent 即使不想覆盖也没办法通过 MCP 新建（不带或带空 draft_id 都会被注入）。返回里有 overwritten: true，但容易被忽略；草稿未提交，版本库里也没有前一版。

影响范围：只影响 MCP 写入，且前提是 Cursor 接受 preToolUse 的 updated_input（尚未实测确认）；终端 pmem record 不注入。按“同一任务对同一模块只留一条”的规则，单任务对话不受影响。

建议：只在 entity 相同（不分大小写）时自动注入 draft_id，不同 entity 视为新议题新建。
