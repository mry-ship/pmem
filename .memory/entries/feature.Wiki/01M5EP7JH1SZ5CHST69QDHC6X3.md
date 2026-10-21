---
id: 01M5EP7JH1SZ5CHST69QDHC6X3
module: feature.Wiki
entity: Hierarchy
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/wiki.py#_module_page
- src/pmem/generate/wiki.py#_index_page
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: Wiki 索引子模块紧跟父模块并缩进；模块页列上级、下级和手工 related，相关模块排除直系
verify: uv run pytest tests/test_module_hierarchy.py -k wiki
aliases:
- Wiki 层级
- Wiki 子模块
source:
  conversation: 9622f1ee-c79a-429b-b50b-25228d393eb8
---
需求来源：父子模块设计第四阶段。
必须保持的行为：
- 索引按大类分组后按模块名小写排序，子模块紧跟父模块，第 3 段前加“└ ”，第 4 段再缩进一个全角空格。
- 模块页列“上级模块”（注明上级的教训同样适用）和“下级模块”（登记的下级加上有页面的未登记下级）；只有有页面的模块才加链接，其余用代码格式，避免死链接。
- “相关模块”先列 modules.yaml 里双向的手工 related（“手工登记：原因”），再列计算出的，直系模块和已手工列出的不重复列。
入口：src/pmem/generate/wiki.py（_module_page、_index_page、render_wiki）。
