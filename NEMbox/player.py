#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-07-15 15:48:27
# @Last Modified by:   omi
# @Last Modified time: 2015-01-30 18:05:08
'''
网易云音乐 Player
'''
# Let's make some noise
from __future__ import (
    print_function, unicode_literals, division, absolute_import
)

import subprocess
import threading
import time
import os
import random


from future.builtins import str

from .ui import Ui
from .storage import Storage
from .api import NetEase
from .cache import Cache
from .config import Config
from .utils import notify

from . import logger

log = logger.getLogger(__name__)


class Player(object):

    MODE_ORDERED = 0
    MODE_ORDERED_LOOP = 1
    MODE_SINGLE_LOOP = 2
    MODE_RANDOM = 3
    MODE_RANDOM_LOOP = 4

    def __init__(self):
        self.config = Config()
        self.ui = Ui()
        self.popen_handler = None
        # flag stop, prevent thread start
        self.playing_flag = False
        self.process_length = 0
        self.process_location = 0
        self.storage = Storage()
        self.cache = Cache()
        self.end_callback = None
        self.playing_song_changed_callback = None
        self.api = NetEase()

    @property
    def info(self):
        return self.storage.database['player_info']

    @property
    def songs(self):
        return self.storage.database['songs']

    @property
    def index(self):
        return self.info['idx']

    @property
    def list(self):
        return self.info['player_list']

    @property
    def order(self):
        return self.info['playing_order']

    @property
    def mode(self):
        return self.info['playing_mode']

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
        return self.config.get('notifier')

    @property
    def config_mpg123(self):
        return self.config.get('mpg123_parameters')

    @property
    def current_song(self):
        if not self.songs:
            return {}

        if not self.is_index_valid:
            return {}
        song_id = self.list[self.index]
        return self.songs.get(song_id, {})

    @property
    def playing_id(self):
        return self.current_song['song_id']

    @property
    def playing_name(self):
        return self.current_song['song_name']

    @property
    def is_empty(self):
        return len(self.list) == 0

    @property
    def is_index_valid(self):
        return 0 <= self.index < len(self.list)

    def change_mode(self, step=1):
        self.info['playing_mode'] = (self.info['playing_mode'] + step) % 5

    def build_playinfo(self):
        if not self.current_song:
            return

        self.ui.build_playinfo(
            self.current_song['song_name'],
            self.current_song['artist'],
            self.current_song['album_name'],
            self.current_song['quality'],
            time.time(), pause=not self.playing_flag
        )

    def add_songs(self, songs):
        for song in songs:
            song_id = str(song['song_id'])
            self.info['player_list'].append(song_id)
            if song_id in self.songs:
                self.songs[song_id].update(song)
            else:
                self.songs[song_id] = song

    def stop(self):
        if not self.popen_handler:
            return

        self.playing_flag = False
        self.popen_handler.stdin.write(b'Q\n')
        self.popen_handler.stdin.flush()
        self.popen_handler.kill()
        self.popen_handler = None
        # wait process to be killed
        time.sleep(0.01)

    def tune_volume(self, up=0):
        if not self.popen_handler:
            return

        new_volume = self.info['playing_volume'] + up
        if new_volume > 100:
            new_volume = 100
        elif new_volume < 0:
            new_volume = 0

        self.info['playing_volume'] = new_volume
        self.popen_handler.stdin.write(
            'V {}\n'.format(self.info['playing_volume']).encode()
        )
        self.popen_handler.stdin.flush()

    def switch(self):
        if not self.popen_handler:
            return

        self.playing_flag = not self.playing_flag
        self.popen_handler.stdin.write(b'P\n')
        self.popen_handler.stdin.flush()

        self.build_playinfo()

    def run_mpg123(self, on_exit, url):
        para = ['mpg123', '-R'] + self.config_mpg123
        self.popen_handler = subprocess.Popen(
            para,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        self.tune_volume()
        self.popen_handler.stdin.write(b'L ' + url.encode('utf-8') + b'\n')
        self.popen_handler.stdin.flush()

        endless_loop_cnt = 0
        while True:
            if not self.popen_handler:
                break

            strout = self.popen_handler.stdout.readline().decode('utf-8').strip()
            if strout[:2] == '@F':
                # playing, update progress
                out = strout.split(' ')
                self.process_location = int(float(out[3]))
                if not self.process_length:
                    self.process_length = int(float(out[3]) + float(out[4]))
            elif strout[:2] == '@E':
                # error, stop song and move to next
                self.playing_flag = True
                notify('版权限制，无法播放此歌曲')
                log.warning('Song {} is unavailable due to copyright issue.'.format(self.playing_id))
                break
            elif strout == '@P 0':
                # end, moving to next
                self.playing_flag = True
            elif strout == '':
                endless_loop_cnt += 1
                # 有播放后没有退出，mpg123一直在发送空消息的情况，此处直接终止处理
                if endless_loop_cnt > 100:
                    log.warning('mpg123 error, halt, endless loop and high cpu use, then we kill it')
                    break

        self.stop()
        if self.playing_flag:
            self.next_idx()
            self.replay()

    def download_lyric(self, is_transalted=False):
        key = 'lyric' if not is_transalted else 'tlyric'

        if key not in self.songs[str(self.playing_id)]:
            self.songs[str(self.playing_id)][key] = []

        if len(self.songs[str(self.playing_id)][key]) > 0:
            return

        if not is_transalted:
            lyric = self.api.song_lyric(self.playing_id)
        else:
            lyric = self.api.song_tlyric(self.playing_id)

        self.songs[str(self.playing_id)][key] = lyric

    def download_song(self, song_id, song_name, artist, url):
        def write_path(song_id, path):
            self.songs[str(song_id)]['cache'] = path

        self.cache.add(song_id, song_name, artist, url, write_path)
        self.cache.start_download()

    def start_playing(self, on_exit, args):
        '''
        Runs the given args in subprocess.Popen, and then calls the function
        on_exit when the subprocess completes.
        on_exit is a callable object, and args is a lists/tuple of args
        that would give to subprocess.Popen.
        '''

        if 'cache' in args.keys() and os.path.isfile(args['cache']):
            thread = threading.Thread(target=self.run_mpg123,
                                      args=(on_exit, args['cache']))
        else:
            thread = threading.Thread(target=self.run_mpg123,
                                      args=(on_exit, args['mp3_url']))
            cache_thread = threading.Thread(
                target=self.download_song,
                args=(args['song_id'], args['song_name'], args['artist'], args['mp3_url'])
            )
            cache_thread.start()

        thread.start()
        lyric_download_thread = threading.Thread(target=self.download_lyric)
        lyric_download_thread.start()
        tlyric_download_thread = threading.Thread(target=self.download_lyric, args=(True,))
        tlyric_download_thread.start()
        # returns immediately after the thread starts
        return thread

    def replay(self):
        if not self.is_index_valid:
            self.stop()
            if self.end_callback:
                log.debug('Callback')
                self.end_callback()
            return

        self.playing_flag = True
        item = self.current_song
        self.build_playinfo()

        if self.config_notifier:
            notify('正在播放: {}\n{}-{}'.format(item['song_name'], item['artist'], item['album_name']))

        self.start_playing(lambda: 0, item)

    def shuffle_order(self):
        self.order.clear()
        self.order.extend(self.list)
        random.shuffle(self.order)
        self.info['ridx'] = 0

    def new_player_list(self, type, title, datalist, offset):
        self.info['player_list_type'] = type
        self.info['player_list_title'] = title
        self.info['idx'] = offset
        self.info['player_list'] = []
        self.info['playing_order'] = []
        self.info['ridx'] = 0
        self.add_songs(datalist)

    def append_songs(self, datalist):
        self.add_songs(datalist)

    def play_or_pause(self, idx):
        if self.is_empty:
            return

        # if same playlists && idx --> same song :: pause/resume it
        if self.info['idx'] == idx:
            if not self.popen_handler:
                self.replay()
            else:
                self.switch()
        else:
            self.info['idx'] = idx
            self.stop()
            # start new play
            self.replay()

    def _swap_song(self):
        plist = self.info['playing_order']
        now_songs = plist.index(self.info['idx'])
        plist[0], plist[now_songs] = plist[now_songs], plist[0]

    def _inc_idx(self):
        if self.info['idx'] < len(self.info['player_list']):
            self.info['idx'] += 1

    def _dec_idx(self):
        if self.info['idx'] >= 0:
            self.info['idx'] -= 1

    def _need_to_shuffle(self):
        playing_list = self.info['playing_order']
        ridx = self.info['ridx']
        idx = self.info['idx']
        if ridx >= len(playing_list) or playing_list[ridx] != idx:
            return True
        else:
            return False

    def next_idx(self):
        if not self.is_index_valid:
            return self.stop()
        playlist_len = len(self.info['player_list'])
        playinglist_len = len(self.info['playing_order'])

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
                self.shuffle_order()
                playinglist_len = len(self.info['playing_order'])
                # When you regenerate playing list
                # you should keep previous song same.
                self._swap_song()

            self.info['ridx'] += 1
            # Out of border
            if self.info['playing_mode'] == 4:
                self.info['ridx'] %= playinglist_len

            if self.info['ridx'] >= playinglist_len:
                self.info['idx'] = playlist_len
            else:
                self.info['idx'] = self.info['playing_order'][self.info['ridx']]
        else:
            self.info['idx'] += 1
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
        playlist_len = len(self.info['player_list'])
        playinglist_len = len(self.info['playing_order'])
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
                self.shuffle_order()
                playinglist_len = len(self.info['playing_order'])
            self.info['ridx'] -= 1
            if self.info['ridx'] < 0:
                if self.info['playing_mode'] == 3:
                    self.info['ridx'] = 0
                else:
                    self.info['ridx'] %= playinglist_len
            self.info['idx'] = self.info['playing_order'][self.info['ridx']]
        else:
            self.info['idx'] -= 1
        if self.playing_song_changed_callback is not None:
            self.playing_song_changed_callback()

    def prev(self):
        self.stop()
        self.prev_idx()
        self.replay()

    def shuffle(self):
        self.stop()
        self.info['playing_mode'] = 3
        self.shuffle_order()
        self.info['idx'] = self.info['playing_order'][self.info['ridx']]
        self.replay()

    def volume_up(self):
        self.tune_volume(5)

    def volume_down(self):
        self.tune_volume(-5)

    def update_size(self):
        self.ui.update_size()
        self.build_playinfo()

    def cache_song(self, song_id, song_name, artist, song_url):
        def on_exit(song_id, path):
            self.songs[str(song_id)]['cache'] = path
            self.cache.enable = False

        self.cache.enable = True
        self.cache.add(song_id, song_name, artist, song_url, on_exit)
        self.cache.start_download()
