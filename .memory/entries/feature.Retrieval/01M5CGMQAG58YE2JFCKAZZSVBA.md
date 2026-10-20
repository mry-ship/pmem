---
id: 01M5CGMQAG58YE2JFCKAZZSVBA
module: feature.Retrieval
entity: StaleCheck
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/index/anchors.py#_check_merged_in
- src/pmem/index/anchors.py#_block
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 合并进来的早于写入的提交也要报需核实；单行 def、装饰器按函数块识别
verify: uv run pytest tests/index/test_anchors.py -k "merged or confirmed_memory or
  one_line or decorators or trailing_comment"
applies: 'Git 版本库，记忆的 revision 以 git: 开头'
aliases:
- 需核实误报
- 函数块识别
- stale 误报
- 过期漏报
source:
  conversation: 56cad1c4-fae9-44ef-a1f2-9a52de89fdf1
---
需求来源：用户 2026-10-20 深度审查后要求修复确认过的问题，并同意过期核对按写入时版本号补查。
必须保持：记忆写下后，写入时本地没有、之后拉取或合并进来的提交（提交时间早于写入）改了锚点文件或函数时，要报“需核实”，提示带“之后拉取或合并进来”；
只改了别的函数不报；
确认过的记忆不按写入版本复查。
写入之后的提交仍按精确到秒、基准不后移的时间规则。
Python 函数块：单行 def、冒号后带注释的 def 只取自身，不延伸到文件末尾；同缩进的装饰器算在函数块内。
适用：Git；SVN 暂不支持按版本号补查。入口：AnchorChecker.check。
