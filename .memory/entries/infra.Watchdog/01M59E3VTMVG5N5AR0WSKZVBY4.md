---
id: 01M59E3VTMVG5N5AR0WSKZVBY4
module: infra.Watchdog
entity: CLI
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py#build_parser
- src/pmem/cli/main.py#_serve
revision: git:21d24e9
author: 1002378395@qq.com
note_date: '2026-10-19'
aliases:
- worker
- 看门狗
verified: '2026-10-20'
verified_at: '2026-10-20T18:57:28.399+08:00'
---
决定：pmem serve 增加隐藏参数 --worker：带它时直接运行 MCP 服务（看门狗拉起子进程用），不带时先起看门狗。
子进程命令是 sys.executable -m pmem.cli.main serve --worker --root <已解析的根目录>，不依赖 PATH 里的 pmem，也不需要 pmem/__main__.py。
手动调试服务本身时可以直接加 --worker。
