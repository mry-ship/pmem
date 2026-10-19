"""MCP 服务看门狗：Cursor 只连着这个轻量进程，真正的服务跑在子进程里。

子进程崩溃、请求超时卡死、pmem 代码更新时，看门狗重启子进程，并用缓存的 initialize 替客户端重新握手，
客户端连接始终不断，不需要在 Cursor 里手动重启 MCP。正在处理的请求返回错误，提示重试。
这里不能导入 mcp、service 等重型模块：看门狗自身越简单越不容易挂。
"""
from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

DEFAULT_TIMEOUT = 120.0
MAX_TIMEOUT_FACTOR = 8
BACKOFF_SECONDS = (0, 1, 2, 5, 10, 30)
STABLE_SECONDS = 60.0
RELOAD_CHECK_SECONDS = 2.0
INIT_ID = "pmem-watchdog-init"
ERROR_CODE = -32603


def package_stamp() -> int:
    base = Path(__file__).resolve().parents[1]
    try:
        return max((p.stat().st_mtime_ns for p in base.rglob("*.py")), default=0)
    except OSError:
        return 0


def _parse(line: bytes) -> dict | None:
    try:
        msg = json.loads(line)
    except ValueError:
        return None
    return msg if isinstance(msg, dict) else None


def _key(msg_id) -> str:
    return json.dumps(msg_id)


def _dump(msg: dict) -> bytes:
    return json.dumps(msg, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"


def _log(text: str) -> None:
    # 管道下 stderr 默认按系统代码页（中文 Windows 为 GBK）编码，MCP 客户端按 UTF-8 读日志会乱码
    stream = getattr(sys.stderr, "buffer", None)
    try:
        if stream is not None:
            stream.write(f"[pmem 看门狗] {text}\n".encode())
            stream.flush()
        else:
            sys.stderr.write(f"[pmem 看门狗] {text}\n")
    except (OSError, ValueError):
        pass


class Watchdog:
    def __init__(self, command: list[str], stdin: BinaryIO, stdout: BinaryIO, timeout: float = DEFAULT_TIMEOUT,
                 on_restart: Callable[[str, str], None] | None = None,
                 stamp: Callable[[], int] | None = package_stamp):
        self.command = command
        self.stdin, self.stdout = stdin, stdout
        self.timeout = self.current_timeout = timeout
        self.on_restart = on_restart or (lambda kind, reason: None)
        self.stamp_fn = stamp
        self.stamp = stamp() if stamp else 0
        self.last_check = time.monotonic()
        self.events: queue.Queue = queue.Queue()
        self.child: subprocess.Popen | None = None
        self.gen = 0
        self.started_at = 0.0
        self.init_request: dict | None = None
        self.initialized_note: dict | None = None
        self.ready = True
        self.init_sent_at = 0.0
        self.waiting: list[bytes] = []
        # 客户端请求：id 的 JSON 形式 → (发出时间, method, 原始 id)
        self.pending: dict[str, tuple[float, str, object]] = {}
        self.failures = 0
        self.next_start = 0.0
        self.down_reason = ""
        self.kill_reason: tuple[str, str] | None = None

    # ---- 主循环 ----

    def run(self) -> int:
        threading.Thread(target=self._read_client, daemon=True).start()
        self._start()
        while True:
            try:
                kind, *rest = self.events.get(timeout=0.5)
            except queue.Empty:
                kind, rest = None, []
            if kind == "eof":
                break
            try:
                if kind == "client":
                    self._from_client(rest[0])
                elif kind == "child" and rest[0] == self.gen:
                    self._from_child(rest[1])
                elif kind == "exit" and rest[0] == self.gen:
                    self._child_exited(rest[1])
                self._tick()
            except Exception as exc:  # noqa: BLE001
                _log(f"内部错误（已忽略）：{exc!r}")
        self._stop_child()
        return 0

    def _read_client(self) -> None:
        try:
            for line in iter(self.stdin.readline, b""):
                if line.strip():
                    self.events.put(("client", line))
        except (OSError, ValueError):
            pass
        self.events.put(("eof",))

    def _read_child(self, proc: subprocess.Popen, gen: int) -> None:
        try:
            for line in iter(proc.stdout.readline, b""):
                if line.strip():
                    self.events.put(("child", gen, line))
        except (OSError, ValueError):
            pass
        self.events.put(("exit", gen, proc.wait()))

    # ---- 子进程 ----

    def _start(self) -> None:
        self.gen += 1
        self.kill_reason = None
        self.started_at = time.monotonic()
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            self.child = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          bufsize=0, creationflags=flags)
        except OSError as exc:
            self.child = None
            self._schedule_restart("crash", f"无法启动（{exc}）")
            return
        threading.Thread(target=self._read_child, args=(self.child, self.gen), daemon=True).start()
        init_pending = any(method == "initialize" for _, method, _ in self.pending.values())
        if self.init_request is None or init_pending:
            # 客户端还没握手，或握手请求随上个子进程丢了：原样转发，响应照常回给客户端
            self.ready = True
            if init_pending:
                msg_id = self.init_request["id"]
                self.pending[_key(msg_id)] = (time.monotonic(), "initialize", msg_id)
                self._send_child(_dump(self.init_request))
            return
        self.ready = False
        self.init_sent_at = time.monotonic()
        self._send_child(_dump({**self.init_request, "id": INIT_ID}))

    def _send_child(self, line: bytes) -> None:
        if self.child is None or self.child.stdin is None:
            return
        try:
            self.child.stdin.write(line if line.endswith(b"\n") else line + b"\n")
            self.child.stdin.flush()
        except (OSError, ValueError):
            pass

    def _kill(self, kind: str, reason: str) -> None:
        if self.child is None or self.kill_reason:
            return
        self.kill_reason = (kind, reason)
        try:
            self.child.kill()
        except OSError:
            pass

    def _stop_child(self, wait: float = 3.0) -> None:
        proc, self.child = self.child, None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
            proc.wait(wait)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            try:
                proc.kill()
                proc.wait(wait)
            except (OSError, subprocess.TimeoutExpired):
                pass

    def _child_exited(self, code: int) -> None:
        kind, reason = self.kill_reason or ("crash", f"意外退出（返回码 {code}）")
        self.child = None
        for key, (_, method, msg_id) in list(self.pending.items()):
            if method != "initialize":
                self._reply_error(msg_id, f"pmem 记忆服务{reason}，正在自动重启，请重试这次调用")
                del self.pending[key]
        self.waiting.clear()
        self._schedule_restart(kind, reason)

    def _schedule_restart(self, kind: str, reason: str) -> None:
        now = time.monotonic()
        if now - self.started_at > STABLE_SECONDS:
            self.failures = 0
        delay = BACKOFF_SECONDS[min(self.failures, len(BACKOFF_SECONDS) - 1)]
        self.failures += 1
        self.next_start = now + delay
        self.down_reason = reason
        _log(f"服务{reason}，{delay} 秒后重启（连续第 {self.failures} 次）")
        self.on_restart(kind, reason)

    def _tick(self) -> None:
        now = time.monotonic()
        if self.child is None:
            if now >= self.next_start:
                self._start()
            return
        if self.kill_reason:
            return
        limit = self.current_timeout
        if not self.ready and now - self.init_sent_at > limit:
            self._timed_out(f"重新握手超过 {limit:g} 秒没有响应")
            return
        for started, method, _ in self.pending.values():
            if now - started > limit:
                self._timed_out(f"处理 {method} 超过 {limit:g} 秒没有响应")
                return

    def _timed_out(self, reason: str) -> None:
        # 首次下载语义模型、首次建索引可能只是慢：每超时一次放宽一倍，任一请求成功后恢复，免得永远做不完
        self._kill("timeout", reason)
        self.current_timeout = min(self.current_timeout * 2, self.timeout * MAX_TIMEOUT_FACTOR)

    def _maybe_reload(self) -> None:
        """pmem 代码更新（升级或开发中修改）后，在没有进行中的请求时换新子进程，免得一直跑旧代码。"""
        now = time.monotonic()
        if not self.stamp_fn or now - self.last_check < RELOAD_CHECK_SECONDS:
            return
        self.last_check = now
        if self.child is None or not self.ready or self.pending:
            return
        stamp = self.stamp_fn()
        if stamp == self.stamp:
            return
        self.stamp = stamp
        _log("检测到 pmem 代码更新，重新加载服务")
        self._stop_child()
        self.on_restart("reload", "代码已更新")
        self._start()

    # ---- 消息转发 ----

    def _from_client(self, line: bytes) -> None:
        msg = _parse(line)
        method = msg.get("method") if msg else None
        if method == "initialize":
            self.init_request = msg
        elif method == "notifications/initialized":
            self.initialized_note = msg
        elif method == "notifications/cancelled":
            self.pending.pop(_key((msg.get("params") or {}).get("requestId")), None)
        if method and "id" in msg:
            if method != "initialize":
                self._maybe_reload()
            if self.child is None:
                wait = max(0, round(self.next_start - time.monotonic()))
                self._reply_error(msg["id"], f"pmem 记忆服务{self.down_reason}，{wait} 秒后自动重启，请稍后重试；"
                                             "急用可在终端运行 pmem search --module <模块> --brief \"<要点>\"")
                return
            self.pending[_key(msg["id"])] = (time.monotonic(), method, msg["id"])
        if self.child is None:
            return
        if not self.ready:
            self.waiting.append(line)
            return
        self._send_child(line)

    def _from_child(self, line: bytes) -> None:
        msg = _parse(line)
        if msg and msg.get("id") == INIT_ID and "method" not in msg:
            if "error" in msg:
                self._kill("crash", f"重新握手失败（{msg['error'].get('message', '')}）")
                return
            self.ready = True
            if self.initialized_note:
                self._send_child(_dump(self.initialized_note))
            for waiting in self.waiting:
                self._send_child(waiting)
            self.waiting.clear()
            return
        if msg and "method" not in msg and "id" in msg and self.pending.pop(_key(msg["id"]), None):
            self.current_timeout = self.timeout
        self._write_client(line)

    def _reply_error(self, msg_id, message: str) -> None:
        self._write_client(_dump({"jsonrpc": "2.0", "id": msg_id, "error": {"code": ERROR_CODE, "message": message}}))

    def _write_client(self, line: bytes) -> None:
        try:
            self.stdout.write(line if line.endswith(b"\n") else line + b"\n")
            self.stdout.flush()
        except (OSError, ValueError):
            pass
