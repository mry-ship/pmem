---
id: 01M6R570QVY12HK88EVY9BD5YX
module: feature.Gate
entity: ShellParse
kind: feature
status: active
supersedes: []
anchors:
- src/pmem/hooks/shell/__init__.py
- src/pmem/hooks/shell/targets.py
- src/pmem/hooks/shell/lexer.py
- src/pmem/hooks/shell/constants.py
revision: git:9c0cf10
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: shell.py 683 行拆成 shell/ 包（constants/lexer/targets/__init__），对外 7 名不变、行为零变化
verify: uv run pytest tests/hooks/test_gate.py；from pmem.hooks.shell import scan,cli_args,may_change_unseen,searched_before_writes,shell_write_targets,VARIABLE_PATH,WILDCARD_PATH
aliases:
- 单文件复杂度
- 重构拆分
---
需求来源：单文件复杂度偏高，hooks/shell.py 683 行把分词、拆句、命令识别、写目标提取、heredoc、cd 跟踪挤在一起，维护门槛高。拆成包，纯重构不改行为。

必须保持的行为：
- 对外仍从 pmem.hooks.shell 导入这 7 个名字（调用方 gate/guard/mcp/snapshot 与全部测试都走它，没有谁 import 子模块或私有 _ 函数）：scan、cli_args、may_change_unseen、searched_before_writes、shell_write_targets、VARIABLE_PATH、WILDCARD_PATH；
  另 MAX_PARSED_COMMAND 也从这里导出。
- 拆分后结构：constants.py（所有命令名集合、只读名单、正则，纯数据）、lexer.py（_strip_heredocs/_statements/_segments/_tokens/_command/_redirects/_expand/_read_small/_unbalanced_quotes，分词与拆句）、targets.py（各命令写目标提取 + _scan/scan 等编排与对外函数）、__init__.py（只 re-export 7 个公开名）。
- 递归链 _scan→_segment_targets→各提取器耦合紧，全放 targets.py 一处，避免循环 import。
- 行为零变化：908 测试全绿，其中 tests/hooks/test_gate.py（闸门全量）兜底。

坑（拆分时踩到）：从原文件机械抽函数时，_unbalanced_quotes 既被 lexer 导入又被原样复制进 targets（F811 重复定义），_PIPED_ITEMS 漏加进 targets 的 constants 导入（F821）。
靠 ruff F811/F821 + 测试抓出，不是逻辑问题。

入口：src/pmem/hooks/shell/（__init__、constants、lexer、targets）。
