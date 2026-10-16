---
id: 01M4X7E2GM36C8AX17HNRFGEGH
module: feature.Import
entity: LanceDB
kind: decision
status: active
supersedes: []
anchors:
- src/pmem/importers/lancedb.py
revision: git:f131206
author: 1002378395@qq.com
note_date: '2026-10-14'
---
决定：pmem import --lancedb 只读导入参考实现（tilematch-dev-memory 一类）的 LanceDB 记忆。

- 只读：先把库目录复制到临时目录再打开，不与正在运行的 MCP 服务争用文件，也不改源库（测试断言导入前后源目录文件不变）。
- 来源与幂等：每条写 source.conversation = "lancedb:<源 id>"，重复导入按它跳过。
  副作用是检索时每条自成一批、不受“同批最多 2 条”限制——这是有意的：导入作者统一（如 tilematch-team），若退回“作者+模块+90 分钟窗口”会把不同人的记忆误并成一批。
- 时间：ULID 用源 created_at（缺失用 note_date），按时间升序写入，保留新旧排序与衰减。
- kind 默认全部 conclusion；--guess-kind 按正文开头关键词猜（排除/更正/风险/决定），猜测不可靠所以不默认。
- 含疑似密钥的条目直接跳过并列出 id，不脱敏后写入。
- --catalog 只在 modules.yaml 还没有任何模块时填入参考目录，避免覆盖已有划分；参考目录没有 paths，路径映射需另行补。

实测：TileMatch 853 条 / 53 个模块导入成功，目录 75 个模块，reindex 生成 853 个向量。
