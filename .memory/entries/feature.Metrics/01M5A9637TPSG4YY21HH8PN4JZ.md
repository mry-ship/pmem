---
id: 01M5A9637TPSG4YY21HH8PN4JZ
module: feature.Metrics
entity: Contradiction
kind: decision
status: active
supersedes:
- 01M59G7EKR8C1RAND6FFXJ3DYY
anchors:
- src/pmem/metrics/health.py#_reviewed_after
- src/pmem/metrics/health.py#_contradictions
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 矛盾
- 冲突
- 健康报告
- health
- 同一天
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定：pmem health 的“疑似互相矛盾的记忆”一节。
判定条件（不变）：同模块同议题、都现行、一条是 conclusion/decision 而另一条是 exclusion/correction、互相没有 supersedes、正文词集合 Jaccard 相似度 ≥ 0.15；
risk 不参与；
最多列 10 对。
阈值依据：本仓库同议题无关的一正一反记忆相似度最高 0.11，TileMatch 的真矛盾是 0.18；没有用否定词判断正负（中文里到处都有，误报太多）。

“负责人已看过”的判断改了：较早那条的核对日期晚于较晚那条的写入日期就不再提示；同一天时比精确时刻：核对时刻（verified_at，毫秒）不早于较晚那条 ULID 里的生成时间才算看过。
原先同一天一律算看过：上午核对了旧记忆、下午有人写下与它矛盾的新记忆，这一对会被屏蔽。如果只是改成严格晚于，当天 confirm 永远消不掉提示。
老版本核对的记忆没有 verified_at，同一天的会重新出现一次，再 confirm 一次即可。
处理办法不变：确实冲突就写 correction 替代；只是互补就 pmem confirm 较早那条。
风险：“选定方案 + 排除另一方向”用词很像时会误报，处理一次后不再出现。
