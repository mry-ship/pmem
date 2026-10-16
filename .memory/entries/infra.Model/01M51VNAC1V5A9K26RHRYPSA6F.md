---
id: 01M51VNAC1V5A9K26RHRYPSA6F
module: infra.Model
entity: Ulid
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/ids.py#is_ulid
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- ULID 校验
- 记忆id格式
---
决定：ULID 的格式定义统一放在 core/ids.py：ULID_PATTERN（26 位 Crockford Base32，大写，不含 I、L、O、U）和 is_ulid()。闸门从工具返回中提取记忆 id、存储层按 id 找文件之前的校验都用它，不要再各写一份正则。is_ulid 只认大写；new_ulid 生成的永远是大写，外部传进来的小写 id 会被拒绝，不会被自动转换。
