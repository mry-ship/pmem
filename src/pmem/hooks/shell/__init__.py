"""终端命令解析：会写到哪些文件、是否在跑脚本，以及命令里的 pmem search/record 调用。

按职责拆分：constants 常量与正则、lexer 分词与拆句、targets 写目标识别与对外接口。
对外仍从 pmem.hooks.shell 导入以下名字，拆分不改调用方。
"""
from __future__ import annotations

from pmem.hooks.shell.constants import MAX_PARSED_COMMAND, VARIABLE_PATH, WILDCARD_PATH
from pmem.hooks.shell.targets import (
    cli_args,
    may_change_unseen,
    scan,
    searched_before_writes,
    shell_write_targets,
)

__all__ = [
    "MAX_PARSED_COMMAND",
    "VARIABLE_PATH",
    "WILDCARD_PATH",
    "cli_args",
    "may_change_unseen",
    "scan",
    "searched_before_writes",
    "shell_write_targets",
]
