---
id: 01M83KJNAGC8K2VQ18JXEVQPFF
module: feature.Gate
entity: SpecRead
kind: feature
status: active
supersedes:
- 01M83HMRYNTQCKH8EA8P4BCSVQ
anchors:
- src/pmem/hooks/guard.py#_guard_spec
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 规格闸门文案写明摘录后再改可放行
verify: uv run pytest tests/hooks/test_gate.py -q -k spec_read
source:
  kind: code
---
需求来源：拦截文案仍写「读完再重试」，与二次放行行为及用户文档口径不一致。

必须保持：规格闸门 deny 文案为「pmem：修改 <路径>（<模块>）之前，请先阅读相关规格：<文件列表>。
请阅读后重试；
若环境看不到 Read，摘录给过后再改会放行。」后面附摘录。
行为不变：本对话尚未记到任何成功读取时，摘录给过后再改放行；
已有成功读取则未读完继续拦。
手册接入说明与命令表、Gate 程序设计原文与此一致。

入口：src/pmem/hooks/guard.py#_guard_spec。
