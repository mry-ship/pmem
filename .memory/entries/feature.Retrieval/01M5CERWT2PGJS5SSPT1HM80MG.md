---
id: 01M5CERWT2PGJS5SSPT1HM80MG
module: feature.Retrieval
entity: StaleCheck
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py#AnchorChecker._baselines
- src/pmem/index/anchors.py#AnchorChecker._check
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 过期判定必须严格：精确到秒、基准不后移、只提示不自动删改
aliases:
- 需核实
- 过期
- stale
---
需求来源：负责人要求“过期这个事情检查和处理要很严格，不要乱删内容”（2026-10-20）。

必须保持的行为：
- 记忆写下或核对之后，关联代码的任何改动都要能让它标“需核实”，包括同一天稍后的改动（比较精确到秒，不按天）。
- 基准只顺延到记忆写入（或核对）后 7 天内的第一次提交，用来容纳“记忆和代码一起提交”；之后格式化、归档、改锚点再提交记忆文件，不能让基准后移。
- 函数定义被删掉（文件里只剩调用或同名变量）要报“找不到”，不能只说“改过”或放过。
- 宁可误报不漏报：拿不准时退回按文件判断，而不是当作没改。
- 过期只提示，从不自动归档、删除或改写记忆；处理方式只有两种：核对后 confirm，或写 correction 并用 supersedes 替代。

入口：src/pmem/index/anchors.py 的 AnchorChecker（检索、memory_graph、读代码摘要、拦截、Wiki、health 共用）；
时刻查询在 vcs 适配层（changed_since、commit_times、file_before）。
