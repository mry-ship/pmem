---
id: 01M6N8HG0C9EWHEHN4A1VEHFH6
module: feature.Onboarding
entity: WindowsConsole
kind: conclusion
status: active
supersedes: []
anchors: []
revision: git:4d776a5
author: 1002378395@qq.com
note_date: '2026-11-05'
summary: Art出图闪窗：闸门勿匹配Shell+CLI用pyw
applies: Windows + Cursor-Pmem-Art 出图/converge
---
现象：pmem-art 出图仍疯狂弹控制台。
磁盘上 art hook 已是 pyw，但出图闭环会大量 Shell 跑 python pmem_art.py；
pmemw pre-tool 若 matcher 含 Shell，每条再闪一次。处理：
  1) lifecycle._strip_shell_from_pmem_pretool 在 win32 合并 stubs 时去掉 Shell；
闸门仍拦 Write/Edit/MCP。
  2) 规则写明 Windows 必须 pyw -3 -u 或 pmem_artw.cmd，禁止 python/python3。
  3) GenerateImage 继续只绑 art pre/post/stop。
改完后必须重开 Art 的 Cursor 窗口。
