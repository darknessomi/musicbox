# -*- coding: utf-8 -*-
# @Author: Catofes
# @Date:   2017-05-2
'''
Class to cache songs into local storage.
'''
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import str
from future import standard_library
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
from mutagen.easyid3 import EasyID3#新增u对元数据的编辑
standard_library.install_aliases()

import threading
import subprocess
import os
import signal

from .const import Constant
from .config import Config
from .singleton import Singleton
from .api import NetEase
from .utils import notify
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
            picurl = data[4]
            onExit = data[5]
            album = data[6]
            output_path = Constant.download_dir
            output_img_path = Constant.img_dir
            output_file = str(artist) + ' - ' + str(song_name) + '.mp3'
            output_img = str(artist) + ' - ' + str(album) + '.jpg'#新增封面下载
            output_file = output_file.replace('/',' ')
            output_img = output_img.replace('/',' ')
            full_path = os.path.join(output_path, output_file)
            full_img = os.path.join(output_img_path, output_img)
            if os.path.exists(full_path):
                if self.check_mp3(full_path,album) == False:
                    success=False
                    count=1
                    while success==False:
                        if os.path.exists(full_path) == True and self.check_mp3(full_path,album) == False:
                            output_file = str(artist) + ' - ' + str(song_name) + '(%s)'%count + '.mp3'
                            output_file=output_file.replace('/',' ')
                            full_path = os.path.join(output_path, output_file)
                        if os.path.exists(full_path) == False:
                            success=True
                            break
                        count+=1
            try:
                self._mkdir(output_img_path)
                new_url = NetEase().songs_detail_new_api([song_id])[0]['url']
                log.info('Old:{}. New:{}'.format(url, new_url))
                try:
                    if os.path.exists(full_img):
                        log.debug(str(full_img) + ' Exists')
                    else:
                        if picurl is not None:
                            para = ['aria2c', '--auto-file-renaming=false',
                                    '--allow-overwrite=true', '-d', output_img_path, '-o',
                                    output_img, picurl]
                            para[1:1] = self.aria2c_parameters
                            self.aria2c = subprocess.Popen(para,
                                                           stdin=subprocess.PIPE,
                                                           stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE)
                            self.aria2c.wait()
                    if os.path.exists(full_path):
                        log.debug(str(song_id) + ' Exists')
                        notify("%s 已经存在"%song_name)
                        self.save_mp3(full_path, full_img, song_name, artist, album, 1)
                        onExit(song_id, full_path)
                    else:
                        if new_url == None:
                            para = ['aria2c', '--auto-file-renaming=false',
                                    '--allow-overwrite=true', '-d', output_path, '-o',
                                    output_file, url]
                        else:
                            para = ['aria2c', '--auto-file-renaming=false',
                                '--allow-overwrite=true', '-d', output_path, '-o',
                                output_file, new_url]
                        para[1:1] = self.aria2c_parameters
                        self.aria2c = subprocess.Popen(para,
                                                       stdin=subprocess.PIPE,
                                                       stdout=subprocess.PIPE,
                                                       stderr=subprocess.PIPE)
                        self.aria2c.wait()
                        self.save_mp3(full_path, full_img, song_name, artist, album, 1)

                except OSError as e:
                    log.warning(
                        '{}.\tAria2c is unavailable, fall back to wget'.format(e))
                    notify("注意：\n使用Wget下载")
                    self._mkdir(output_path)
                    self._mkdir(output_img_path)
                    para = ['wget', '-O', full_img, picurl]
                    self.wget = subprocess.Popen(para,
                                                 stdin=subprocess.PIPE,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
                    self.wget.wait()
                    if os.path.exists(full_path):
                        log.debug(str(song_id) + ' Exists')
                        notify("%s 已经存在～"%song_name)
                        self.save_mp3(full_path, full_img)
                        onExit(song_id, full_path)
                    para = ['wget', '-O', full_path, new_url]
                    self.wget = subprocess.Popen(para,
                                                 stdin=subprocess.PIPE,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
                    self.wget.wait()
                    self.save_mp3(full_path, full_img, song_name, artist, album, 1)
                if self._is_cache_successful():
                    log.debug(str(song_id) + ' Cache OK')
                    notify("下载 %s 成功啦"%song_name)
                    onExit(song_id, full_path)
            except Exception as e:
                if os.path.exists(full_path):
                        log.debug(str(song_id) + ' Exists')
                        if os.path.exists(full_img):
                            self.save_mp3(full_path, full_img, song_name, artist, album, 1)
                            notify("%s 已经存在, 虽然没有网络，但是还是成功啦～"%song_name)
                        else:
                            self.save_mp3(full_path, full_img, song_name, artist, album, 0)
                            notify("%s 已经存在, 但是图片下载失败了"%song_name)
                        onExit(song_id, full_path)
                else:
                        notify('缓存失败...%s\n因为%s'%(song_name,e))
            
        self.download_lock.release()

    def add(self, song_id, song_name, artist, url, picurl, onExit, album):
        self.check_lock.acquire()
        self.downloading.append([song_id, song_name, artist, url, picurl, onExit, album])
        self.check_lock.release()

    def save_mp3(self, path_mp3, path_img, title, artist, album, img_save=True):
        if img_save:
            try:
                audio = MP3(path_mp3, ID3=ID3)
                # add ID3 tag if it doesn't exist
                try:
                    audio.add_tags()
                except error:
                    pass

                audio.tags.add(
                    APIC(
                        encoding = 3, # 3 is for utf-8
                        mime= u'image/jpeg', # image/jpeg or image/png
                        type = 3, # 3 is for the cover image
                        desc = u'Cover',
                        data = open(path_img, 'rb').read()
                    )
                )
                audio.save()
            except:
                pass
        try:
            audio = EasyID3(path_mp3)
            audio.clear()
            audio["title"] = title
            audio["artist"] = artist
            audio["album"] = album
            audio.save()
        except:
            pass

    def check_mp3(self, path_mp3, album):
        try:
            audio = EasyID3(path_mp3)
            if str(audio["album"][0]) == str(album):
                return True
        except:
            return True
        return False
        
    def quit(self):
        self.stop = True
        try:
            self._kill_all()
        except (AttributeError, OSError) as e:
            log.error(e)
            pass
