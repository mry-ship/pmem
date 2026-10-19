import json
import os
import queue
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from pmem.server import watchdog as wd

FAKE_CHILD = """\
import json, os, sys
initialized = False
for line in sys.stdin:
    msg = json.loads(line)
    method = msg.get("method")
    if method == "initialize":
        initialized = True
    elif "id" not in msg or method == "hang":
        continue
    elif method == "crash":
        os._exit(3)
    if not initialized:
        out = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32002, "message": "not initialized"}}
    else:
        out = {"jsonrpc": "2.0", "id": msg["id"], "result": {"pid": os.getpid(), "method": method}}
    print(json.dumps(out), flush=True)
"""


@pytest.fixture
def dog(tmp_path, monkeypatch):
    monkeypatch.setattr(wd, "RELOAD_CHECK_SECONDS", 0)
    script = tmp_path / "child.py"
    script.write_text(FAKE_CHILD, encoding="utf-8")
    cin_r, cin_w = os.pipe()
    out_r, out_w = os.pipe()
    client, replies = os.fdopen(cin_w, "wb", 0), os.fdopen(out_r, "rb", 0)
    restarts: list[str] = []
    stamp = {"value": 1}
    watchdog = wd.Watchdog([sys.executable, str(script)], os.fdopen(cin_r, "rb", 0), os.fdopen(out_w, "wb", 0),
                           timeout=10, on_restart=lambda kind, reason: restarts.append(kind),
                           stamp=lambda: stamp["value"])
    thread = threading.Thread(target=watchdog.run, daemon=True)
    thread.start()
    inbox: queue.Queue = queue.Queue()
    threading.Thread(target=lambda: [inbox.put(json.loads(raw)) for raw in iter(replies.readline, b"")],
                     daemon=True).start()

    def send(msg_id, method, **params):
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        if msg_id is not None:
            msg["id"] = msg_id
        client.write((json.dumps(msg) + "\n").encode("utf-8"))

    def call(msg_id, method="ping", **params):
        send(msg_id, method, **params)
        reply = inbox.get(timeout=15)
        assert reply["id"] == msg_id
        return reply

    def short_timeout():
        watchdog.timeout = watchdog.current_timeout = 1.5

    def handshake():
        reply = call(1, "initialize", protocolVersion="2025-06-18")
        assert "result" in reply, (reply, restarts)
        pid = reply["result"]["pid"]
        send(None, "notifications/initialized")
        return pid

    yield SimpleNamespace(send=send, call=call, handshake=handshake, short_timeout=short_timeout, restarts=restarts, stamp=stamp,
                          watchdog=watchdog, thread=thread, client=client)
    client.close()
    thread.join(10)


def test_forwards_requests_to_child(dog):
    pid = dog.handshake()
    assert dog.call(2, "tools/list")["result"] == {"pid": pid, "method": "tools/list"}
    assert dog.restarts == []


def test_child_dying_before_handshake_answer_resends_it(dog):
    deadline = time.monotonic() + 10
    while dog.watchdog.child is None and time.monotonic() < deadline:
        time.sleep(0.05)
    dog.watchdog.child.kill()
    result = dog.call(1, "initialize", protocolVersion="2025-06-18")["result"]
    assert result["method"] == "initialize"


def test_crash_restarts_child_and_replays_handshake(dog):
    pid = dog.handshake()
    error = dog.call(2, "crash")["error"]
    assert "意外退出" in error["message"] and "重试" in error["message"]
    result = dog.call(3, "tools/list")["result"]
    assert result["pid"] != pid and result["method"] == "tools/list"
    assert dog.restarts == ["crash"]


def test_hung_request_times_out_and_restarts(dog):
    pid = dog.handshake()
    dog.short_timeout()
    started = time.monotonic()
    error = dog.call(2, "hang")["error"]
    assert "超过" in error["message"] and time.monotonic() - started < 10
    assert dog.watchdog.current_timeout == 3.0
    assert dog.call(3)["result"]["pid"] != pid
    assert dog.watchdog.current_timeout == 1.5
    assert dog.restarts == ["timeout"]


def test_cancelled_request_does_not_trigger_timeout(dog):
    pid = dog.handshake()
    dog.short_timeout()
    dog.send(2, "hang")
    dog.send(None, "notifications/cancelled", requestId=2)
    time.sleep(2.5)
    assert dog.call(3)["result"]["pid"] == pid
    assert dog.restarts == []


def test_crash_loop_backs_off_and_answers_immediately(dog):
    dog.handshake()
    dog.call(2, "crash")
    dog.call(3, "crash")
    error = dog.call(4)["error"]
    assert "秒后自动重启" in error["message"] and "pmem search" in error["message"]
    time.sleep(1.5)
    assert "result" in dog.call(5)


def test_code_update_reloads_idle_child(dog):
    pid = dog.handshake()
    dog.stamp["value"] = 2
    assert dog.call(2)["result"]["pid"] != pid
    assert dog.restarts == ["reload"]


def test_client_disconnect_stops_child(dog):
    dog.handshake()
    child = dog.watchdog.child
    dog.client.close()
    dog.thread.join(10)
    assert not dog.thread.is_alive() and child.poll() is not None
