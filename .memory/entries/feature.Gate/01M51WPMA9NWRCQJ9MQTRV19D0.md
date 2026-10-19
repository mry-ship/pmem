---
id: 01M51WPMA9NWRCQJ9MQTRV19D0
module: feature.Gate
entity: HookLatency
kind: risk
status: active
supersedes:
- 01M51RTVY753D7A8F86XZ3TEG1
anchors:
- .cursor/hooks.json
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- Hook 耗时
- Hook 慢
- 延迟
- 卡
- latency
- 录制钩子
---
风险：每次工具调用都会额外启动 pmem hook 进程，有固定开销。
2026-10-16 轻量化之后在本仓库（Windows，已装语义模型）实测：不涉及模块的 post-tool 约 0.17 秒，读代码附摘要约 0.30 秒，改前拦截（deny）约 0.30 秒；
此前分别约 0.20、0.46、0.39 秒。
剩余开销主要是 Python 启动（约 65 毫秒）、取工作区指纹的 2 次 git 调用（约 70 毫秒）和读模块记忆时导入 yaml。
本仓库 .cursor/hooks.json 里用于观察 Cursor Hook 行为的 spike/cursor_hooks/record.py 录制钩子已全部删除（原来每个事件多起一个 python，afterFileEdit 多 4 个），现在只剩 7 个 pmem hook，与 pmem init 模板一致。
需要再研究 Cursor Hook 载荷时，临时加回录制钩子，用完删掉。
