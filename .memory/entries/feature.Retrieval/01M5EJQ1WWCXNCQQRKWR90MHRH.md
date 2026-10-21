---
id: 01M5EJQ1WWCXNCQQRKWR90MHRH
module: feature.Retrieval
entity: StaleCheck
kind: feature
status: active
supersedes:
- 01M5CERWT2PGJS5SSPT1HM80MG
- 01M5CNVKXW80JB6B5PME3HRFAR
anchors:
- src/pmem/index/anchors.py#AnchorChecker._baselines
- src/pmem/index/anchors.py#AnchorChecker._check
- src/pmem/index/anchors.py#AnchorChecker.check
- src/pmem/index/anchors.py#_python_block
- src/pmem/index/anchors.py#_python_tree
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 过期检查必须严格：任何锚点改动都标需核实、宁可误报、从不自动删改记忆
applies: 所有用到需核实标记的入口：检索、记忆图、读码摘要、拦截、Wiki、health
aliases:
- 过期
- 需核实
---
需求来源：负责人 2026-10-20 要求“过期这个事情检查和处理要很严格，不要乱删内容”，之后深度审查和两轮复查要求全部修复，并同意按写入时版本号补查。
必须保持：
1) 记忆写下或核对之后，关联代码的任何改动都要能让它标“需核实”，包括同一天稍后的改动（精确到秒）。
2) 基准只顺延到写入（或核对）后 7 天内的第一次提交，用来容纳“记忆和代码一起提交”；之后格式化、归档、改锚点再提交记忆文件，不能让基准后移。
3) 写入时本地没有、之后拉取或合并进来的提交（提交时间早于写入）改了锚点文件或函数时，要报“需核实”，提示带“之后拉取或合并进来”；只改了别的函数不报；确认过的记忆不按写入版本复查。
4) 函数定义被删掉（只剩调用或同名变量）要报“找不到”。
   Python 函数块先用语法树取起止行（含多行装饰器，“类.成员”先找类再找成员）；
   解析不了时退回缩进规则（单行 def、冒号后带注释的 def 只取自身）。
   解析用户代码时忽略 SyntaxWarning，不污染 --brief 输出和 Hook 的 stderr。
5) 宁可误报不漏报：拿不准时退回按文件判断，而不是当作没改。
6) 过期只提示，从不自动归档、删除或改写记忆；处理方式只有核对后 confirm，或写 correction 并用 supersedes 替代。
入口：src/pmem/index/anchors.py 的 AnchorChecker.check / _baselines、_python_block、_python_tree；
时刻查询在 vcs 适配层（changed_since、commit_times、file_before）。
合并自 2 条功能记录。
