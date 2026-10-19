---
id: 01M52J3HG3FQCANQ1G9FGZP51E
module: infra.Model
entity: Entry
kind: decision
status: active
supersedes:
- 01M52J03FW0V4KASWB8A8T1BFZ
anchors:
- src/pmem/core/entry.py#status_on
- src/pmem/core/entry.py#to_markdown
- src/pmem/core/entry.py#from_markdown
- src/pmem/service/status.py#change_status
revision: git:3ed5001
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 归档
- 归档人
- archived_by
- 记忆文件格式
verified: '2026-10-19'
---
决定：记忆文件的 YAML 头新增可选字段 archived: {on: YYYY-MM-DD, from: 归档前状态, by: 归档人}，对应 Entry.archived_on / archived_from / archived_by，只在归档时写入（by 取当前用户，即 PMEM_AUTHOR 或版本库用户名），恢复和接受时三者一并删除。
满足 Issue #3“记录归档人和日期”的验收要求。
Entry.status_on(日期) 给出某天的状态：那天之后才归档的按原状态算。

容错：archived 不是字典时忽略；from 不是 active/seed/draft 时当作没有记录（恢复为 active），避免手改出的非法值在恢复时写进 status；没有 by 时当作无归档人。

原因：恢复要回到原状态（退回的种子回到种子）；as_of 回看要知道归档发生在哪天；审计需要知道谁归档的。用一个嵌套键，不影响其他字段的解析。

风险：旧版 pmem 读到带 archived 的文件会忽略该字段，但如果旧版本自己重写文件（如 confirm、format）时这个字段会丢掉；团队里版本不一致时可能丢失归档日期和归档人。
