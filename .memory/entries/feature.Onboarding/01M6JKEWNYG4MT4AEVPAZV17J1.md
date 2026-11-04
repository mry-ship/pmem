---
id: 01M6JKEWNYG4MT4AEVPAZV17J1
module: feature.Onboarding
entity: McpUserServe
kind: risk
status: active
supersedes: []
anchors:
- src/pmem/server/watchdog.py
revision: git:e51a54a
author: 1002378395@qq.com
note_date: '2026-11-04'
summary: 用户级 pmem MCP：Windows 上外层勿用 pythonw，子进程勿 CREATE_NO_WINDOW，否则握手断
verify: 手动 PIPE 握手能拿到 serverInfo；Cursor Restart 后 user-pmem 非 error
applies: Windows 用户级 ~/.cursor/mcp.json 经 pmem-mcp-serve.py 启动时
aliases:
- user-pmem
- Connection closed
- live tool discovery
---
现象：Cursor 里 user-pmem 报 failed during live tool discovery / Connection closed；
本机 pmem CLI 正常，Agent 改跑终端 pmem 导致 Terminal 面板被顶出。
排查：~/.local/bin/pmem-mcp-serve.py 选 root 后 subprocess 拉 uv tools 里的 python -m pmem.cli.main serve。实测：
  (1) 外层用 pythonw.exe 时子进程 MCP stdout 读不到 initialize；
  (2) 子进程加 CREATE_NO_WINDOW 同样握手无响应；
  (3) 外层 python.exe + 内层 python.exe 继承 stdio 可在约 2s 内完成 initialize/tools/list。
启动日志用 ASCII 写 stderr，避免 GBK 干扰 Cursor 日志。
修复后需在 Cursor MCP 面板 Restart user-pmem。
