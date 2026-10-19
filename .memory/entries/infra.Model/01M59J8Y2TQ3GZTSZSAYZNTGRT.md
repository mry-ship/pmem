---
id: 01M59J8Y2TQ3GZTSZSAYZNTGRT
module: infra.Model
entity: Constants
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/core/entry.py#KIND_LABELS
- src/pmem/core/entry.py#VISIBLE_STATUSES
- src/pmem/core/entry.py#REPLACING_STATUSES
revision: git:df9b06c
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 常量重复
- 类型中文名
- 可见状态
- 扩展 kind
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：跨模块共用的记忆常量集中到 core/entry.py：
- KIND_LABELS（类型中文名）
- VISIBLE_STATUSES（检索可见状态）
- REPLACING_STATUSES（哪些状态的记忆算“已替代旧记忆”）
检索、图谱、Wiki、健康报告、CLI 都从这里导入。原因：原先各自复制一份，新增 kind 或状态时只改一处就会出现“检索看得见、Wiki 不显示”这类不一致。扩展 kind/status 时只改这一处，再跑全量测试。
尚未收归的重复常量（MIN_SEARCHES_FOR_IDLE、通配符判断、热度统计、git log 解析）已列入 GitHub issue。
