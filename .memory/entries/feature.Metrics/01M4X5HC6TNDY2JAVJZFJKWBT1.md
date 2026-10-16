---
id: 01M4X5HC6TNDY2JAVJZFJKWBT1
module: feature.Metrics
entity: Citation
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/metrics/cite.py#judge
revision: git:c079bc9
author: 1002378395@qq.com
note_date: '2026-10-14'
---
判断“检索返回的记忆是否被 Agent 采用”时，语义相似度不可用，只用字面重合（中文 4 字片段 + 标识符的覆盖比例），阈值 0.15。

证据：用 6 条记忆对 5 个无关项目的对话记录和 1 个真实使用过记忆的对话校准。
bge-small-zh 按段落切块后取最大余弦，无关对话也有 0.69–0.81，与真实使用的 0.74–0.81 重叠，且长对话要算约 80 秒；
字面重合在无关对话里最高 0.109，真实使用的对话为 0.139–0.347。

影响：pmem report 的“记忆被采用”是保守下限，Agent 完全换说法复述的情况不计入；
引用在 report 时离线计算并缓存到 cites.json，不放进 stop Hook，避免拖慢每轮结束。
复核阈值用 scripts/calibrate_cite.py。
