---
id: 01M59E3Q2YACDS3Q8W6WD7F7ZZ
module: feature.Tools
entity: Watchdog
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/server/watchdog.py#Watchdog
- src/pmem/server/app.py#serve
revision: git:21d24e9
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- 看门狗
- 断开
- 重连
- 掉线
- MCP断开
- 自动重启
- watchdog
---
决定：pmem serve 默认带看门狗（src/pmem/server/watchdog.py）。Cursor 只连着这个轻量进程，真正的 MCP 服务跑在 pmem serve --worker 子进程里。

问题：MCP 是 Cursor 用 stdio 拉起的常驻进程，崩溃、卡死后 Cursor 不会自动重连，工具一直不可用，闸门和检索全部失效；改了或升级了 pmem 代码，也要手动重启 MCP 才生效。

做法：
- 子进程退出、单次请求超过 server.request_timeout（默认 120 秒）、或 pmem 包里的 .py 修改时间变了（空闲时才换）就换新子进程；
- 用缓存的客户端 initialize 替它重新握手（内部 id，响应吞掉），再补发 notifications/initialized，握手完成前到的消息先排队；
- 进行中的请求回 JSON-RPC 错误“正在自动重启，请重试”；连续失败按 0/1/2/5/10/30 秒退避，退避期间的请求立即回错误并提示用终端 pmem search；
- 超时每发生一次放宽一倍（最多 8 倍），任一请求成功后恢复，避免首次下载语义模型、首次建索引这种“慢但没死”的任务被反复杀掉；
- 客户端取消（notifications/cancelled）的请求不再计时；客户端断开时关掉子进程；
- 看门狗不导入 mcp 和服务层，日志按 UTF-8 写 stderr（管道下默认 GBK，Cursor 读日志会乱码）；Windows 下子进程用 CREATE_NO_WINDOW。
- 重启记本机事件 server_restart（kind=crash/timeout/reload），pmem health 只统计 crash 和 timeout。

验证：假子进程测试覆盖转发、崩溃重握手、超时、取消、退避、代码更新重载、握手前崩溃、客户端断开；真实 pmem serve 端到端：杀掉 worker 后下一次 search_memory 1～2 秒内正常返回。

风险：看门狗判断不了“慢”和“卡死”，只按超时；
Cursor 已把 MCP 标为出错（如启动时找不到 pmem）的情况管不到；
从无看门狗的旧版升级后，第一次仍需在 Cursor 里重启 MCP；
server.watchdog: false 可关闭。
