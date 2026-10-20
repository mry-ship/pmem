---
id: 01M5AB7K4WGM5SKTM03C00NK2W
module: feature.Curation
entity: CorpusQuality
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/index/graph.py#digest
- src/pmem/service/search.py#_search
- src/pmem/core/quality.py#content_hints
- src/pmem/hooks/reminders.py#on_stop
revision: git:627b54f
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 记忆质量
- 变更日志化
- 采用率低
- token 浪费
- 排除项太少
- 重复返回
- 对话内去重
source:
  conversation: ca2edda2-f749-419e-aa6d-74617201a8d5
---
风险（2026-10-19 全库分析）：记忆库正在变成“变更日志”，最能防错、提速的类型几乎没有；检索输出有大量重复。

证据：
- 现行 147 条中决定 95（65%）、结论 29、更正 14、风险 7、排除项仅 2；96 个议题里 62 个只有 1 条；平均 458 字/条。
- pmem report：返回 312 条只被采用 60 条（19%，字面重合下限）。
- 事件日志：带对话 id 的 82 次检索共返回 357 条，其中 144 条（40%）是同一对话里已经返回过的；服务端不做对话内去重。
- 对话输入 token 中位数约 3400 万，97% 是缓存读；记忆输出只占其中一小部分，省 token 的大头在“少走弯路、少读代码”，不在压缩记忆文本。
- core/quality.py 的变更记录检测被绕过：正文以“决定：”开头就匹配到“决定”这个原因词，提示从不触发。

原因：结束提醒要求“改了哪个模块就为每个模块写一条：为什么这样改、影响范围、风险”，产出多是“现在代码怎么做”的描述；排查中被排除的方向没有专门的写入提示。摘要取正文前 80 字且常是“决定：决定：”重复前缀。

影响：记忆越多，防重复犯错的排除项/风险占比越低。按采用率调排序不可取：采用率只在本机、离线从对话记录算出，会让不同人的检索结果不一致。
