---
id: 01M51WQ2D7CAYHMHXX53YQJQHT
module: infra.Common
entity: CLI
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/reindex_cmd.py#run_reindex
revision: git:4479338
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- 重建索引
- reindex
- 清缓存
---
决定：pmem reindex 删除的缓存文件增加 anchors.json（过期核对的跨进程缓存）。怀疑“需核实”标记不对、或改了 .gitignore 让锚点文件变成被忽略时，跑一次 pmem reindex 即可强制重新核对；平时缓存会在提交号或未提交文件变化时自动失效，最长 10 分钟。
