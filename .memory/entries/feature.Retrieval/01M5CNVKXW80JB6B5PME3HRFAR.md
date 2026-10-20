---
id: 01M5CNVKXW80JB6B5PME3HRFAR
module: feature.Retrieval
entity: StaleCheck
kind: feature
status: active
supersedes:
- 01M5CGMQAG58YE2JFCKAZZSVBA
anchors:
- src/pmem/index/anchors.py#AnchorChecker.check
- src/pmem/index/anchors.py#_python_block
- src/pmem/index/anchors.py#_python_tree
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 合并进来的旧提交也报需核实；Python 函数块按语法树取起止行（含装饰器），不打警告
verify: uv run pytest tests/index/test_anchors.py tests/test_robustness.py -k "merged
  or confirmed_memory or flush_left or decorator or syntax_warnings"
applies: 'Git 版本库，记忆的 revision 以 git: 开头（Python 函数块规则不限版本库）'
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 深度审查后要求修复，并同意过期核对按写入时版本号补查；之后两轮复查又要求全部修复。
必须保持：
1) 记忆写下后，写入时本地没有、之后拉取或合并进来的提交（提交时间早于写入）改了锚点文件或函数时，要报“需核实”，提示带“之后拉取或合并进来”；
   只改了别的函数不报；
   确认过的记忆不按写入版本复查。
   写入之后的提交仍按精确到秒、基准不后移的时间规则。
2) Python 函数块先用语法树取起止行（含多行装饰器，“类.成员”先找类再找成员），顶格的多行字符串、转义引号不再截错；解析不了时退回缩进规则（单行 def、冒号后带注释的 def 只取自身）。
3) 解析用户代码时忽略 SyntaxWarning，不污染 --brief 输出和 Hook 的 stderr。
入口：AnchorChecker.check、index/anchors.py 的 _python_block / _python_tree。
