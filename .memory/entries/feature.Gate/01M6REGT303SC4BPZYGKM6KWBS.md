---
id: 01M6REGT303SC4BPZYGKM6KWBS
module: feature.Gate
entity: ShellParse
kind: feature
status: active
supersedes:
- 01M6R570QVY12HK88EVY9BD5YX
anchors:
- src/pmem/hooks/shell/__init__.py
- src/pmem/hooks/shell/constants.py#is_interpreter
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: shell 包对外仍只导出原来的 7 个名字
verify: uv run pytest tests/hooks/test_gate.py -q
applies: 改 hooks/shell 的公开导入或解释器识别时
aliases:
- 重构拆分
- 对外导出
---
需求来源：单文件复杂度偏高，hooks/shell.py 683 行把分词、拆句、命令识别、写目标提取、heredoc、cd 跟踪挤在一起，维护门槛高。拆成包。拆分当时是纯重构，不改解析行为。

必须保持的行为：
- 对外仍从 pmem.hooks.shell 导入这 7 个名字（调用方 gate/guard/mcp/snapshot 与全部测试都走它，没有谁 import 子模块或私有 _ 函数）：scan、cli_args、may_change_unseen、searched_before_writes、shell_write_targets、VARIABLE_PATH、WILDCARD_PATH；
  另 MAX_PARSED_COMMAND 也从这里导出。
- 拆分后结构：constants.py（命令名集合、只读名单、正则）、lexer.py（分词与拆句）、targets.py（写目标提取与对外函数）、__init__.py（只 re-export 公开名）。
- 递归链 _scan 到 _segment_targets 到各提取器耦合紧，全放 targets.py 一处，避免循环 import。
- 拆分本身不改对外名字。不要把「拆分当时行为不变」理解成以后不能改解析：带版本号的 python3.12 必须事前读脚本，以 CommandSurface 那条为准，不要为了这条拆分记录改回去。

坑（拆分时踩到）：从原文件机械抽函数时，_unbalanced_quotes 既被 lexer 导入又被原样复制进 targets（F811 重复定义），_PIPED_ITEMS 漏加进 targets 的 constants 导入（F821）。
靠 ruff F811/F821 加测试抓出，不是逻辑问题。

入口：src/pmem/hooks/shell/（__init__、constants、lexer、targets）。
