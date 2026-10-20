---
id: 01M5CFPZ23KMEC39WMDHNS5W5E
module: feature.Retrieval
entity: Graph
kind: correction
status: active
supersedes:
- 01M59J79WE1DY0Q8BY6VTKFRB2
anchors:
- src/pmem/index/graph.py#related
- src/pmem/index/anchors.py#_cached
- src/pmem/index/anchors.py#MAX_CACHED
- src/pmem/index/embedder.py#LazyOnnxEmbedder
revision: git:7c086e5
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 相关模块按共享的不同文件数计；过期核对缓存超 512 项清空
aliases:
- 相关模块
- 共享代码
- 缓存上限
source:
  conversation: ca2edda2-f749-419e-aa6d-74617201a8d5
---
更正：记忆图谱和检索返回的“相关模块（共享代码 N）”原先按“记忆对”累加，共享 gate.py 这类大文件的模块全被算成“共享代码 36”，看不出真实关联强度。现在按共享的不同文件数计，文案为“共享代码 N 个文件”。
同时：
1) 长驻 MCP 进程里过期核对的两个进程内缓存（按“类型+文件组合+起始时刻”存的改动结果、按“文件+基准时刻”存的旧版文件内容）超过 512 项整体清空，原先只增不减。
   更正：缓存键已从“日期”改为精确到秒的时刻（见 StaleCheck 更正）。
2) 语义模型（LazyOnnxEmbedder）加载失败后记住失败，10 分钟内不再重试、直接退回关键词检索；原先离线时每次检索都重新尝试加载（可能卡在下载上拖到看门狗超时）。
3) 类型中文名、可见状态常量从 core/entry.py 导入（见 infra.Model）。
