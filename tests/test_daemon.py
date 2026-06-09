import os
import shutil
import tempfile
import threading
import time

import pytest

from NEMbox.const import Constant
from NEMbox.daemon import (
    MusicboxDaemon,
    acquire_lock,
    is_daemon_running,
    release_lock,
    send_request,
)
from NEMbox.player import Player


@pytest.fixture
def runtime_paths(monkeypatch):
    # macOS AF_UNIX paths must stay short; pytest tmp_path names exceed the limit.
    runtime_dir = tempfile.mkdtemp(prefix="mbd-")
    monkeypatch.setattr(Constant, "runtime_dir", runtime_dir)
    monkeypatch.setattr(
        Constant, "socket_path", os.path.join(runtime_dir, "musicboxd.sock")
    )
    monkeypatch.setattr(
        Constant, "lock_path", os.path.join(runtime_dir, "musicboxd.lock")
    )
    yield runtime_dir
    shutil.rmtree(runtime_dir, ignore_errors=True)


def test_acquire_lock_is_exclusive(runtime_paths):
    fd1 = acquire_lock()
    assert fd1 is not None
    try:
        assert acquire_lock() is None
    finally:
        release_lock(fd1)
    fd2 = acquire_lock()
    assert fd2 is not None
    release_lock(fd2)


def test_tune_volume_persists_when_stopped():
    player = Player.__new__(Player)
    player.popen_handler = None
    player.current_backend = "mpv"
    player.storage = type(
        "Storage",
        (),
        {"database": {"player_info": {"playing_volume": 50}}},
    )()
    player.tune_volume(10)
    assert player.storage.database["player_info"]["playing_volume"] == 60


def test_daemon_volume_delta_when_stopped(runtime_paths):
    daemon = MusicboxDaemon()
    daemon.player.popen_handler = None
    daemon.player.info["playing_volume"] = 50
    result = daemon._volume({"delta": 10})
    assert result["volume"] == 60


def test_daemon_rpc_ping_status_and_shutdown(runtime_paths):
    daemon = MusicboxDaemon()
    errors: list[BaseException] = []

    def serve():
        try:
            daemon.serve()
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    deadline = time.time() + 5
    while time.time() < deadline:
        if is_daemon_running():
            break
        time.sleep(0.05)
    else:
        pytest.fail("daemon did not become reachable in time")

    try:
        ping = send_request("daemon.ping")
        assert ping["ok"] is True
        assert isinstance(ping["data"]["pid"], int)

        status = send_request("player.status")
        assert status["ok"] is True
        assert status["data"]["state"] in ("playing", "paused", "stopped")

        shutdown = send_request("daemon.shutdown")
        assert shutdown["ok"] is True
    finally:
        thread.join(timeout=5)

    assert errors == []
    assert not is_daemon_running()
