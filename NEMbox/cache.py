# @Author: Catofes
# @Date:   2015-08-15
"""
Class to cache songs into local storage.
"""

import os
import signal
import subprocess
import threading
from urllib.parse import urlparse

from . import logger
from .api import LOSSLESS_LEVELS, NetEase, music_quality_to_level
from .config import Config
from .const import Constant
from .singleton import Singleton

log = logger.getLogger(__name__)


def infer_cache_extension(url="", song_type="", level="", configured_quality=None):
    if str(song_type or "").lower() == "flac":
        return ".flac"

    parsed_path = urlparse(url or "").path.lower()
    for ext in (".flac", ".mp3"):
        if parsed_path.endswith(ext):
            return ext

    normalized_level = str(level or "").lower()
    if normalized_level in LOSSLESS_LEVELS:
        return ".flac"

    if configured_quality is not None:
        configured_level = music_quality_to_level(configured_quality)
        if configured_level in LOSSLESS_LEVELS:
            return ".flac"

    return ".mp3"


class Cache(Singleton):
    def __init__(self):
        if hasattr(self, "_init"):
            return
        self._init = True

        self.const = Constant()
        self.config = Config()
        self.download_lock = threading.Lock()
        self.check_lock = threading.Lock()
        self.downloading = []
        self.aria2c = None
        self.wget = None
        self.stop = False
        self.enable = self.config.get("cache")
        self.aria2c_parameters = self.config.get("aria2c_parameters")

    def _is_cache_successful(self):
        def succ(x):
            return x and x.returncode == 0

        return succ(self.aria2c) or succ(self.wget)

    def _kill_all(self):
        def _kill(p):
            if p:
                os.kill(p.pid, signal.SIGKILL)

        _kill(self.aria2c)
        _kill(self.wget)

    def start_download(self):
        check = self.download_lock.acquire(False)
        if not check:
            return False
        while True:
            if self.stop:
                break
            if not self.enable:
                break
            self.check_lock.acquire()
            if len(self.downloading) <= 0:
                self.check_lock.release()
                break
            data = self.downloading.pop()
            self.check_lock.release()
            song_id = data[0]
            song_name = data[1]
            artist = data[2]
            url = data[3]
            onExit = data[4]
            song_type = data[5] if len(data) > 5 else ""
            level = data[6] if len(data) > 6 else ""
            output_path = Constant.download_dir
            ext = infer_cache_extension(
                url, song_type, level, self.config.get("music_quality")
            )
            output_file = str(artist) + " - " + str(song_name) + ext
            full_path = os.path.join(output_path, output_file)

            url_info = NetEase().songs_url([song_id])[0]
            new_url = url_info["url"]
            if not song_type:
                song_type = url_info.get("type", "")
            if not level:
                level = url_info.get("level", "")
            ext = infer_cache_extension(
                new_url, song_type, level, self.config.get("music_quality")
            )
            output_file = str(artist) + " - " + str(song_name) + ext
            full_path = os.path.join(output_path, output_file)
            if new_url:
                log.info(f"Old:{url}. New:{new_url}")
                try:
                    para = [
                        "aria2c",
                        "--auto-file-renaming=false",
                        "--allow-overwrite=true",
                        "-d",
                        output_path,
                        "-o",
                        output_file,
                        new_url,
                    ]
                    para.extend(self.aria2c_parameters)
                    log.debug(para)
                    self.aria2c = subprocess.Popen(
                        para,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self.aria2c.wait()
                except OSError as e:
                    log.warning(f"{e}.\tAria2c is unavailable, fall back to wget")

                    para = ["wget", "-O", full_path, new_url]
                    self.wget = subprocess.Popen(
                        para,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self.wget.wait()

                if self._is_cache_successful():
                    log.debug(str(song_id) + " Cache OK")
                    onExit(song_id, full_path)
        self.download_lock.release()

    def add(self, song_id, song_name, artist, url, onExit, song_type="", level=""):
        self.check_lock.acquire()
        self.downloading.append(
            [song_id, song_name, artist, url, onExit, song_type, level]
        )
        self.check_lock.release()

    def quit(self):
        self.stop = True
        try:
            self._kill_all()
        except (AttributeError, OSError) as e:
            log.error(e)
            pass
