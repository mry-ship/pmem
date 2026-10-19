---
id: 01M59J79WE1DY0Q8BY6VTKFRB2
module: feature.Retrieval
entity: Graph
kind: correction
status: active
supersedes: []
anchors:
- src/pmem/index/graph.py#related
- src/pmem/index/anchors.py#_changed_after
- src/pmem/index/embedder.py#LazyOnnxEmbedder
revision: git:df9b06c
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 共享代码虚高
- 相关模块
- 缓存只增不减
- 模型加载失败重试
- 离线检索慢
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
更正：记忆图谱和检索返回的“相关模块（共享代码 N）”原先按“记忆对”累加，共享 gate.py 这类大文件的模块全被算成“共享代码 36”，看不出真实关联强度。现在按共享的不同文件数计，文案改为“共享代码 N 个文件”。
同时：
1) 长驻 MCP 进程里过期核对的两个缓存（按文件组合+日期的改动结果、按文件+基准日的旧版本内容）原先只增不减，超过 512 项整体清空。
2) 语义模型（LazyOnnxEmbedder）加载失败后记住失败，10 分钟内不再重试、直接退回关键词检索；原先离线时每次检索都重新尝试加载（可能卡在下载上拖到看门狗超时）。
3) 类型中文名、可见状态常量改从 core/entry.py 导入（见 infra.Model）。
