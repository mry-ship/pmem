---
id: 01M6RDZCZ1WH9SNTGBJ06173G2
module: infra.Model
entity: EntryLine
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/core/entry.py#from_markdown
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: 从磁盘读回的议题、日期和锚点收成一行
verify: uv run pytest tests/core/test_entry.py::test_hand_edited_newlines_collapse_to_one_line
  -q
applies: 读取手改过的记忆 markdown；写入 API 仍另有单行校验
aliases:
- 读回换行
- 议题换行
---
需求来源：写入 API 会拒绝多行议题并压平 summary，但从磁盘 from_markdown 读回时，entity、module、note_date、kind 以及 anchors 等列表仍是原始字符串，换行能把后来的摘要拆开。

必须保持：from_markdown 把 module、entity、kind、note_date 收成一行；
anchors、supersedes、aliases 的每一项也收成一行，收成空串的丢掉。
YAML 写错、头不是键值对、缺必填项仍然报 ValueError。
未知头字段仍原样保留。
kind 收成一行之后若不在类型表里，仍拒绝这条记忆。

入口：Entry.from_markdown、_line。
