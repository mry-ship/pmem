---
id: 01M5CEQ7761KCP8GVSQBX9952Q
module: feature.Retrieval
entity: StaleCheck
kind: correction
status: active
supersedes:
- 01M5AA7DVGMZW6HHYKKVEF7Q09
- 01M51WPH43M068SZRPVJNJG2YZ
anchors:
- src/pmem/index/anchors.py#AnchorChecker._baselines
- src/pmem/index/anchors.py#AnchorChecker._symbol_problem
- src/pmem/index/anchors.py#checked_at
- src/pmem/index/anchors.py#AnchorChecker.check
- src/pmem/vcs/git.py#_iso
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 过期判定精确到秒，基准只顺延到记忆写入后的第一次提交
verify: uv run pytest tests/index/test_anchors.py
aliases:
- 需核实
- 过期
- stale
- 基准日
- 核对日期
- 同一天改动漏报
---
更正（现行规则，替代原判定规则与缓存规则两条）：“需核实”由 AnchorChecker 统一判定，检索、memory_graph、读代码摘要、拦截、Wiki、health 共用。

判定：锚点文件已删除标“已不存在”；路径#函数 在当前文件里连名字都找不到标“找不到”。
文件在基准时刻之后改过：Git 下取基准时刻那版文件，比较函数代码块，相同不算过期，不同提示“X 中 函数 在 日期 之后改过”；
旧版有、当前找不到定义（只剩调用或同名变量）提示“X 中找不到 函数”。“类.成员”先找类再找成员。SVN、无历史、两版都取不到代码块时按文件判断。

基准时刻（更正点）：
- 原先按天比较，基准日当天之后的改动一律放过（上午 confirm、下午有人改了函数，仍显示已核对）。
  现在精确到秒：写入取 ULID 时间（与 note_date 不同天时按 note_date 当天结束），核对取 verified_at（只有 verified 时按当天结束）。
- 原先取记忆文件最近一次提交（7 天内）作基准，之后 format、归档、改锚点再提交会把基准一路后推。现在只顺延到写入或核对后 7 天内的第一次提交。
- 只有从没提交过的草稿取现在；
  提交过、核对后没再提交的不顺延。
  曾误把后者当草稿，所有改动被放过（回归测试 test_committed_memory_without_later_commit_is_not_treated_as_draft）。
- 未提交的代码改动按文件修改时间算，不再一律记为今天。
- Windows 上 1970 年附近的时间戳转本地时间抛 OSError；写入日无效（基准为 0）时曾让整批核对被吞掉、当成都没改过。git 参数改用 UTC 且不早于 1970-01-02。

缓存：Git 下结果缓存在 anchors.json，工作区指纹（提交号、日期、.memory/ 外未提交文件的修改时间和大小）变化即作废，单条按 id、写入日、核对日、verified_at、锚点命中，10 分钟过期；
reindex 删除。
进程内缓存超过 512 项清空。

代价：记忆先提交、代码过后单独提交时会误报，核对后 confirm。锚点尽量写到函数。
