from __future__ import annotations

import os
import re
import threading
import time

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ULID_PATTERN = r"[0-9A-HJKMNP-TV-Z]{26}"
_ULID_RE = re.compile(ULID_PATTERN)
_RANDOM_BITS = 80
_lock = threading.Lock()
_last_ms = -1
_last_rand = 0


def _encode(value: int, length: int) -> str:
    chars = []
    for _ in range(length):
        value, rem = divmod(value, 32)
        chars.append(ALPHABET[rem])
    return "".join(reversed(chars))


def is_ulid(value: str) -> bool:
    return bool(_ULID_RE.fullmatch(str(value or "")))


def new_ulid(now_ms: int | None = None) -> str:
    """生成单调递增的 ULID：同一毫秒内随机部分加一，时钟回拨时沿用上一毫秒。

    显式给出 now_ms（如导入历史记忆）时按原时间生成，不参与也不影响单调序列。"""
    global _last_ms, _last_rand
    if now_ms is not None:
        return _encode(now_ms, 10) + _encode(int.from_bytes(os.urandom(_RANDOM_BITS // 8), "big"), 16)
    ms = int(time.time() * 1000)
    with _lock:
        if ms <= _last_ms:
            ms = _last_ms
            rand = (_last_rand + 1) & ((1 << _RANDOM_BITS) - 1)
        else:
            rand = int.from_bytes(os.urandom(_RANDOM_BITS // 8), "big")
        _last_ms, _last_rand = ms, rand
    return _encode(ms, 10) + _encode(rand, 16)
