---
id: 01M59TCMS5CS2QYTKRA6WA1041
module: infra.Model
entity: Entry
kind: correction
status: active
supersedes:
- 01M52J3HG3FQCANQ1G9FGZP51E
anchors:
- src/pmem/core/entry.py#to_markdown
- src/pmem/core/entry.py#from_markdown
revision: git:a92221a
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 字段丢失
- 新旧版本混用
- 未知字段
- 向前兼容
source:
  conversation: 6b540a20-0fb2-45fe-9ffb-9ce5b287b508
---
更正：记忆文件重写（confirm、归档/恢复、format、anchors、migrate）原先只写已知字段，较新版本写入的 YAML 头字段会被旧版本悄悄抹掉并随提交进入版本库。
现在 Entry.extra 收下所有不在 KNOWN_KEYS 里的顶层字段，重写时原样写回（在已知字段之后）。以后加新字段时要同步加进 KNOWN_KEYS，否则会被当成未知字段重复写。
局限：只保留顶层字段，source、archived 这类嵌套字典里的未知子键仍会丢；带 draft_id 覆盖草稿时是新建 Entry，不继承旧文件的未知字段；本次之前的 pmem 版本仍会丢字段，团队需升级。

仍有效：YAML 头可选字段 archived: {on, from, by}，只在归档时写入，恢复和接受时删除；
status_on(日期) 对那天之后才归档的按原状态算。
容错：archived 不是字典时忽略；
from 不是 active/seed/draft 时当作没有记录。
注意：YAML 1.1 会把不加引号的 on/off/yes/no 解析成布尔，手写 archived: {on: ...} 会变成 True 键而读不到日期；pmem 自己写出的文件会加引号。
