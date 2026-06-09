"""musicboxd: resident playback daemon (phase 2 of agent-cli-design.md).

The daemon owns the single stateful ``Player`` and ``database.json`` for the
whole machine. Control-type CLI commands talk to it over a Unix domain socket
using newline-delimited JSON-RPC. A flock-based single-owner lock makes the
daemon and the curses TUI mutually exclusive.
"""

from __future__ import annotations

import contextlib
import errno
import fcntl
import json
import os
import signal
import socket
import sys
import time
from typing import Any

from . import logger
from .api import NetEase
from .const import Constant
from .player import NullUi, Player
from .storage import Storage

log = logger.getLogger(__name__)

MODE_NAMES = {
    Player.MODE_ORDERED: "ordered",
    Player.MODE_ORDERED_LOOP: "ordered-loop",
    Player.MODE_SINGLE_LOOP: "single-loop",
    Player.MODE_RANDOM: "random",
    Player.MODE_RANDOM_LOOP: "random-loop",
}
NAME_TO_MODE = {name: mode for mode, name in MODE_NAMES.items()}

_READY_TIMEOUT = 8.0
_RECV_LIMIT = 1 << 20


class DaemonError(Exception):
    """Structured error surfaced to the CLI as ``{type, message, hint}``."""

    def __init__(self, error_type: str, message: str, hint: str = ""):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.hint = hint


def _ensure_runtime_dir() -> None:
    os.makedirs(Constant.runtime_dir, mode=0o700, exist_ok=True)


def acquire_lock() -> int | None:
    """Grab the single-owner flock. Returns the open fd, or None if held.

    The fd must stay open for the owner's whole lifetime; closing it (or the
    process exiting) releases the lock. Both ``musicboxd`` and the curses TUI
    use this, which makes them mutually exclusive.
    """
    _ensure_runtime_dir()
    fd = os.open(Constant.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    os.ftruncate(fd, 0)
    os.write(fd, str(os.getpid()).encode())
    return fd


def release_lock(fd: int | None) -> None:
    if fd is None:
        return
    with contextlib.suppress(Exception):
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def is_daemon_running() -> bool:
    """True if a daemon is reachable on the socket."""
    if not os.path.exists(Constant.socket_path):
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(1.0)
            client.connect(Constant.socket_path)
        return True
    except OSError:
        return False


def send_request(
    method: str, params: dict[str, Any] | None = None, timeout: float = 10.0
) -> dict[str, Any]:
    """Send one JSON-RPC request and return the parsed response.

    Raises ``ConnectionError`` when no daemon is listening.
    """
    payload = (
        json.dumps(
            {"id": 1, "method": method, "params": params or {}}, ensure_ascii=False
        ).encode()
        + b"\n"
    )
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(timeout)
            client.connect(Constant.socket_path)
            client.sendall(payload)
            data = b""
            while b"\n" not in data:
                chunk = client.recv(4096)
                if not chunk:
                    break
                data += chunk
    except (FileNotFoundError, ConnectionRefusedError) as exc:
        raise ConnectionError("daemon not running") from exc
    if not data:
        raise ConnectionError("empty response from daemon")
    return json.loads(data.split(b"\n", 1)[0].decode())


class MusicboxDaemon:
    def __init__(self):
        self.storage = Storage()
        self.storage.load()
        self.api = NetEase()
        self.player = Player(ui=NullUi())
        self.player.end_callback = None
        self._lock_fd: int | None = None
        self._server: socket.socket | None = None
        self._running = False

    # -- lifecycle ---------------------------------------------------------

    def _acquire_lock(self) -> bool:
        self._lock_fd = acquire_lock()
        return self._lock_fd is not None

    def _bind(self) -> None:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(Constant.socket_path)
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(Constant.socket_path)
        os.chmod(Constant.socket_path, 0o600)
        self._server.listen(8)

    def _cleanup(self) -> None:
        self._running = False
        with contextlib.suppress(Exception):
            self.player.stop()
        with contextlib.suppress(Exception):
            self.storage.save()
        if self._server is not None:
            with contextlib.suppress(Exception):
                self._server.close()
        with contextlib.suppress(FileNotFoundError):
            os.unlink(Constant.socket_path)
        release_lock(self._lock_fd)
        self._lock_fd = None

    def serve(self) -> int:
        if not self._acquire_lock():
            log.error("another daemon or TUI already owns the lock")
            print(
                "musicbox 已在运行（daemon 或 TUI 占用），无法启动 daemon",
                file=sys.stderr,
            )
            return 1
        self._bind()
        self._running = True

        def _on_signal(_signum, _frame):
            self._running = False
            with contextlib.suppress(Exception):
                if self._server is not None:
                    self._server.close()

        # signal only works on the main thread; spawn_daemon's child is fine.
        with contextlib.suppress(ValueError):
            signal.signal(signal.SIGTERM, _on_signal)
            signal.signal(signal.SIGINT, _on_signal)

        log.info("musicboxd listening on %s", Constant.socket_path)
        assert self._server is not None
        self._server.settimeout(1.0)
        try:
            while self._running:
                try:
                    conn, _ = self._server.accept()
                except TimeoutError:
                    continue
                except OSError as exc:
                    if exc.errno == errno.EBADF or not self._running:
                        break
                    log.warning("accept failed: %s", exc)
                    continue
                with conn:
                    self._handle_conn(conn)
        finally:
            self._cleanup()
        return 0

    # -- request handling --------------------------------------------------

    def _handle_conn(self, conn: socket.socket) -> None:
        conn.settimeout(10.0)
        data = b""
        try:
            while b"\n" not in data and len(data) < _RECV_LIMIT:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
        except OSError:
            return
        if not data:
            return
        req_id: Any = None
        try:
            req = json.loads(data.split(b"\n", 1)[0].decode())
            req_id = req.get("id")
            method = req.get("method", "")
            params = req.get("params") or {}
            result = self._dispatch(method, params)
            response = {"id": req_id, "ok": True, "data": result}
        except DaemonError as exc:
            response = {
                "id": req_id,
                "ok": False,
                "error": {
                    "type": exc.error_type,
                    "message": exc.message,
                    **({"hint": exc.hint} if exc.hint else {}),
                },
            }
        except Exception as exc:  # noqa: BLE001 — never let one request kill daemon
            log.exception("request failed")
            response = {
                "id": req_id,
                "ok": False,
                "error": {"type": "internal_error", "message": str(exc)},
            }
        with contextlib.suppress(OSError):
            conn.sendall(json.dumps(response, ensure_ascii=False).encode() + b"\n")

    def _dispatch(self, method: str, params: dict[str, Any]) -> Any:
        handlers = {
            "daemon.ping": lambda: {"pid": os.getpid()},
            "daemon.shutdown": self._shutdown,
            "player.status": self._status,
            "player.play": lambda: self._play(params),
            "player.pause": self._pause,
            "player.resume": self._resume,
            "player.toggle": self._toggle,
            "player.stop": self._stop,
            "player.next": lambda: self._next(params),
            "player.prev": lambda: self._prev(params),
            "player.volume": lambda: self._volume(params),
            "player.mode": lambda: self._mode(params),
            "player.seek": lambda: self._seek(params),
            "player.lyrics": lambda: self._lyrics(params),
            "queue.list": self._queue_list,
            "queue.add": lambda: self._queue_add(params),
            "queue.play": lambda: self._play({"index": params.get("index")}),
            "queue.clear": self._queue_clear,
        }
        handler = handlers.get(method)
        if handler is None:
            raise DaemonError("invalid_args", f"未知方法: {method}")
        result = handler()
        if method not in ("player.status", "queue.list", "daemon.ping"):
            with contextlib.suppress(Exception):
                self.storage.save()
        return result

    # -- handlers ----------------------------------------------------------

    def _shutdown(self) -> dict[str, Any]:
        self._running = False
        return {"stopped": True}

    def _status(self) -> dict[str, Any]:
        p = self.player
        song = p.current_song
        alive = bool(p.popen_handler and p.popen_handler.poll() is None)
        if p.is_empty or not p.is_index_valid:
            state = "stopped"
        elif alive:
            state = "playing" if p.playing_flag else "paused"
        else:
            state = "stopped"
        song_data: dict[str, Any] = {}
        if song:
            song_data = {
                "id": song.get("song_id"),
                "name": song.get("song_name"),
                "artist": song.get("artist"),
                "album": song.get("album_name"),
                "duration": song.get("duration"),
            }
        return {
            "state": state,
            "song": song_data,
            "position": round(float(p.process_location or 0), 1),
            "length": int(p.process_length or 0),
            "volume": p.info["playing_volume"],
            "mode": MODE_NAMES.get(p.mode, "ordered"),
            "backend": p.current_backend,
            "queue_index": p.index,
            "queue_size": len(p.list),
        }

    def _load_songs(self, song_ids: list[int]) -> list[dict[str, Any]]:
        songs = self.api.dig_info([{"id": sid} for sid in song_ids], "songs")
        return songs or []

    def _play(self, params: dict[str, Any]) -> dict[str, Any]:
        p = self.player
        playlist = params.get("playlist")
        song_id = params.get("id")
        index = params.get("index")
        if playlist is not None:
            track_ids = self.api.playlist_songlist(playlist)
            songs = self.api.dig_info(track_ids, "songs") or []
            if not songs:
                raise DaemonError("api_error", f"歌单 {playlist} 为空或不存在")
            p.new_player_list("songs", f"playlist-{playlist}", songs, -1)
            p.end_callback = None
            p.stop()
            p.info["idx"] = 0
            p.replay()
        elif song_id is not None:
            songs = self._load_songs([song_id])
            if not songs:
                raise DaemonError("api_error", f"歌曲 {song_id} 不可播放")
            p.new_player_list("songs", f"song-{song_id}", songs, -1)
            p.end_callback = None
            p.stop()
            p.info["idx"] = 0
            p.replay()
        elif index is not None:
            if index < 0 or index >= len(p.list):
                raise DaemonError(
                    "invalid_args",
                    f"索引 {index} 超出范围 (0-{max(len(p.list) - 1, 0)})",
                )
            p.stop()
            p.info["idx"] = index
            p.replay()
        else:
            if p.is_empty:
                raise DaemonError(
                    "invalid_args",
                    "播放队列为空",
                    "musicbox play --id <songid> 或 --playlist <id>",
                )
            if not p.popen_handler or p.popen_handler.poll() is not None:
                p.replay()
            elif not p.playing_flag:
                p.switch()
        return self._status()

    def _pause(self) -> dict[str, Any]:
        p = self.player
        if p.popen_handler and p.popen_handler.poll() is None and p.playing_flag:
            p.switch()
        return self._status()

    def _resume(self) -> dict[str, Any]:
        p = self.player
        if not p.popen_handler or p.popen_handler.poll() is not None:
            if not p.is_empty:
                p.replay()
        elif not p.playing_flag:
            p.switch()
        return self._status()

    def _toggle(self) -> dict[str, Any]:
        p = self.player
        if not p.popen_handler or p.popen_handler.poll() is not None:
            if not p.is_empty:
                p.replay()
        else:
            p.switch()
        return self._status()

    def _stop(self) -> dict[str, Any]:
        self.player.stop()
        return self._status()

    def _next(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.player.is_empty:
            raise DaemonError("invalid_args", "播放队列为空")
        for _ in range(max(int(params.get("n", 1) or 1), 1)):
            self.player.next()
        return self._status()

    def _prev(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.player.is_empty:
            raise DaemonError("invalid_args", "播放队列为空")
        for _ in range(max(int(params.get("n", 1) or 1), 1)):
            self.player.prev()
        return self._status()

    def _volume(self, params: dict[str, Any]) -> dict[str, Any]:
        if params.get("delta") is not None:
            self.player.tune_volume(int(params["delta"]))
        elif params.get("value") is not None:
            self.player.set_volume(int(params["value"]))
        else:
            raise DaemonError("invalid_args", "缺少音量值")
        return self._status()

    def _mode(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("mode", "")
        if name not in NAME_TO_MODE:
            raise DaemonError(
                "invalid_args",
                f"未知播放模式: {name}",
                "ordered|ordered-loop|single-loop|random|random-loop",
            )
        self.player.info["playing_mode"] = NAME_TO_MODE[name]
        return self._status()

    def _seek(self, params: dict[str, Any]) -> dict[str, Any]:
        p = self.player
        if not p.popen_handler or p.popen_handler.poll() is not None:
            raise DaemonError("invalid_args", "当前没有正在播放的歌曲")
        if p.current_backend != "mpv":
            raise DaemonError(
                "not_supported",
                "mpg123 后端不支持 seek",
                "将 player_backend 配置为 mpv，或播放无损以自动切换",
            )
        seconds = int(params.get("seconds", 0))
        relative = bool(params.get("relative", False))
        if not p.seek(seconds, relative):
            raise DaemonError("api_error", "seek 失败")
        return self._status()

    def _lyrics(self, params: dict[str, Any]) -> dict[str, Any]:
        p = self.player
        song_id = p.playing_id
        if not song_id:
            raise DaemonError("invalid_args", "当前没有正在播放的歌曲")
        lyric = self.api.song_lyric(song_id)
        tlyric = self.api.song_tlyric(song_id)
        return {
            "song_id": song_id,
            "name": p.playing_name,
            "lyric": lyric,
            "tlyric": tlyric,
        }

    def _queue_list(self) -> dict[str, Any]:
        p = self.player
        items = []
        for idx, sid in enumerate(p.list):
            song = p.songs.get(sid, {})
            items.append(
                {
                    "index": idx,
                    "song_id": song.get("song_id") or sid,
                    "name": song.get("song_name"),
                    "artist": song.get("artist"),
                    "current": idx == p.index,
                }
            )
        return {"items": items, "index": p.index, "size": len(p.list)}

    def _queue_add(self, params: dict[str, Any]) -> dict[str, Any]:
        ids = params.get("ids") or []
        if not ids:
            raise DaemonError("invalid_args", "缺少要添加的歌曲 ID")
        songs = self._load_songs([int(i) for i in ids])
        if not songs:
            raise DaemonError("api_error", "无法获取这些歌曲的信息")
        self.player.append_songs(songs)
        return self._queue_list()

    def _queue_clear(self) -> dict[str, Any]:
        self.player.stop()
        self.player.new_player_list("", "", [], -1)
        self.player.info["idx"] = 0
        return self._queue_list()


def _daemonize_and_serve() -> None:
    """Second-stage child: detach from controlling terminal and serve."""
    os.setsid()
    pid = os.fork()
    if pid > 0:
        os._exit(0)

    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    if devnull > 2:
        os.close(devnull)

    daemon = MusicboxDaemon()
    code = daemon.serve()
    os._exit(code)


def spawn_daemon(timeout: float = _READY_TIMEOUT) -> bool:
    """Double-fork a background daemon and wait until it is reachable."""
    if is_daemon_running():
        return True
    _ensure_runtime_dir()
    pid = os.fork()
    if pid == 0:
        try:
            _daemonize_and_serve()
        finally:
            os._exit(1)
    # Parent: reap the first child (which exits right after the second fork).
    with contextlib.suppress(OSError):
        os.waitpid(pid, 0)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_daemon_running():
            return True
        time.sleep(0.1)
    return False


def stop_daemon(timeout: float = 5.0) -> bool:
    if not is_daemon_running():
        return False
    with contextlib.suppress(ConnectionError, OSError, ValueError):
        send_request("daemon.shutdown", timeout=timeout)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not is_daemon_running():
            return True
        time.sleep(0.1)
    return not is_daemon_running()


def main(argv: list[str] | None = None) -> int:
    """Internal entrypoint: ``python -m NEMbox._daemon_serve`` style foreground run."""
    argv = argv if argv is not None else sys.argv[1:]
    daemon = MusicboxDaemon()
    return daemon.serve()


if __name__ == "__main__":
    sys.exit(main())
