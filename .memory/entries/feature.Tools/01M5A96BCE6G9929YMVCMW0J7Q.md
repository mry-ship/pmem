---
id: 01M5A96BCE6G9929YMVCMW0J7Q
module: feature.Tools
entity: ConfigReload
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/server/app.py#build_server
revision: git:43a477e
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 热加载
- 重启
- 配置不生效
- config.yaml
source:
  conversation: b48c143a-9675-4a7b-97ea-8ee28f06840e
---
决定：MCP 服务（server/app.py 的 call）每次调用前看一眼 .memory/config.yaml 的修改时间和大小，变了就关掉旧的 MemoryService 并重建，写入校验、密钥规则、检索和嵌入设置下一次调用即生效。
原因：服务常驻，原先只在第一次调用时读配置，改了 config.yaml 后 Hook 和命令行已生效而 MCP 仍是旧配置，行为不一致。
modules.yaml 本来就按修改时间重读，不受影响。
例外：server.watchdog 和 server.request_timeout 由看门狗进程在启动时读，改了仍要在 Cursor 里重启 pmem 服务；手册和 architecture.md 已同步。
代价：重建后索引、嵌入模型要重新懒加载，改配置后的第一次检索会慢一些。
