---
id: 01M7ZAEF4CZ18MP6J7XATKMC1R
module: feature.Gate
entity: SpecRead
kind: feature
status: active
supersedes:
- 01M7Z1TCXGZJHWC18PW445B793
anchors:
- src/pmem/hooks/guard.py#_note_spec_reads
- src/pmem/hooks/guard.py#_harvest_spec_reads
- src/pmem/hooks/guard.py#read_failed
- src/pmem/hooks/gate.py#_post_tool
revision: git:eabeffc
author: yanghu
note_date: '2026-11-21'
summary: 已读只认成功 Read 打开某一份规格正文
verify: uv run pytest tests/hooks/test_gate.py -q -k 'spec_read or empty_spec or transcript_read
  or glob_ or grep_ or failed_ or is_error or second_write or compact_requires'
applies: spec.read_before_edit 为真且闸门不是 off、本对话未跳过记忆时
aliases:
- 规格已读
- 读过规格
- spec_read
source:
  conversation: c6898741-27d3-42d3-adc6-a12993fd5225
---
需求来源：改前读规格默认开启；已读证据要收紧，列出文件或只匹配一行不算读过正文。
必须保持：程序设计或模块现状已写完（整行空标记，行尾 CR 仍算）时，block 在成功读过之前拦住修改。
读过只认 Read 成功打开某一份规格正文。
post-tool 不能带 failure_type、error_message、顶层 is_error，也不能带 tool_response 或 tool_output 里的 is_error。
对话记录要有同一次 Read，且 tool_result 未标失败；
没有 id、没有结果或结果失败都不算。
Grep、Glob、语义搜索、打开目录不算。写或改规格不算。pre-tool 当前写入路径不算。项目内符号链接仍要读，项目外不读。空骨架、不存在、只写策划或美术不拦。
warn 只拦一次。闸门 off、跳过记忆、read_before_edit 为假不拦。多个模块先拦记忆。还没有任何读取时，摘录给过后再改放行；已经读过则没读完的继续拦。压缩后 spec_read 清空。
规格提醒缺省仍开：与功能记录同一份模块名单；无需记录、免记录文件、已写过四份之一的不提醒；缺美术设计就补上；文案以 [pmem] 开头。
入口：改代码前的 pre-tool 闸门。
