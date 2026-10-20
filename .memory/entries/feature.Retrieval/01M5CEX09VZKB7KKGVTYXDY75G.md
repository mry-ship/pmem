---
id: 01M5CEX09VZKB7KKGVTYXDY75G
module: feature.Retrieval
entity: Verify
kind: correction
status: active
supersedes:
- 01M4ZNZZ81SDRC5DT7CNYAJ36H
- 01M51PJKCPP62KWN7YTWYRD2KJ
anchors:
- src/pmem/index/anchors.py#AnchorChecker._baselines
- src/pmem/index/store.py#SYNONYM_WEIGHT
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 过期核对须扣除记忆自身修复提交；基准改为写入后首次提交
verify: uv run pytest tests/index/test_anchors.py -k baseline
aliases:
- 过期
- 失效
- 核对
- stale
---
更正（合并 Verify 议题两条旧记忆，基准规则按 2026-10-20 的现行规则改写）：

结论（仍成立）：按当前代码核对记忆是否过期时，必须扣除“记忆自己那次修复”的提交，否则误报很多。
TileMatch 真实历史回放：按提交做基准后，需核实的记忆从 75 条降到 49 条，去掉的 26 条约 20 条确实是记忆对应的修复提交
（如大拇指规则记忆写于 10-13，r41082 于 10-15“修改大拇指逻辑”；倒计时接关写于 10-10，r41015 于 10-12 调整）。
误去掉的约 5 条都是只排查、没修复的记忆，7 天内别人的无关提交被当成了“修复”；真正的风险是把记忆攒几天、夹在无关提交里一起提交，期间别人对关联代码的改动会被漏报。

决定（仍成立）：判定抽成独立的 AnchorChecker（src/pmem/index/anchors.py），检索、memory_graph、读代码摘要、改代码拦截、Wiki、health 共用；
Hook 进程不加载索引，所以检查器只依赖项目根目录和版本库。原因：以前只有 search_memory 标 stale，摘要和 Wiki 看不出过期，Agent 可能照着过期的坑行事。
代价：每次摘要或拦截要跑一次 git log 加一次 git diff（SVN 是 info 加 status），本仓库百毫秒以内。

更正点（基准规则）：原文“基准日 = max(写入日, verified)；记忆在写入后 7 天内提交（草稿按今天）就取提交日”已不准确。
现在精确到秒，且只顺延到写入或核对之后的第一次提交；从没提交过的草稿取现在；记忆文件提交过、之后没再提交的不顺延。完整规则见 feature.Retrieval / StaleCheck 的现行更正。

其他（仍成立）：没有版本库时退回看 mtime，误报多（TileMatch 837 个脚本里 102 个 mtime 是当天），有版本库就必须用版本库时间。
同义词：TileMatch 里“闪退”0 条、“崩溃”28 条；
在 modules.yaml 加 synonyms: [闪退, 崩溃, crash] 后，搜“拼图 闪退”前 2 条就是提到崩溃的记忆；
扩展词按 0.8 权重计入，条目的 aliases 只并入本条索引、不参与扩展。
