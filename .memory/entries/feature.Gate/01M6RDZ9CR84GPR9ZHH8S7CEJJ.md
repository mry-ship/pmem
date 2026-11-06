---
id: 01M6RDZ9CR84GPR9ZHH8S7CEJJ
module: feature.Gate
entity: CommandSurface
kind: feature
status: active
supersedes:
- 01M6RD5MPS1XRH27TD6X4ZJGM1
anchors:
- src/pmem/hooks/shell/constants.py#is_interpreter
- src/pmem/hooks/shell/targets.py#_script_of
- src/pmem/hooks/memories.py#_lines
revision: git:4bc1bee
author: 1002378395@qq.com
note_date: '2026-11-06'
summary: python3.12 事前读脚本，摘要行里的议题收成一行
verify: uv run pytest tests/hooks/test_gate.py::test_shell_write_targets_reads_scripts_and_patches
  tests/core/test_entry.py::test_memory_line_flattens_entity_newline -q
applies: 终端命令的事前写目标解析，以及 Hook 交给 Agent 的记忆摘要行
aliases:
- python3.12
- 摘要换行
---
需求来源：python3.12、python3.11.exe 不在解释器精确集合里，事前不读脚本，只能靠执行后的快照。手改记忆文件时，议题或日期里的换行会把闸门摘要拆成额外一行。

必须保持：
python、python3、py、node、deno，以及 python3.12、python312、python3.11.exe 这种带版本号的名字，都按解释器去读后面的脚本，找出脚本里的写入路径。
这些 python 名字也算 pmem 的启动器（python3.12 -m pmem search 仍算查过）。
pythonw、python3w 不是。
闸门摘要每一条都是一行：模块、议题、日期、标题里的换行和多余空白收成空格。占位用的核对标记不要折进这行文字里。

入口：is_interpreter、is_launcher、_script_of、MemoryView._lines。
