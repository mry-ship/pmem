---
id: 01M59J7MB4DFCDF3ZSPVSC86RH
module: feature.Tools
entity: Robustness
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/server/app.py#build_server
- src/pmem/service/record.py#_normalize_anchor
- src/pmem/service/record.py#_on_disk_case
revision: git:df9b06c
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 并发
- 线程安全
- 异常兜底
- 配置写错 MCP 起不来
- 锚点大小写
- 绝对路径锚点
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
source:
  conversation: 7e7aeed7-103b-4d87-bb8d-18765c815bd5
---
决定：MCP 工具入口（server/app.py 的 build_server）统一经 call() 执行：
1) 加一把锁串行。mcp 框架把同步工具放进线程池并发跑，索引 refresh 增删 _items 时另一线程在遍历、sqlite 连接跨线程共用、模型可能重复加载。
2) 任何异常都转成带 "server":"pmem" 的 ok:false（“pmem 内部错误：类型: 信息”），否则框架返回的纯文本错误没有来源标记，闸门认不出。
3) MemoryService 懒创建；config.yaml 写错时每次调用返回具体原因，改好即恢复，不再让 worker 子进程启动即崩、被看门狗无限重启。
写入时锚点规范化：绝对路径转相对、按磁盘真实大小写拼路径（Windows 不区分大小写而 git 区分，原来这类锚点永远不会标“需核实”）；
调用方显式传入的锚点文件不存在或在项目外时附 warnings，继承来的不提示。
作者统一取缓存的 self.user。
