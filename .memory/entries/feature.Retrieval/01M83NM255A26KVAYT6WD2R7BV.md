---
id: 01M83NM255A26KVAYT6WD2R7BV
module: feature.Retrieval
entity: StaleCheck
kind: conclusion
status: active
supersedes:
- 01M5EJQ0DA43DG5P3RBYEWQRK1
- 01M6QYPV7F7SF5NPM5K3MQM07A
anchors:
- src/pmem/index/anchors.py#AnchorChecker._worktree_state
- src/pmem/index/anchors.py#AnchorChecker._baselines
- src/pmem/index/anchors.py#AnchorChecker._symbol_problem
- src/pmem/index/anchors.py#checked_at
- src/pmem/index/anchors.py#AnchorChecker.check
- src/pmem/vcs/git.py#_iso
- src/pmem/index/anchors.py#_read_anchor
- src/pmem/index/anchors.py#_check
revision: git:8b402c9
author: 1002378395@qq.com
note_date: '2026-11-23'
summary: 需核实由 AnchorChecker 统一判定，只提示不自动改写
aliases:
- 需核实
- stale
- 锚点
source:
  kind: document
---
结论：需核实（stale）由 AnchorChecker 统一判定，检索、图谱、读码摘要、拦截、Wiki、health 共用。过期只提示，不自动归档或改写；处理只有 confirm，或 correction 加 supersedes。

判定：锚点文件删除或路径 resolve 后不在项目内，标已不存在（../../ 这类越界只警告仍可能写入，但读取走 _read_anchor，越界或 OSError 当已不存在，不去读项目外文件）。
路径#函数连名字都没有标找不到。
Git 下基准之后改过则比较函数块，相同不算过期。
SVN、无历史或取不到块时按文件判断。
未跟踪文件见同议题更正。

基准精确到秒。
写入取 ULID 时间（与 note_date 不同天时按 note_date 当天结束），核对取 verified_at。
只顺延到写入或核对后 7 天内第一次提交。
从没提交的草稿取现在。
Git 时间用 UTC 且不早于 1970-01-02。
写入后才拉进来、提交时间早于写入、却改了锚点的提交也要报。

缓存：仅 Git（cheap_dirty_files）用 anchors.json，工作区指纹变化即作废，单条 10 分钟，reindex 删除。
SVN 不做指纹（全量 status 太慢）。
新版本库只有 dirty_files 够快才开缓存。
锚点尽量写到函数。
记忆先提交、代码后提交会误报，核对后 confirm。

合并自 2 条结论。必须保持的行为详见同议题功能记录。
