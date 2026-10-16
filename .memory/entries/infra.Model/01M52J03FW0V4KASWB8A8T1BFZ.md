---
id: 01M52J03FW0V4KASWB8A8T1BFZ
module: infra.Model
entity: Entry
kind: decision
status: active
supersedes:
- 01M52HSKZDA5C2BNRKKZ0CHVVA
anchors:
- src/pmem/core/entry.py#status_on
- src/pmem/core/entry.py#to_markdown
- src/pmem/core/entry.py#from_markdown
revision: git:2f0f6f6
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 归档日期
- archived_on
- 记忆文件格式
---
决定：记忆文件的 YAML 头新增可选字段 archived: {on: YYYY-MM-DD, from: 归档前状态}，对应 Entry.archived_on / archived_from，只在归档时写入、恢复时删除；
Entry.status_on(日期) 给出某天的状态（那天之后才归档的按原状态）。

解析容错：archived 不是字典时忽略；from 不是 active/seed/draft 时当作没有记录（恢复为 active）。否则手改出的非法值会在恢复时写进 status，之后这个文件每次解析都报错。

原因：恢复要回到原状态（退回的种子仍是种子），as_of 回看要知道归档发生在哪天。放在一个嵌套键里，不影响已有字段的解析。

风险：旧版 pmem 读到带 archived 的文件会忽略该字段（不报错），但它自己重写文件（如 confirm、format）时会把字段丢掉，团队里版本不一致时可能丢失归档日期。
