---
id: 01M5CRAHS5FXD72CCJDW9DAB5H
module: infra.Common
entity: CLI
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/cli/main.py#main
- src/pmem/cli/main.py#_scan
revision: git:64dc634
author: 1002378395@qq.com
note_date: '2026-10-20'
summary: 配置或模块目录写错时命令行给一行原因、返回 2，不给异常栈
verify: uv run pytest tests/test_cli_flow.py -k one_line_error
aliases:
- 异常栈
- traceback
- 配置写错
source:
  conversation: 9ef91500-0ba8-471d-b103-5d232ce0615e
---
需求来源：用户 2026-10-20 要求全面查漏补缺。
必须保持：
1) 任何子命令遇到 ConfigError（config.yaml 取值不对）或 RegistryError（modules.yaml 写错）时，在 stderr 打一行“pmem：原因”并返回 2。
2) stdout 和 stderr 都强制 UTF-8（原先只有 stdout，中文错误在 GBK 控制台上可能再抛 UnicodeEncodeError）。
3) pmem scan --root 指向不存在的目录时返回 2 并说明。
4) 没有 help 的参数补了说明；--content-file 的说明改成“UTF-8 或带 BOM 的 UTF-16”，与实际解码一致。
5) 设计文档 4.4 的配置示例按 DEFAULTS 重写（原示例的 secret_patterns: default 会直接报 ConfigError），第 11 节去掉不存在的 pmem upgrade、migrate merge --rewrite、doctor --coverage、init --lang，并区分 health 与 report。
入口：cli/main.py 的 main。
