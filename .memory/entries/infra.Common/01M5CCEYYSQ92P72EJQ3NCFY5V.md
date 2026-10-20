---
id: 01M5CCEYYSQ92P72EJQ3NCFY5V
module: infra.Common
entity: CLI
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py#build_parser
revision: git:030bbcb
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 命令行新增 pmem map 与 compact --undo，文档同步写明
---
需求来源：用户要求 v0.3.2 的记忆图和合并回滚（Issue #13），并要求路线进度都记在 GitHub 和文档里。
必须保持的行为：
- 命令行新增 pmem map（--out、--days、--json、--root）和 pmem compact --undo <id>；main.py 只解析参数，逻辑在 map_cmd、compact_cmd。
- README、使用手册、架构文档、设计文档 14.4 写明这两条命令、health 新增的三节，以及已知限制：旧版不认 reverted 字段。
入口：src/pmem/cli/main.py 的 build_parser。
