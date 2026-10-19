---
id: 01M51PJS4Z9M2WF1ZVCR5Y07ZC
module: feature.Wiki
entity: Wiki
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/generate/wiki.py
- src/pmem/generate/templates.py
revision: git:9510a42
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 知识图谱
- 需核实
- gitignore
---
决定：Wiki 生成逻辑放在 src/pmem/generate/wiki.py，命令行 pmem wiki 和写入后自动生成共用。

页面规则：
- 现行记忆的关联代码之后改过或已删除的，标题加“⚠ 需核实”，并引用具体原因；模块页和首页统计需核实的条数。
- 内容没变的页面不重写；只删除带生成标记、且已不对应任何模块的旧页面，手写的笔记保留。
- 目录首次创建时放一个内容为 * 的 .gitignore：Wiki 是派生视图，默认不进版本库，以免团队里出现过时的副本或合并冲突。想提交就删掉这个文件，之后不会再生成。

config.yaml 模板新增 wiki.auto / wiki.dir 两项。
