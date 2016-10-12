#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-07-15 15:48:27
# @Last Modified by:   omi
# @Last Modified time: 2015-01-30 18:05:08
'''
网易云音乐 Player
'''
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import range
from builtins import str
from future import standard_library
standard_library.install_aliases()
# Let's make some noise

import subprocess
import threading
import time
import os
import random
import re

from .ui import Ui
from .storage import Storage
from .api import NetEase
from .cache import Cache
from .config import Config
from . import logger

log = logger.getLogger(__name__)


class Player(object):

    def __init__(self):
        self.config = Config()
        self.ui = Ui()
        self.popen_handler = None
        # flag stop, prevent thread start
        self.playing_flag = False
        self.pause_flag = False
        self.process_length = 0
        self.process_location = 0
        self.process_first = False
        self.storage = Storage()
        self.info = self.storage.database['player_info']
        self.songs = self.storage.database['songs']
        self.playing_id = -1
        self.playing_name = ''
        self.cache = Cache()
        self.notifier = self.config.get_item('notifier')
        self.mpg123_parameters = self.config.get_item('mpg123_parameters')
        self.end_callback = None
        self.playing_song_changed_callback = None

    def popen_recall(self, onExit, popenArgs):
        '''
        Runs the given args in subprocess.Popen, and then calls the function
        onExit when the subprocess completes.
        onExit is a callable object, and popenArgs is a lists/tuple of args
        that would give to subprocess.Popen.
        '''

        def runInThread(onExit, arg):
            para = ['mpg123', '-R']
            para[1:1] = self.mpg123_parameters
            self.popen_handler = subprocess.Popen(para,
                                                  stdin=subprocess.PIPE,
                                                  stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE)
            self.popen_handler.stdin.write(b'V ' + str(self.info['playing_volume']).encode('u8') + b'\n')
            if arg:
                self.popen_handler.stdin.write(b'L ' + arg.encode('u8') + b'\n')
            else:
                self.next_idx()
                onExit()
                return

            self.popen_handler.stdin.flush()

            self.process_first = True
            while True:
                if self.playing_flag is False:
                    break

                strout = self.popen_handler.stdout.readline().decode('u8')

                if re.match('^\@F.*$', strout):
                    process_data = strout.split(' ')
                    process_location = float(process_data[4])
                    if self.process_first:
                        self.process_length = process_location
                        self.process_first = False
                        self.process_location = 0
                    else:
                        self.process_location = self.process_length - process_location  # NOQA
                    continue
                elif strout[:2] == '@E':
                    # get a alternative url from new api
                    sid = popenArgs['song_id']
                    new_url = NetEase().songs_detail_new_api([sid])[0]['url']
                    if new_url is None:
                        log.warning(('Song {} is unavailable '
                                     'due to copyright issue').format(sid))
                        break
                    log.warning(
                        'Song {} is not compatible with old api.'.format(sid))
                    popenArgs['mp3_url'] = new_url

                    self.popen_handler.stdin.write(b'\nL ' + new_url.encode('u8') + b'\n')
                    self.popen_handler.stdin.flush()
                    self.popen_handler.stdout.readline()
                elif strout == '@P 0\n':
                    self.popen_handler.stdin.write(b'Q\n')
                    self.popen_handler.stdin.flush()
                    self.popen_handler.kill()
                    break

            if self.playing_flag:
                self.next_idx()
                onExit()
            return

        def getLyric():
            if 'lyric' not in self.songs[str(self.playing_id)].keys():
                self.songs[str(self.playing_id)]['lyric'] = []
            if len(self.songs[str(self.playing_id)]['lyric']) > 0:
                return
            netease = NetEase()
            lyric = netease.song_lyric(self.playing_id)
            if lyric == [] or lyric == '未找到歌词':
                return
            lyric = lyric.split('\n')
            self.songs[str(self.playing_id)]['lyric'] = lyric
            return

        def gettLyric():
            if 'tlyric' not in self.songs[str(self.playing_id)].keys():
                self.songs[str(self.playing_id)]['tlyric'] = []
            if len(self.songs[str(self.playing_id)]['tlyric']) > 0:
                return
            netease = NetEase()
            tlyric = netease.song_tlyric(self.playing_id)
            if tlyric == [] or tlyric == '未找到歌词翻译':
                return
            tlyric = tlyric.split('\n')
            self.songs[str(self.playing_id)]['tlyric'] = tlyric
            return

        def cacheSong(song_id, song_name, artist, song_url):
            def cacheExit(song_id, path):
                self.songs[str(song_id)]['cache'] = path

            self.cache.add(song_id, song_name, artist, song_url, cacheExit)
            self.cache.start_download()

        if 'cache' in popenArgs.keys() and os.path.isfile(popenArgs['cache']):
            thread = threading.Thread(target=runInThread,
                                      args=(onExit, popenArgs['cache']))
        else:
            thread = threading.Thread(target=runInThread,
                                      args=(onExit, popenArgs['mp3_url']))
            cache_thread = threading.Thread(
                target=cacheSong,
                args=(popenArgs['song_id'], popenArgs['song_name'], popenArgs[
                    'artist'], popenArgs['mp3_url']))
            cache_thread.start()
        thread.start()
        lyric_download_thread = threading.Thread(target=getLyric, args=())
        lyric_download_thread.start()
        tlyric_download_thread = threading.Thread(target=gettLyric, args=())
        tlyric_download_thread.start()
        # returns immediately after the thread starts
        return thread

    def get_playing_id(self):
        return self.playing_id

    def get_playing_name(self):
        return self.playing_name

    def recall(self):
        if self.info['idx'] >= len(self.info[
                'player_list']) and self.end_callback is not None:
            log.debug('Callback')
            self.end_callback()
        if self.info['idx'] < 0 or self.info['idx'] >= len(self.info[
                'player_list']):
            self.info['idx'] = 0
            self.stop()
            return
        self.playing_flag = True
        self.pause_flag = False
        item = self.songs[self.info['player_list'][self.info['idx']]]
        self.ui.build_playinfo(item['song_name'], item['artist'],
                               item['album_name'], item['quality'],
                               time.time())
        if self.notifier:
            self.ui.notify('Now playing', item['song_name'],
                           item['album_name'], item['artist'])
        self.playing_id = item['song_id']
        self.playing_name = item['song_name']
        self.popen_recall(self.recall, item)

    def generate_shuffle_playing_list(self):
        del self.info['playing_list'][:]
        for i in range(0, len(self.info['player_list'])):
            self.info['playing_list'].append(i)
        random.shuffle(self.info['playing_list'])
        self.info['ridx'] = 0

    def new_player_list(self, type, title, datalist, offset):
        self.info['player_list_type'] = type
        self.info['player_list_title'] = title
        self.info['idx'] = offset
        del self.info['player_list'][:]
        del self.info['playing_list'][:]
        self.info['ridx'] = 0
        for song in datalist:
            self.info['player_list'].append(str(song['song_id']))
            if str(song['song_id']) not in self.songs.keys():
                self.songs[str(song['song_id'])] = song
            else:
                database_song = self.songs[str(song['song_id'])]
                if (database_song['song_name'] != song['song_name'] or
                        database_song['quality'] != song['quality']):
                    self.songs[str(song['song_id'])] = song

    def append_songs(self, datalist):
        for song in datalist:
            self.info['player_list'].append(str(song['song_id']))
            if str(song['song_id']) not in self.songs.keys():
                self.songs[str(song['song_id'])] = song
            else:
                database_song = self.songs[str(song['song_id'])]
                cond = any([database_song[k] != song[k]
                            for k in ('song_name', 'quality', 'mp3_url')])
                if cond:
                    if 'cache' in self.songs[str(song['song_id'])].keys():
                        song['cache'] = self.songs[str(song['song_id'])][
                            'cache']
                    self.songs[str(song['song_id'])] = song
        if len(datalist) > 0 and self.info['playing_mode'] == 3 or self.info[
                'playing_mode'] == 4:
            self.generate_shuffle_playing_list()

    def play_and_pause(self, idx):
        # if same playlists && idx --> same song :: pause/resume it
        if self.info['idx'] == idx:
            if self.pause_flag:
                self.resume()
            else:
                self.pause()
        else:
            self.info['idx'] = idx

            # if it's playing
            if self.playing_flag:
                self.switch()

            # start new play
            else:
                self.recall()

    # play another
    def switch(self):
        self.stop()
        # wait process be killed
        time.sleep(0.1)
        self.recall()

    def stop(self):
        if self.playing_flag and self.popen_handler:
            self.playing_flag = False
            self.popen_handler.stdin.write(b'Q\n')
            self.popen_handler.stdin.flush()
            try:
                self.popen_handler.kill()
            except OSError as e:
                log.error(e)
                return

    def pause(self):
        if not self.playing_flag and not self.popen_handler:
            return
        self.pause_flag = True
        self.popen_handler.stdin.write(b'P\n')
        self.popen_handler.stdin.flush()

        item = self.songs[self.info['player_list'][self.info['idx']]]
        self.ui.build_playinfo(item['song_name'],
                               item['artist'],
                               item['album_name'],
                               item['quality'],
                               time.time(),
                               pause=True)

    def resume(self):
        self.pause_flag = False
        self.popen_handler.stdin.write(b'P\n')
        self.popen_handler.stdin.flush()

        item = self.songs[self.info['player_list'][self.info['idx']]]
        self.ui.build_playinfo(item['song_name'], item['artist'],
                               item['album_name'], item['quality'],
                               time.time())
        self.playing_id = item['song_id']
        self.playing_name = item['song_name']

    def _swap_song(self):
        plist = self.info['playing_list']
        now_songs = plist.index(self.info['idx'])
        plist[0], plist[now_songs] = plist[now_songs], plist[0]

    def _is_idx_valid(self):
        return 0 <= self.info['idx'] < len(self.info['player_list'])

    def _inc_idx(self):
        if self.info['idx'] < len(self.info['player_list']):
            self.info['idx'] += 1

    def _dec_idx(self):
        if self.info['idx'] > 0:
            self.info['idx'] -= 1

    def _need_to_shuffle(self):
        playing_list = self.info['playing_list']
        ridx = self.info['ridx']
        idx = self.info['idx']
        if ridx >= len(playing_list) or playing_list[ridx] != idx:
            return True
        else:
            return False

    def next_idx(self):
        if not self._is_idx_valid():
            self.stop()
            return
        playlist_len = len(self.info['player_list'])
        playinglist_len = len(self.info['playing_list'])

        # Playing mode. 0 is ordered. 1 is orderde loop.
        # 2 is single song loop. 3 is single random. 4 is random loop
        if self.info['playing_mode'] == 0:
            self._inc_idx()
        elif self.info['playing_mode'] == 1:
            self.info['idx'] = (self.info['idx'] + 1) % playlist_len
        elif self.info['playing_mode'] == 2:
            self.info['idx'] = self.info['idx']
        elif self.info['playing_mode'] == 3 or self.info['playing_mode'] == 4:
            if self._need_to_shuffle():
                self.generate_shuffle_playing_list()
                playinglist_len = len(self.info['playing_list'])
                # When you regenerate playing list
                # you should keep previous song same.
                try:
                    self._swap_song()
                except Exception as e:
                    log.error(e)
            self.info['ridx'] += 1
            # Out of border
            if self.info['playing_mode'] == 4:
                self.info['ridx'] %= playinglist_len
            if self.info['ridx'] >= playinglist_len:
                self.info['idx'] = playlist_len
            else:
                self.info['idx'] = self.info['playing_list'][self.info['ridx']]
        else:
            self.info['idx'] += 1
        if self.playing_song_changed_callback is not None:
            self.playing_song_changed_callback()

    def next(self):
        self.stop()
        time.sleep(0.01)
        self.next_idx()
        self.recall()

    def prev_idx(self):
        if not self._is_idx_valid():
            self.stop()
            return
        playlist_len = len(self.info['player_list'])
        playinglist_len = len(self.info['playing_list'])
        # Playing mode. 0 is ordered. 1 is orderde loop.
        # 2 is single song loop. 3 is single random. 4 is random loop
        if self.info['playing_mode'] == 0:
            self._dec_idx()
        elif self.info['playing_mode'] == 1:
            self.info['idx'] = (self.info['idx'] - 1) % playlist_len
        elif self.info['playing_mode'] == 2:
            self.info['idx'] = self.info['idx']
        elif self.info['playing_mode'] == 3 or self.info['playing_mode'] == 4:
            if self._need_to_shuffle():
                self.generate_shuffle_playing_list()
                playinglist_len = len(self.info['playing_list'])
            self.info['ridx'] -= 1
            if self.info['ridx'] < 0:
                if self.info['playing_mode'] == 3:
                    self.info['ridx'] = 0
                else:
                    self.info['ridx'] %= playinglist_len
            self.info['idx'] = self.info['playing_list'][self.info['ridx']]
        else:
            self.info['idx'] -= 1
        if self.playing_song_changed_callback is not None:
            self.playing_song_changed_callback()

    def prev(self):
        self.stop()
        time.sleep(0.01)
        self.prev_idx()
        self.recall()

    def shuffle(self):
        self.stop()
        time.sleep(0.01)
        self.info['playing_mode'] = 3
        self.generate_shuffle_playing_list()
        self.info['idx'] = self.info['playing_list'][self.info['ridx']]
        self.recall()

    def volume_up(self):
        self.info['playing_volume'] = self.info['playing_volume'] + 7
        if (self.info['playing_volume'] > 100):
            self.info['playing_volume'] = 100
        if not self.playing_flag:
            return
        self.popen_handler.stdin.write(b'V ' + str(self.info[
            'playing_volume']).encode('u8') + b'\n')
        self.popen_handler.stdin.flush()

    def volume_down(self):
        self.info['playing_volume'] = self.info['playing_volume'] - 7
        if (self.info['playing_volume'] < 0):
            self.info['playing_volume'] = 0
        if not self.playing_flag:
            return

        self.popen_handler.stdin.write(b'V ' + str(self.info[
            'playing_volume']).encode('u8') + b'\n')
        self.popen_handler.stdin.flush()

    def update_size(self):
        try:
            self.ui.update_size()
            item = self.songs[self.info['player_list'][self.info['idx']]]
            if self.playing_flag:
                self.ui.build_playinfo(item['song_name'], item['artist'],
                                       item['album_name'], item['quality'],
                                       time.time())
            if self.pause_flag:
                self.ui.build_playinfo(item['song_name'],
                                       item['artist'],
                                       item['album_name'],
                                       item['quality'],
                                       time.time(),
                                       pause=True)
        except Exception as e:
            log.error(e)
            pass

    def cacheSong1time(self, song_id, song_name, artist, song_url):
        def cacheExit(song_id, path):
            self.songs[str(song_id)]['cache'] = path
            self.cache.enable = False

        self.cache.enable = True
        self.cache.add(song_id, song_name, artist, song_url, cacheExit)
        self.cache.start_download()
