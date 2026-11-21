---
id: 01M7ZAEQNK14V7M80VFWNES7XQ
module: feature.Gate
entity: SpecRead
kind: exclusion
status: active
supersedes:
- 01M7Z1TJNWFFVMKMPTR55N7TZA
anchors:
- src/pmem/hooks/guard.py#_note_spec_reads
- src/pmem/hooks/guard.py#_successful_read_args
revision: git:eabeffc
author: yanghu
note_date: '2026-11-21'
summary: 排除：Glob、Grep、失败 Read 或打开目录当成已读规格
verify: uv run pytest tests/hooks/test_gate.py -q -k 'grep_ or glob_ or failed_ or
  is_error or writing_the_spec or pre_tool_edit'
applies: 判断本对话是否已经读过模块规格时
source:
  conversation: c6898741-27d3-42d3-adc6-a12993fd5225
---
排除：把 Grep、Glob、语义搜索、打开规格目录、失败或尚未返回的 Read 当成已读规格。
Grep 的搜索词、Glob 的模式、目录路径都不按读过正文解释。对话记录里只有 tool_use、没有未标失败的 tool_result，也不算。
排除：写或改规格文件本身算已读。
pre-tool 拦截写入时，不要把当前工具参数里的路径记成已读：先改规格再改代码，或同一次写入同时列出规格路径和代码路径，都不能因此放行。
排除：为了改前读规格去把 harness.mode 从 off 改成 hint 或 check。harness 仍默认关，它还会附带常一起改和修复提交；改前读规格是 spec.read_before_edit。
