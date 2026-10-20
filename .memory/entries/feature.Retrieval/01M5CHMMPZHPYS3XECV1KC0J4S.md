---
id: 01M5CHMMPZHPYS3XECV1KC0J4S
module: feature.Retrieval
entity: StaleRevision
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py#_check_merged_in
- src/pmem/index/anchors.py#_block
- src/pmem/vcs/git.py#commits_after
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 过期核对保留时间规则，另按写入版本补查后合并进来的旧提交
verify: uv run pytest tests/index/test_anchors.py -k "merged or one_line or decorator
  or comment"
aliases:
- 需核实
- stale
- 过期判定
- 合并后过期
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
现象：记忆写下时本地还没拉到的提交，提交时间早于写入时间，之后拉取或合并进来，纯按时间比较永远判不出过期。
取舍：没有把整个过期判定换成“按写入版本比内容”，只在时间规则之外补一层：对未被时间规则标出、也没被 confirm 过的记忆，取写入版本到 HEAD 之间、提交时间早于写入时间 60 秒以上的提交；
符号锚点比较该提交前后的符号块，文件锚点直接算改过。
原因：时间规则已有“精确到秒、基准不后移”的约束和大量测试，整体替换风险大；
补充规则只覆盖时间规则的盲区。
代价与限制：合并进来的提交最多查 10 个；SVN 没有 commits_after，不支持这条补充规则；confirm 过的记忆不再回查写入版本（核对日期已代表人工确认）。在本仓库真实数据上补充规则产生 0 条误报。
顺带修了符号块截取：单行 def、行尾注释里带冒号、装饰器都会让 Python 符号块截错，导致改别的函数也被判过期或该判的没判。
