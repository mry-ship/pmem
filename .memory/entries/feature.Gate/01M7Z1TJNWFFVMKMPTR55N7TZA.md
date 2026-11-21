---
id: 01M7Z1TJNWFFVMKMPTR55N7TZA
module: feature.Gate
entity: SpecRead
kind: exclusion
status: active
supersedes: []
anchors:
- src/pmem/hooks/guard.py#_note_spec_reads
- src/pmem/hooks/guard.py#_harvest_spec_reads
revision: git:9db856d
author: yanghu
note_date: '2026-11-21'
summary: 排除：把 Grep 搜索词、改规格文件或打开 harness 当成已读规格
verify: uv run pytest tests/hooks/test_gate.py -q -k 'grep_pattern or writing_the_spec
  or pre_tool_edit'
applies: 判断本对话是否已经读过模块规格时
source:
  conversation: 5500e8d7-007c-460c-b7d7-15a5bb04aee9
---
排除：Grep 的 pattern 是搜索词，里面出现规格路径也不算读过。只有 Glob 的 glob_pattern、glob 或 pattern 才按路径解释。
排除：写或改规格文件本身算已读。
读过只认 Read、Grep、Glob 这类查看工具的 post-tool，以及对话记录里这些工具的调用。
pre-tool 拦截写入时，不要把当前工具参数里的路径记成已读：先改规格再改代码，或同一次写入同时列出规格路径和代码路径，都不能因此放行。
排除：为了改前读规格去把 harness.mode 从 off 改成 hint 或 check。harness 仍默认关，它还会附带常一起改和修复提交；改前读规格是 spec.read_before_edit。
