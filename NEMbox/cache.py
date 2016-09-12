# -*- coding: utf-8 -*-
# @Author: Catofes
# @Date:   2015-08-15
'''
Class to cache songs into local storage.
'''
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import str
from future import standard_library
standard_library.install_aliases()

import threading
import subprocess
import os
import signal

from .const import Constant
from .config import Config
from .singleton import Singleton
from .api import NetEase
from . import logger

log = logger.getLogger(__name__)


class Cache(Singleton):

    def __init__(self):
        if hasattr(self, '_init'):
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
        self.enable = self.config.get_item('cache')
        self.aria2c_parameters = self.config.get_item('aria2c_parameters')

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

    def _mkdir(self, name):
        try:
            os.mkdir(name)
        except OSError:
            pass

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
            output_path = Constant.download_dir
            output_file = str(artist) + ' - ' + str(song_name) + '.mp3'
            full_path = os.path.join(output_path, output_file)

            new_url = NetEase().songs_detail_new_api([song_id])[0]['url']
            log.info('Old:{}. New:{}'.format(url, new_url))
            try:
                para = ['aria2c', '--auto-file-renaming=false',
                        '--allow-overwrite=true', '-d', output_path, '-o',
                        output_file, new_url]
                para[1:1] = self.aria2c_parameters
                self.aria2c = subprocess.Popen(para,
                                               stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE)
                self.aria2c.wait()
            except OSError as e:
                log.warning(
                    '{}.\tAria2c is unavailable, fall back to wget'.format(e))

                self._mkdir(output_path)
                para = ['wget', '-O', full_path, new_url]
                self.wget = subprocess.Popen(para,
                                             stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
                self.wget.wait()

            if self._is_cache_successful():
                log.debug(str(song_id) + ' Cache OK')
                onExit(song_id, full_path)
        self.download_lock.release()

    def add(self, song_id, song_name, artist, url, onExit):
        self.check_lock.acquire()
        self.downloading.append([song_id, song_name, artist, url, onExit])
        self.check_lock.release()

    def quit(self):
        self.stop = True
        try:
            self._kill_all()
        except (AttributeError, OSError) as e:
            log.error(e)
            pass
