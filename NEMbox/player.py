#!/usr/bin/env python
# @Author: omi
# @Date:   2014-07-15 15:48:27
# @Last Modified by:   AlanAlbert
# @Last Modified time: 2018-11-21 14:00:00
"""
网易云音乐 Player
"""

from __future__ import annotations

# Let's make some noise
import json
import os
import random
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from typing import (  # noqa: UP035 — List avoids shadowing by @property list
    Any,
    List,
    cast,
)

from . import logger
from .api import NetEase
from .cache import Cache
from .config import Config
from .kill_thread import stop_thread
from .storage import Storage
from .ui import Ui
from .utils import notify

log = logger.getLogger(__name__)


class NullUi:
    """Headless UI stub for the daemon: every render call is a no-op.

    The real ``Ui`` grabs the terminal via ``curses.initscr()`` on construction,
    which must never happen inside ``musicboxd``.
    """

    def build_playinfo(self, *args, **kwargs):
        return None

    def update_size(self, *args, **kwargs):
        return None


class Player:
    MODE_ORDERED = 0
    MODE_ORDERED_LOOP = 1
    MODE_SINGLE_LOOP = 2
    MODE_RANDOM = 3
    MODE_RANDOM_LOOP = 4
    SUBPROCESS_LIST = []
    MUSIC_THREADS = []

    def __init__(self, ui=None):
        self.config = Config()
        self.ui = ui if ui is not None else Ui()
        self.popen_handler: Any = None
        self.current_backend = ""
        self.mpv_ipc_path = ""
        self.playback_token = 0
        # flag stop, prevent thread start
        self.playing_flag = False
        self.refresh_url_flag = False
        self.process_length = 0
        self.process_location = 0
        self.storage = Storage()
        self.cache = Cache()
        self.end_callback: Callable[[], None] | None = None
        self.playing_song_changed_callback: Callable[[], None] | None = None
        self.api = NetEase()
        self.playinfo_starts = time.time()

    @property
    def info(self) -> dict[str, Any]:
        return cast(dict[str, Any], self.storage.database["player_info"])

    @property
    def songs(self) -> dict[str, dict[str, Any]]:
        return cast(dict[str, dict[str, Any]], self.storage.database["songs"])

    @property
    def index(self):
        return self.info["idx"]

    @property
    def list(self) -> List[str]:  # noqa: UP006
        return cast(list[str], self.info["player_list"])

    @property
    def order(self) -> List[int]:  # noqa: UP006
        return cast(list[int], self.info["playing_order"])

    @property
    def mode(self):
        return self.info["playing_mode"]

    @property
    def is_ordered_mode(self):
        return self.mode == Player.MODE_ORDERED

    @property
    def is_ordered_loop_mode(self):
        return self.mode == Player.MODE_ORDERED_LOOP

    @property
    def is_single_loop_mode(self):
        return self.mode == Player.MODE_SINGLE_LOOP

    @property
    def is_random_mode(self):
        return self.mode == Player.MODE_RANDOM

    @property
    def is_random_loop_mode(self):
        return self.mode == Player.MODE_RANDOM_LOOP

    @property
    def config_notifier(self):
        return self.config.get("notifier")

    @property
    def config_mpg123(self):
        return self.config.get("mpg123_parameters")

    @property
    def config_mpv(self):
        return self.config.get("mpv_parameters")

    @property
    def current_song(self) -> dict[str, Any]:
        if not self.songs:
            return {}

        if not self.is_index_valid:
            return {}
        song_id = self.list[self.index]
        return self.songs.get(song_id, {})

    @property
    def playing_id(self):
        return self.current_song.get("song_id")

    @property
    def playing_name(self):
        return self.current_song.get("song_name")

    @property
    def is_empty(self):
        return len(self.list) == 0

    @property
    def is_index_valid(self):
        return 0 <= self.index < len(self.list)

    def notify_playing(self):
        if not self.current_song:
            return

        if not self.config_notifier:
            return

        song = self.current_song
        notify(
            "正在播放: {}\n{}-{}".format(
                song["song_name"], song["artist"], song["album_name"]
            )
        )

    def notify_copyright_issue(self):
        log.warning(f"Song {self.playing_id} is unavailable due to copyright issue.")
        notify("版权限制，无法播放此歌曲")

    def change_mode(self, step=1):
        self.info["playing_mode"] = (self.info["playing_mode"] + step) % 5

    def build_playinfo(self):
        if not self.current_song:
            return

        quality = self.current_song["quality"]
        audio_quality = self.current_song.get("audio_quality", "")
        if audio_quality and int(time.time() - self.playinfo_starts) % 6 >= 3:
            quality = audio_quality
        self.ui.build_playinfo(
            self.current_song["song_name"],
            self.current_song["artist"],
            self.current_song["album_name"],
            quality,
            self.playinfo_starts,
            pause=not self.playing_flag,
        )

    def add_songs(self, songs):
        for song in songs:
            song_id = str(song["song_id"])
            self.info["player_list"].append(song_id)
            if song_id in self.songs:
                self.songs[song_id].update(song)
            else:
                self.songs[song_id] = song

    def refresh_urls(self):
        songs = cast(list[dict[str, Any]], self.api.dig_info(self.list, "refresh_urls"))
        if songs:
            for song in songs:
                song_id = str(song["song_id"])
                if song_id in self.songs:
                    self.songs[song_id]["mp3_url"] = song["mp3_url"]
                    self.songs[song_id]["type"] = song.get("type", "")
                    self.songs[song_id]["level"] = song.get("level", "")
                    self.songs[song_id]["expires"] = song["expires"]
                    self.songs[song_id]["get_time"] = song["get_time"]
                else:
                    self.songs[song_id] = song
            self.refresh_url_flag = True

    def stop(self):
        if (
            not hasattr(self.popen_handler, "poll")
            or self.popen_handler.poll() is not None
        ):
            return

        self.playback_token += 1
        self.playing_flag = False
        try:
            if (
                self.current_backend == "mpg123"
                and self.popen_handler.poll() is None
                and self.popen_handler.stdin
                and not self.popen_handler.stdin.closed
            ):
                self.popen_handler.stdin.write(b"Q\n")
                self.popen_handler.stdin.flush()
                self.popen_handler.communicate()
                self.popen_handler.kill()
            elif self.popen_handler.poll() is None:
                self.popen_handler.terminate()
                try:
                    self.popen_handler.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.popen_handler.kill()
        except Exception as e:
            log.warn(e)
        finally:
            for thread_i in range(0, len(self.MUSIC_THREADS) - 1):
                if self.MUSIC_THREADS[thread_i].is_alive():
                    try:
                        stop_thread(self.MUSIC_THREADS[thread_i])
                    except Exception as e:
                        log.warn(e)
                        pass

    def tune_volume(self, up=0):
        new_volume = self.info["playing_volume"] + up
        if new_volume < 0:
            new_volume = 0
        self.info["playing_volume"] = new_volume
        if not self.popen_handler:
            return
        try:
            if self.popen_handler.poll() is not None:
                return
        except Exception as e:
            log.warn("Unable to tune volume: " + str(e))
            return
        if self.current_backend == "mpv":
            self._send_mpv_command(["set_property", "volume", new_volume])
            return
        try:
            self.popen_handler.stdin.write(f"V {new_volume}\n".encode())
            self.popen_handler.stdin.flush()
        except Exception as e:
            log.warn(e)

    def set_volume(self, volume):
        """Set absolute volume (0-100+). Persists to storage even when stopped."""
        volume = max(0, int(volume))
        self.info["playing_volume"] = volume
        if not self.popen_handler or self.popen_handler.poll() is not None:
            return
        if self.current_backend == "mpv":
            self._send_mpv_command(["set_property", "volume", volume])
            return
        try:
            self.popen_handler.stdin.write(f"V {volume}\n".encode())
            self.popen_handler.stdin.flush()
        except Exception as e:
            log.warn(e)

    def switch(self):
        if not self.popen_handler:
            return
        if self.popen_handler.poll() is not None:
            return
        if self.current_backend == "mpv":
            self.playing_flag = not self.playing_flag
            self._send_mpv_command(["set_property", "pause", not self.playing_flag])
            self.playinfo_starts = time.time()
            self.build_playinfo()
            return
        self.playing_flag = not self.playing_flag
        if not self.popen_handler.stdin.closed:
            self.popen_handler.stdin.write(b"P\n")
            self.popen_handler.stdin.flush()

        self.playinfo_starts = time.time()
        self.build_playinfo()

    @staticmethod
    def _is_flac_url(url):
        if not url:
            return False
        url_part = url.split("?", 1)[0].lower()
        return url_part.endswith(".flac") or ".flac/" in url_part

    @classmethod
    def _is_flac_song(cls, song, url):
        song_type = str(song.get("type") or "").lower()
        level = str(song.get("level") or "").lower()
        return bool(
            song_type == "flac"
            or level in {"lossless", "hires", "jymaster"}
            or cls._is_flac_url(url)
        )

    def _play_backend(self, song, url):
        backend = str(self.config.get("player_backend") or "mpg123").lower()
        if backend == "mpv" or self._is_flac_song(song, url):
            return "mpv"
        return "mpg123"

    def _new_mpv_ipc_path(self):
        return os.path.join(
            tempfile.gettempdir(), f"musicbox-mpv-{os.getpid()}-{id(self)}.sock"
        )

    def _cleanup_mpv_ipc(self, path=None):
        path = path if path is not None else getattr(self, "mpv_ipc_path", "")
        if not path:
            return
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        except OSError as e:
            log.warn(e)
        if path == getattr(self, "mpv_ipc_path", ""):
            self.mpv_ipc_path = ""

    def _is_current_playback(self, token, process=None):
        if token != self.playback_token:
            return False
        return not (process is not None and self.popen_handler is not process)

    def _send_mpv_command(self, command):
        path = getattr(self, "mpv_ipc_path", "")
        if not path:
            return False
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(path)
                payload = json.dumps({"command": command}).encode() + b"\n"
                client.sendall(payload)
            return True
        except OSError as e:
            log.warn(e)
            return False

    def _request_mpv_property(self, name, path=None):
        path = path or getattr(self, "mpv_ipc_path", "")
        if not path:
            return None
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(0.2)
                client.connect(path)
                payload = json.dumps({"command": ["get_property", name]}).encode()
                client.sendall(payload + b"\n")
                data = b""
                while b"\n" not in data:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            if not data:
                return None
            response = json.loads(data.split(b"\n", 1)[0].decode())
            if response.get("error") == "success":
                return response.get("data")
        except (OSError, ValueError):
            pass
        return None

    @staticmethod
    def _format_sample_rate(rate):
        if not rate:
            return ""
        khz = float(rate) / 1000
        text = f"{khz:.1f}".rstrip("0").rstrip(".")
        return f"{text}kHz"

    @staticmethod
    def _format_sample_bits(fmt):
        fmt = str(fmt or "").lower()
        if fmt == "float":
            return "32bit"
        if fmt == "double":
            return "64bit"
        digits = "".join(ch for ch in fmt if ch.isdigit())
        return f"{digits}bit" if digits else ""

    @classmethod
    def _format_audio_params(cls, params):
        if not isinstance(params, dict):
            return ""
        parts = [
            cls._format_sample_rate(params.get("samplerate")),
            cls._format_sample_bits(params.get("format")),
        ]
        return " ".join(part for part in parts if part)

    def _refresh_mpv_audio_info(self, ipc_path, token, process):
        if not self._is_current_playback(token, process):
            return False
        label = self._format_audio_params(
            self._request_mpv_property("audio-params", ipc_path)
        )
        if not label:
            return False
        song = self.current_song
        if not song:
            return False
        song["audio_quality"] = label
        return True

    def run_mpv(self, on_exit, url, expires=-1, get_time=-1, duration=0, token=0):
        self.current_backend = "mpv"
        if not url:
            self.notify_copyright_issue()
            if not self.is_single_loop_mode:
                self.next()
            else:
                self.stop()
            return

        self._cleanup_mpv_ipc()
        ipc_path = self._new_mpv_ipc_path()
        self.mpv_ipc_path = ipc_path
        para = (
            [
                "mpv",
                "--no-video",
                "--really-quiet",
                f"--input-ipc-server={ipc_path}",
                f"--volume={self.info['playing_volume']}",
            ]
            + self.config_mpv
            + [url]
        )
        try:
            process = subprocess.Popen(
                para,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.popen_handler = process
            self.process_length = max(int(duration or 0), 1)
            self.process_location = 0
            last_tick = time.time()
            audio_info_loaded = False
            while process.poll() is None:
                now = time.time()
                is_current = self._is_current_playback(token, process)
                if self.playing_flag and is_current:
                    self.process_location = min(
                        self.process_location + now - last_tick,
                        self.process_length,
                    )
                    if not audio_info_loaded:
                        audio_info_loaded = self._refresh_mpv_audio_info(
                            ipc_path, token, process
                        )
                last_tick = now
                time.sleep(0.2)
        except OSError as e:
            log.error(e)
            notify("mpv 不可用，无法播放无损音频")
            self.playing_flag = False
            self._cleanup_mpv_ipc(ipc_path)
            return
        self._cleanup_mpv_ipc(ipc_path)

        if not self.playing_flag or not self._is_current_playback(token, process):
            return
        if process.returncode == 0:
            self.next()
            return
        if expires >= 0 and get_time >= 0 and time.time() - expires - get_time >= 0:
            self.refresh_urls()
            if self.refresh_url_flag:
                self.stop()
                self.playing_flag = True
                self.start_playing(lambda: 0, self.current_song)
                self.refresh_url_flag = False
            return
        self.notify_copyright_issue()
        if self.is_single_loop_mode:
            self.stop()
        else:
            self.next()

    def run_mpg123(self, on_exit, url, expires=-1, get_time=-1):
        self.current_backend = "mpg123"
        para = ["mpg123", "-R"] + self.config_mpg123
        self.popen_handler = subprocess.Popen(
            para, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if not url:
            self.notify_copyright_issue()
            if not self.is_single_loop_mode:
                self.next()
            else:
                self.stop()
            return

        self.tune_volume()
        try:
            self.popen_handler.stdin.write(b"L " + url.encode("utf-8") + b"\n")
            self.popen_handler.stdin.flush()
        except Exception:
            pass

        strout = " "
        copyright_issue_flag = False
        frame_cnt = 0
        while True:
            # Check the handler/stdin/stdout
            if not hasattr(self.popen_handler, "poll") or self.popen_handler.poll():
                break
            if self.popen_handler.stdout.closed:
                break

            # try to read the stdout of mpg123
            try:
                stroutlines = self.popen_handler.stdout.readline()
            except Exception as e:
                log.warn(e)
                break
            if not stroutlines:
                strout = " "
                break
            else:
                strout_new = stroutlines.decode().strip()
                if strout_new[:2] != strout[:2]:
                    # if status of mpg123 changed
                    for thread_i in range(0, len(self.MUSIC_THREADS) - 1):
                        if self.MUSIC_THREADS[thread_i].is_alive():
                            try:
                                stop_thread(self.MUSIC_THREADS[thread_i])
                            except Exception as e:
                                log.warn(e)

                strout = strout_new

            # Update application status according to mpg123 output
            if strout[:2] == "@F":
                # playing, update progress
                out = strout.split(" ")
                frame_cnt += 1
                self.process_location = float(out[3])
                self.process_length = int(float(out[3]) + float(out[4]))
            elif strout[:2] == "@E":
                self.playing_flag = True
                if (
                    expires >= 0
                    and get_time >= 0
                    and time.time() - expires - get_time >= 0
                ):
                    # 刷新URL，设 self.refresh_url_flag = True
                    self.refresh_urls()
                else:
                    # copyright issue raised, next if not single loop
                    copyright_issue_flag = True
                    self.notify_copyright_issue()
                break
            elif strout == "@P 0" and frame_cnt:
                # normally end, moving to next
                self.playing_flag = True
                copyright_issue_flag = False
                break
            elif strout == "@P 0":
                # copyright issue raised, next if not single loop
                self.playing_flag = True
                copyright_issue_flag = True
                self.notify_copyright_issue()
                break

        # Ideal behavior:
        # if refresh_url_flag are set, then replay.
        # if not, do action like following:
        #   [self.playing_flag, copyright_issue_flag, self.is_single_loop_mode]: function()
        #       [0, 0, 0]: self.stop()
        #       [0, 0, 1]: self.stop()
        #       [0, 1, 0]: self.stop()
        #       [0, 1, 1]: self.stop()
        #       [1, 0, 0]: self.next()
        #       [1, 0, 1]: self.next()
        #       [1, 1, 0]: self.next()
        #       [1, 1, 1]: self.stop()

        # Do corresponding action according to status
        if self.playing_flag and self.refresh_url_flag:
            self.stop()  # Will set self.playing_flag = False
            # So set the playing_flag here to be True is necessary
            # to keep the play/pause status right
            self.playing_flag = True
            self.start_playing(lambda: 0, self.current_song)
            self.refresh_url_flag = False
        else:
            # When no replay are needed
            if (
                not self.playing_flag
                or copyright_issue_flag
                and self.is_single_loop_mode
            ):
                self.stop()
            else:
                self.next()

    def download_lyric(self, is_transalted=False):
        key = "lyric" if not is_transalted else "tlyric"

        if key not in self.songs[str(self.playing_id)]:
            self.songs[str(self.playing_id)][key] = []

        if len(self.songs[str(self.playing_id)][key]) > 0:
            return

        if not is_transalted:
            lyric = self.api.song_lyric(self.playing_id)
        else:
            lyric = self.api.song_tlyric(self.playing_id)

        self.songs[str(self.playing_id)][key] = lyric

    def download_song(self, song_id, song_name, artist, url, song_type="", level=""):
        def write_path(song_id, path):
            self.songs[str(song_id)]["cache"] = path

        self.cache.add(song_id, song_name, artist, url, write_path, song_type, level)
        self.cache.start_download()

    def start_playing(self, on_exit, args):
        """
        Runs the given args in subprocess.Popen, and then calls the function
        on_exit when the subprocess completes.
        on_exit is a callable object, and args is a lists/tuple of args
        that would give to subprocess.Popen.
        """
        # print(args.get('cache'))
        url = (
            args["cache"]
            if "cache" in args and os.path.isfile(args["cache"])
            else args["mp3_url"]
        )
        backend = self._play_backend(args, url)
        runner = self.run_mpv if backend == "mpv" else self.run_mpg123
        self.playback_token += 1
        token = self.playback_token
        if "cache" in args and os.path.isfile(args["cache"]):
            if backend == "mpv":
                thread = threading.Thread(
                    target=runner,
                    args=(
                        on_exit,
                        args["cache"],
                        -1,
                        -1,
                        args.get("duration", 0),
                        token,
                    ),
                )
            else:
                thread = threading.Thread(target=runner, args=(on_exit, args["cache"]))
        else:
            player_args = (on_exit, args["mp3_url"], args["expires"], args["get_time"])
            if backend == "mpv":
                player_args = (*player_args, args.get("duration", 0), token)
            thread = threading.Thread(
                target=runner,
                args=player_args,
            )
            cache_thread = threading.Thread(
                target=self.download_song,
                args=(
                    args["song_id"],
                    args["song_name"],
                    args["artist"],
                    args["mp3_url"],
                    args.get("type", ""),
                    args.get("level", ""),
                ),
            )
            cache_thread.start()
        thread.start()
        self.MUSIC_THREADS.append(thread)
        self.MUSIC_THREADS = [i for i in self.MUSIC_THREADS if i.is_alive()]
        lyric_download_thread = threading.Thread(target=self.download_lyric)
        lyric_download_thread.start()
        tlyric_download_thread = threading.Thread(
            target=self.download_lyric, args=(True,)
        )
        tlyric_download_thread.start()
        # returns immediately after the thread starts
        return thread

    def replay(self):
        if not self.is_index_valid:
            self.stop()
            if self.end_callback:
                log.debug("Callback")
                self.end_callback()
            return

        if not self.current_song:
            return

        self.playing_flag = True
        self.playinfo_starts = time.time()
        self.build_playinfo()
        self.notify_playing()
        self.start_playing(lambda: 0, self.current_song)

    def shuffle_order(self):
        del self.order[:]
        self.order.extend(list(range(0, len(self.list))))
        random.shuffle(self.order)
        self.info["random_index"] = 0

    def new_player_list(self, type, title, datalist, offset):
        self.info["player_list_type"] = type
        self.info["player_list_title"] = title
        # self.info['idx'] = offset
        self.info["player_list"] = []
        self.info["playing_order"] = []
        self.info["random_index"] = 0
        self.add_songs(datalist)

    def append_songs(self, datalist):
        self.add_songs(datalist)

    # switch_flag为true表示：
    # 在播放列表中 || 当前所在列表类型不在"songs"、"djprograms"、"fmsongs"中
    def play_or_pause(self, idx, switch_flag):
        if self.is_empty:
            return

        # if same "list index" and "playing index" --> same song :: pause/resume it
        if self.index == idx and switch_flag:
            if not self.popen_handler:
                self.replay()
            else:
                self.switch()
        else:
            self.info["idx"] = idx
            self.stop()
            self.replay()

    def _swap_song(self):
        now_songs = self.order.index(self.index)
        self.order[0], self.order[now_songs] = self.order[now_songs], self.order[0]

    def _need_to_shuffle(self):
        playing_order = self.order
        random_index = self.info["random_index"]
        return bool(
            random_index >= len(playing_order)
            or playing_order[random_index] != self.index
        )

    def next_idx(self):
        if not self.is_index_valid:
            return self.stop()
        playlist_len = len(self.list)

        if self.mode == Player.MODE_ORDERED:
            # make sure self.index will not over
            if self.info["idx"] < playlist_len:
                self.info["idx"] += 1

        elif self.mode == Player.MODE_ORDERED_LOOP:
            self.info["idx"] = (self.index + 1) % playlist_len

        elif self.mode == Player.MODE_SINGLE_LOOP:
            self.info["idx"] = self.info["idx"]

        else:
            playing_order_len = len(self.order)
            if self._need_to_shuffle():
                self.shuffle_order()
                # When you regenerate playing list
                # you should keep previous song same.
                self._swap_song()
                playing_order_len = len(self.order)

            self.info["random_index"] += 1

            # Out of border
            if self.mode == Player.MODE_RANDOM_LOOP:
                self.info["random_index"] %= playing_order_len

            # Random but not loop, out of border, stop playing.
            if self.info["random_index"] >= playing_order_len:
                self.info["idx"] = playlist_len
            else:
                self.info["idx"] = self.order[self.info["random_index"]]

        if self.playing_song_changed_callback is not None:
            self.playing_song_changed_callback()

    def next(self):
        self.stop()
        self.next_idx()
        self.replay()

    def prev_idx(self):
        if not self.is_index_valid:
            self.stop()
            return
        playlist_len = len(self.list)

        if self.mode == Player.MODE_ORDERED:
            if self.info["idx"] > 0:
                self.info["idx"] -= 1

        elif self.mode == Player.MODE_ORDERED_LOOP:
            self.info["idx"] = (self.info["idx"] - 1) % playlist_len

        elif self.mode == Player.MODE_SINGLE_LOOP:
            self.info["idx"] = self.info["idx"]

        else:
            playing_order_len = len(self.order)
            if self._need_to_shuffle():
                self.shuffle_order()
                playing_order_len = len(self.order)

            self.info["random_index"] -= 1
            if self.info["random_index"] < 0:
                if self.mode == Player.MODE_RANDOM:
                    self.info["random_index"] = 0
                else:
                    self.info["random_index"] %= playing_order_len
            self.info["idx"] = self.order[self.info["random_index"]]

        if self.playing_song_changed_callback is not None:
            self.playing_song_changed_callback()

    def prev(self):
        self.stop()
        self.prev_idx()
        self.replay()

    def shuffle(self):
        self.stop()
        self.info["playing_mode"] = Player.MODE_RANDOM
        self.shuffle_order()
        self.info["idx"] = self.info["playing_order"][self.info["random_index"]]
        self.replay()

    def seek(self, position, relative=False):
        """Seek the current track. Returns True on success.

        Only mpv (which exposes an IPC ``seek`` command) is supported;
        mpg123 streaming has no reliable second->frame mapping, so the daemon
        surfaces a structured ``not_supported`` for it.
        """
        if not self.popen_handler or self.popen_handler.poll() is not None:
            return False
        if self.current_backend != "mpv":
            return False
        mode = "relative" if relative else "absolute"
        if not self._send_mpv_command(["seek", position, mode]):
            return False
        if relative:
            self.process_location = max(
                0, min(self.process_location + position, self.process_length)
            )
        else:
            self.process_location = max(0, min(position, self.process_length))
        return True

    def volume_up(self):
        self.tune_volume(5)

    def volume_down(self):
        self.tune_volume(-5)

    def update_size(self):
        self.ui.update_size()
        self.build_playinfo()

    def cache_song(self, song_id, song_name, artist, song_url, song_type="", level=""):
        def on_exit(song_id, path):
            self.songs[str(song_id)]["cache"] = path
            self.cache.enable = False

        self.cache.enable = True
        self.cache.add(song_id, song_name, artist, song_url, on_exit, song_type, level)
        self.cache.start_download()
