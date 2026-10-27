---
id: 01M5CFK63ZFBHGGNF0ZBAXCS1Y
module: infra.Model
entity: Entry
kind: correction
status: active
supersedes:
- 01M5A966BYC9VJRG07ZT8QNRKW
anchors:
- src/pmem/core/entry.py#Entry
- src/pmem/service/status.py#confirm
- src/pmem/index/anchors.py#checked_at
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: verified_at 也用于锚点过期核对，精确到秒比较；版本库接口传 Unix 秒
aliases:
- 核对时间
- verified
- 确认记忆
- confirm
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:19.568+08:00'
---
更正：旧记忆说“过期核对照旧只用日期，verified_at 只给 health 判断”“锚点核对把 checked_date 当日期传给 git/svn”，都已不对。
现在锚点核对按精确时刻判断：核对时刻取 verified_at（没有时取 verified 当天结束），与写入时刻取较晚者；
版本库接口 changed_since / file_before 收的是 Unix 秒，核对缓存的键也含 verified_at。
仍有效：记忆 YAML 头的可选字段 verified_at（带时区 ISO，精确到毫秒）由 confirm 与 verified 一起写入，只在有 verified 时输出，已在 KNOWN_KEYS；
verified 仍是日期，检索排序、Wiki 用它；
health 用 verified_at 判断“同一天里核对在新记忆写下之前还是之后”。
旧版本把 verified_at 当未知字段原样保留。
风险：同一天多人核对同一条，合并冲突从一行变两行，保留较新的一组即可。
