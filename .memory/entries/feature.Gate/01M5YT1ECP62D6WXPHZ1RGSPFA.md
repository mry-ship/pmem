---
id: 01M5YT1ECP62D6WXPHZ1RGSPFA
module: feature.Gate
entity: Digest
kind: feature
status: active
supersedes:
- 01M5YS5GQT3PMGGDN91YP90G5R
anchors:
- src/pmem/hooks/memories.py#MemoryView.replaced_ids
- src/pmem/hooks/review.py#_offer_digest
- src/pmem/hooks/guard.py#Guard._guard
revision: git:794463d
author: 1002378395@qq.com
note_date: '2026-10-27'
summary: 摘要和拦截按全库替代关系隐藏记忆；方括号路径仍查字面模块
verify: uv run pytest tests/test_module_hierarchy.py::test_digest_and_gate_hide_child_lesson_superseded_by_parent
  tests/hooks/test_gate.py -k bracket
applies: 读代码附摘要、改代码被拦时列坑，以及终端命令的写入目标含方括号时
source:
  conversation: cbdc341f-d2f9-4242-9798-a49dba225746
---
需求来源：上级模块替代下级记忆后，检索会藏起旧结论，读码摘要和闸门仍把它当现行；另外，引号里的 app/[id]/page.tsx 会被 glob 当成字符类，撞上别的模块里已有的文件时字面路径被放行。
必须保持：读代码摘要、拦截列出的排除项/风险/更正/该文件的功能记录、“现行记忆 N 条”、上级教训和全项目级坑，都要藏起被其他记忆替代的条目。
替代关系只认 Entry.replaces（归档仍算，撤销的合并不算）。
方括号路径即使 glob 撞上了别的文件，仍要按字面路径自己的模块拦截；
只有 * 或 ?、没有方括号时，仍只检查展开结果。
适用：Hook 只加载单个模块目录时；终端命令的目标含 [ 且路径还不存在时。
入口：读代码的 post-tool 摘要，preToolUse 拦截。
