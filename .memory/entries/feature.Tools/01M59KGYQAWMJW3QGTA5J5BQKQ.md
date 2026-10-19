---
id: 01M59KGYQAWMJW3QGTA5J5BQKQ
module: feature.Tools
entity: Layout
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/service/__init__.py#MemoryService
- src/pmem/service/base.py#ServiceBase
revision: git:407c1fd
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- service 拆分
- MemoryService 组合
- 服务层结构
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：原 700 行的 service.py 改成 pmem/service/ 包，按职责分文件：base（依赖懒加载、fail/returns_errors、共用小工具）、search（检索、图谱、模块列表，只读）、record（写入规则）、status（confirm、归档、种子转正）、curation（高频词、可合并议题）。
MemoryService 由各 *Ops 类多重继承组合，对外导入路径（from pmem.service import MemoryService, COMPACT_MIN_GROUP）不变。

原因：检索、写入、状态变更挤在一个类里，改一类操作要通读全文件，扩展新操作也没有归处。新增一类操作时加一个 *Ops 文件并在 __init__ 里组合。

验证：方法体逐行不变；
对本仓库真实记忆跑同一批 24 组调用（search 各种组合、graph、list、terms、compact、seeds、record 校验失败、confirm/status 缺失 id），去掉 stale/check 后 JSON 完全一致；
511 个测试通过。
关联到 service.py 的 15 条记忆已用 pmem anchors --rename 改到新文件的函数。

风险：各 Ops 共享 ServiceBase 的属性，跨文件调用的方法（如 _refresh_wiki、_index_search、_relative）必须放在 base；常驻的 MCP 服务要等看门狗换子进程后才加载新结构。
