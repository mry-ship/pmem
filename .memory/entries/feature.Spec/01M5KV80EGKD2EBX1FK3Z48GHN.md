---
id: 01M5KV80EGKD2EBX1FK3Z48GHN
module: feature.Spec
entity: RebuildSpec
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/generate/spec.py#init_specs
- src/pmem/cli/spec_cmd.py#run_spec
revision: git:299dbfb
author: 1002378395@qq.com
note_date: '2026-10-23'
summary: 没有已登记模块时不建规格目录，也不说首稿已写完
verify: uv run pytest tests/test_spec.py tests/test_autosync.py tests/test_cli_flow.py
  tests/hooks/test_gate.py -q
applies: 使用 pmem spec 或按 pmem-spec 写模块规格时
aliases:
- pmem spec
- pmem-spec
- 模块规格
verified: '2026-10-23'
verified_at: '2026-10-23T20:55:06.281+08:00'
source:
  conversation: 0d888a97-1b45-4e7c-8ac3-150747ba7b2e
---
用户要求（2026-10-23，Issue #16）：每个已登记模块一个目录，四份分开。正文一句一行。手动要完整补全时，命令只负责铺骨架并列出没写完的模块；正文由技能按代码写。
必须保持：目录是 .memory/specs/<模块>/，四份文件名固定。
上下级和代码路径只在该目录的 index.md。
美术那一份不放代码路径。
init 和 fill 只补还没有的文件，不覆盖已写正文。
没有未合并模块时不建规格目录，fill 只说明还没到这一步，不说首稿都已写完。
模块名单读不了时说明原因并返回 2，不抛出；
pmem init 仍完成接入。
fill 有未完成首稿时返回 1，都写完返回 0。
index 只刷新模块 index.md 和总目录。
留空列只提示，不改变 --check。
--check 只看程序和现状。
无画面写「本模块无画面」。
父模块不写子模块正文。
目录外或符号链接返回 2。
废弃模块不计入 --check。
旧的单文件在 init 或 index 时拆开。
入口：pmem spec、pmem spec init、pmem spec fill、pmem spec index、pmem spec --check。对 Agent 说「补全模块规格」时按代码写正文。
