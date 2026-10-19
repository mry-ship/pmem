---
id: 01M51VN6PNEY4WZXDSR558EPB3
module: feature.Storage
entity: DraftId
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/storage/files.py#find_path
- src/pmem/storage/files.py#_check_draft
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- draft_id 校验
- 路径穿越
- path traversal
- 通配符
verified: '2026-10-19'
---
决定：按 id 找记忆文件（find_path，供 draft_id 覆盖、confirm_memory、get 使用）只接受合法的 ULID（26 位 Crockford Base32 大写）；
不合法时直接当作不存在。
draft_id 不合法时，写入报错“不是有效的记忆 id（26 位 ULID）”。

原因：id 原先直接拼进 glob 匹配模式（entries/*/<id>.md），传入 ../、* 或小写 id 时可能匹配到记忆目录以外的文件，或者一个通配符匹配到任意一条记忆。
由于还要能解析成记忆、作者一致、未提交才会覆盖，实际风险很小，但边界应当在入口处就挡住。

影响：所有真实记忆和导入记忆的 id 都是 new_ulid 生成的，不受影响；测试里手写的 id 也要用合法字符（不能含 I、L、O、U，必须大写）。
