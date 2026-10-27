---
id: 01M5CR89R9NSQCCV7TA4VW2B8T
module: infra.Model
entity: Entry
kind: correction
status: active
supersedes:
- 01M59TCMS5CS2QYTKRA6WA1041
anchors:
- src/pmem/core/entry.py#Entry.from_markdown
- src/pmem/service/record.py#_record
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 覆盖草稿现在也保留未知字段；记忆文件头写坏或缺必填项时报 ValueError
verify: uv run pytest tests/test_service.py -k unknown_front_matter tests/core
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:21.736+08:00'
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
更正：旧记忆的局限“带 draft_id 覆盖草稿时是新建 Entry，不继承旧文件的未知字段”已不成立，覆盖时把旧文件的 extra 原样带上。
另有一处新增：Entry.from_markdown 遇到 YAML 写错、头不是键值对、缺 id/module/entity/kind/note_date、source 不是字典时一律抛 ValueError（存储层转成 storage_read），原先会抹 KeyError/TypeError 让 confirm、归档整批失败。
仍有效：Entry.extra 收下所有不在 KNOWN_KEYS 里的顶层字段，重写时原样写回（在已知字段之后）；
以后加新字段要同步加进 KNOWN_KEYS。
只保留顶层字段，source、archived 这类嵌套字典里的未知子键仍会丢。
YAML 头可选字段 archived: {on, from, by} 只在归档时写入，恢复和接受时删除；
status_on(日期) 对那天之后才归档的按原状态算；
archived 不是字典时忽略，from 不是 active/seed/draft 时当作没有记录。
注意：YAML 1.1 会把不加引号的 on/off/yes/no 解析成布尔，手写 archived: {on: ...} 会读不到日期；pmem 自己写出的文件会加引号。
