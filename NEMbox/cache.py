# -*- coding: utf-8 -*-
# @Author: Catofes
# @Date:   2015-08-15


'''
Class to cache songs into local storage.
'''

from storage import Singleton
import threading
import subprocess
from const import Constant
import os
import logger
import signal
from storage import Storage

log = logger.getLogger(__name__)


class Cache(Singleton):
    def __init__(self):
        if hasattr(self, '_init'):
            return
        self._init = True
        self.const = Constant()
        self.download_lock = threading.Lock()
        self.check_lock = threading.Lock()
        self.downloading = []
        self.aria2c = None
        self.stop = False
        self.enable = Storage().database['cache']

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
            url = data[1]
            onExit = data[2]
            output_path = Constant.download_dir
            output_file = str(song_id) + ".mp3"
            try:
                self.aria2c = subprocess.Popen(
                    ['aria2c', '--auto-file-renaming=false', '--allow-overwrite=true', '-d', output_path, '-o',
                     output_file, url],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
                self.aria2c.wait()
            except Exception:
                log.debug(str(song_id) + " Cache Error")
            if self.aria2c.returncode == 0:
                log.debug(str(song_id) + " Cache OK")
                onExit(song_id, output_path + "/" + output_file)
        self.download_lock.release()


    def add(self, song_id, url, onExit):
        self.check_lock.acquire()
        self.downloading.append([song_id, url, onExit])
        self.check_lock.release()

    def quit(self):
        self.stop = True
        try:
            os.kill(self.aria2c.pid, signal.SIGKILL)
        except:
            pass

