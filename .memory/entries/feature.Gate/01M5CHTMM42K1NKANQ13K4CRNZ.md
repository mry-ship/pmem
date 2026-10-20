---
id: 01M5CHTMM42K1NKANQ13K4CRNZ
module: feature.Gate
entity: DraftInjection
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/mcp.py#_inject
- src/pmem/hooks/mcp.py#draft_key
- src/pmem/hooks/agents.py#normalize
- src/pmem/hooks/guard.py#_guard
- src/pmem/hooks/gate.py#on_compact
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 注入只回传新增字段（Cursor）；同议题功能记录不覆盖教训；方括号路径照样拦截
verify: uv run pytest tests/hooks -k "only_added or until_module_searched or feature_record_does_not_overwrite
  or brackets or compaction_is_logged"
applies: Cursor/Claude/Codex 通过 Hook 调用 search_memory、record_memory；终端 pmem 命令不注入
aliases:
- 草稿覆盖
- draft_id 注入
- updated_input 合并
- 乱码回传
- 压缩事件
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
需求来源：用户要求先补测试再修审查确认的问题，并“做有效性真实验证”；验证检索效果时发现中文 MCP 检索约六成拿乱码查询词在搜。
必须保持：
- 对 Cursor，preToolUse 的 updated_input 只放 Hook 新增的字段（source_conversation、draft_id、anchors），不回传 Agent 原参数。
  Cursor 按字段合并；
  Hook 读到的参数在中文 Windows 上可能已被转码损坏，回传会覆盖掉 Agent 的正确参数。
- 对 Claude Code、Codex，updatedInput 整体替换原参数，必须回传完整参数加新增字段（normalize 给这两家打 replaces_input 标记）。
- Agent 自己填了 anchors 时不回传 anchors（Cursor 保留原值）。
- 草稿按“模块＋议题＋层”登记，feature/plan 一层、教训一层，功能记录不会拿到教训的草稿 id；教训一层仍用旧键名。写入返回带 kind，拿不到时退回看调用参数。
- 编辑工具给的路径一律按字面检查，app/[id]/page.tsx 这类带方括号的文件照样拦截；终端命令目标只在字面路径不存在时才当通配符展开。
- 上下文压缩时（on_compact）在清空去重记录后记一条 compact 事件，供收益报告切分重复率。
入口：hooks/mcp.py 的 _inject、draft_key；hooks/agents.py 的 normalize；hooks/guard.py 的 _guard；hooks/gate.py 的 on_compact。
