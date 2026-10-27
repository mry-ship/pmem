---
id: 01M5EJPK0B2XNCSPBM77FT3GQW
module: infra.Common
entity: CLI
kind: feature
status: active
supersedes:
- 01M5CAW2W30BN2GJ03ENRHNT4K
- 01M5CCEYYSQ92P72EJQ3NCFY5V
- 01M5CHJ1P3C38QCCE31WMPYMDW
- 01M5CVMGWTES1S99334826CX3X
anchors:
- src/pmem/cli/main.py#build_parser
- src/pmem/cli/brief.py#_search
- src/pmem/cli/main.py
- src/pmem/cli/main.py#main
- src/pmem/cli/main.py#_preflight
- src/pmem/cli/main.py#_positive
- src/pmem/scan/lite.py#summarize
revision: git:44147b4
author: 1002378395@qq.com
note_date: '2026-10-21'
summary: 命令行功能：record/search 写读功能记录、map 与 compact --undo、统一报错退出码 2
applies: pmem 命令行（终端调用）
verified: '2026-10-27'
verified_at: '2026-10-27T14:44:21.736+08:00'
---
需求来源：用户 2026-10-19～20 陆续要求命令行能写功能记录、v0.3.2 记忆图和合并回滚（Issue #13）、修复 search.limit 不生效，以及两轮复查后的统一报错。
必须保持：
1) record 的 --kind 直接取 core/entry.py 的 KINDS（不手写一份），有 --applies；
   search 有 --id（可跟多个）。
   --brief 里功能记录单列一组（“功能记录与规划 N 条”），带 applies 的行下面加“适用：…”，并显示 applies_hint 和 missing；
   Wiki 正文后显示“适用条件”。
2) 有 pmem map（--out、--days、--json、--root）和 pmem compact --undo <id>，逻辑在 map_cmd、compact_cmd；
   README、使用手册、架构文档、设计文档 14.4 写明这两条命令、health 新增的三节和已知限制（旧版不认 reverted 字段）。
3) pmem search 的 --limit 默认不设值，由服务层按 search.limit（默认 5）取；不要写死成 5，否则配置永远不生效。
4) 除 init、scan、hook、serve、doctor、bench 外，每个命令先加载 config.yaml 和 modules.yaml，写错时 stderr 打一行“pmem：原因”、退出码 2；
   doctor 自己把配置错误列成 ✘。
5) --limit、--days、--top、--min、--depth、--repeats 必须是正整数，否则 argparse 报错。
6) stdout/stderr 强制 UTF-8；scan --root 不存在、wiki --out 指向文件、bench 用例文件不对都给一行原因；小项目里全部目录都不足 3 个文件时 scan 目录概览也列出并说明原因。
入口：cli/main.py 的 build_parser、main、_preflight、_positive、SERVICE_COMMANDS；
cli/brief.py 的 _search；
scan/lite.py 的 summarize。
合并自 4 条功能记录。
