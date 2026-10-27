---
id: 01M51PKK3PK1GPSH0Z2J0FD0BX
module: feature.Wiki
entity: Wiki
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/wiki_cmd.py
revision: git:9510a42
author: 1002378395@qq.com
note_date: '2026-10-16'
aliases:
- pmem wiki
- 命令行
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:12.602+08:00'
---
决定：pmem wiki 命令（src/pmem/cli/wiki_cmd.py）只负责打开服务、调用 generate/wiki.py 的 write_wiki 并打印结果，不再包含渲染逻辑。
输出目录默认取 config 的 wiki.dir，--out 可以覆盖。

原因：record/confirm 写入后要自动生成 Wiki，服务层不应依赖命令行模块。渲染逻辑集中在一处，命令行和自动生成的输出才能一致。旧代码从 pmem.cli.wiki_cmd 导入的 MARKER 仍然可用。
