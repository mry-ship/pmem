---
id: 01M5EJQ0DA43DG5P3RBYEWQRK1
module: feature.Retrieval
entity: StaleCheck
kind: conclusion
status: active
supersedes:
- 01M525TV4DF1JDYWBBRR6TT6X8
- 01M5CEQ7761KCP8GVSQBX9952Q
anchors:
- src/pmem/index/anchors.py#AnchorChecker._worktree_state
- src/pmem/index/anchors.py#AnchorChecker._baselines
- src/pmem/index/anchors.py#AnchorChecker._symbol_problem
- src/pmem/index/anchors.py#checked_at
- src/pmem/index/anchors.py#AnchorChecker.check
- src/pmem/vcs/git.py#_iso
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 过期核对统一由 AnchorChecker 判定：基准精确到秒且不后移，缓存只在 Git 上启用
verify: uv run pytest tests/index/test_anchors.py
aliases:
- 过期
- 需核实
- stale
---
结论：“需核实”（过期、stale）由 AnchorChecker 统一判定，检索、memory_graph、读代码摘要、拦截、Wiki、health 共用。现行判定、基准时刻和缓存规则：
判定：锚点文件已删除标“已不存在”；
路径#函数 在当前文件里连名字都找不到标“找不到”。
文件在基准时刻之后改过时，Git 下取基准时刻那版文件比较函数代码块，相同不算过期，不同提示“X 中 函数 在 日期 之后改过”；
旧版有、当前只剩调用或同名变量提示“找不到”。
“类.成员”先找类再找成员。
SVN、无历史、两版都取不到代码块时按文件判断。
基准时刻：精确到秒（曾按天比较，同一天稍后的改动被放过）。
写入取 ULID 时间（与 note_date 不同天时按 note_date 当天结束），核对取 verified_at（只有 verified 时按当天结束）。
只顺延到写入或核对后 7 天内的第一次提交（曾取最近一次提交，格式化、归档再提交会把基准一路后推）。
从没提交过的草稿取现在；
提交过、核对后没再提交的不顺延（回归测试 test_committed_memory_without_later_commit_is_not_treated_as_draft）。
未提交的代码改动按文件修改时间算。
Windows 上 1970 年附近时间戳转本地时间抛 OSError，基准为 0 曾让整批核对被吞掉；
git 参数用 UTC 且不早于 1970-01-02。
缓存：只在 cheap_dirty_files 为 True 的版本库（目前只有 Git）启用 anchors.json 跨进程缓存，工作区指纹（提交号、日期、.memory/ 外未提交文件的修改时间和大小）变化即作废，单条 10 分钟过期，reindex 删除；
进程内缓存超过 512 项清空。
SVN 不算指纹：全量 svn status 在 TileMatch 一次约 3.9 秒，读代码摘要曾从 0.3 秒变 3.4 秒。
风险：新增版本库适配时 dirty_files 快才把 cheap_dirty_files 设 True。记忆先提交、代码过后单独提交时会误报，核对后 confirm；锚点尽量写到函数。合并自 2 条记忆。
