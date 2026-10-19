---
id: 01M5A966BYC9VJRG07ZT8QNRKW
module: infra.Model
entity: Entry
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/entry.py#Entry
- src/pmem/service/status.py#confirm
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 核对时间
- verified
- 确认记忆
- confirm
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定：记忆文件 YAML 头新增可选字段 verified_at（带时区的 ISO 时间，精确到毫秒），由 confirm 和 verified 一起写入，只在有 verified 时输出；已加进 KNOWN_KEYS。
verified 仍是日期，过期核对、检索排序、Wiki 都照旧只用日期；verified_at 只给 health 判断“同一天里核对在新记忆写下之前还是之后”。
没有把 verified 直接改成带时间的格式：锚点核对把 checked_date 当日期传给 git/svn，团队里的旧版本也会解析出错。
兼容：旧版本把 verified_at 当未知字段原样保留（Entry.extra）。风险：同一天多人核对同一条，合并冲突从一行变成两行，保留较新的一组即可。
