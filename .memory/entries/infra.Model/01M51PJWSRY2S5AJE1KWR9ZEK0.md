---
id: 01M51PJWSRY2S5AJE1KWR9ZEK0
module: infra.Model
entity: WikiDefaults
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/config.py
revision: git:9510a42
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- wiki.auto
- wiki.dir
verified: '2026-10-19'
---
决定：配置新增 wiki.auto（默认 true）和 wiki.dir（默认 .memory/wiki）。

已接入的项目升级后不用改配置：读取时与默认值合并，写入或确认记忆后就会开始自动生成 Wiki。
如果项目根目录的 .gitignore 已经忽略了这个目录，或者目录里有 Wiki 自带的 .gitignore，就不会出现在提交里。
注意：如果 wiki.dir 指向已存在的目录，不会自动放 .gitignore，需要自己决定是否提交。
