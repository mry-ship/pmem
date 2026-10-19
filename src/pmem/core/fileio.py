"""记忆文件和 modules.yaml 的写入：先写临时文件再整体替换，MCP 服务、Hook 同时读取时不会读到半截内容。"""
from __future__ import annotations

import os
import time
from pathlib import Path

REPLACE_RETRIES = 5
_RETRY_WAIT = 0.05


def write_atomic(path: Path, text: str) -> None:
    # 临时文件以 .tmp 结尾，不会被当成记忆文件（*.md）扫进索引
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    for attempt in range(REPLACE_RETRIES):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            # Windows 上目标文件正被别的进程读着时会拒绝替换，稍等重试
            if attempt == REPLACE_RETRIES - 1:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(_RETRY_WAIT)
