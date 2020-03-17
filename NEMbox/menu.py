#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57
'''
网易云音乐 Menu
'''
from __future__ import (
    print_function, unicode_literals, division, absolute_import
)

import time
import curses as C
import threading
import sys
import os
import signal
import webbrowser
import locale
from collections import namedtuple

from future.builtins import range, str

from .api import NetEase
from .player import Player
from .ui import Ui
from .osdlyrics import show_lyrics_new_process
from .config import Config
from .utils import notify
from .storage import Storage
from .cache import Cache
from . import logger
from .cmd_parser import parse_keylist, cmd_parser
from copy import deepcopy


locale.setlocale(locale.LC_ALL, '')

log = logger.getLogger(__name__)


def carousel(left, right, x):
    # carousel x in [left, right]
    if x > right:
        return left
    elif x < left:
        return right
    else:
        return x


shortcut = [
    ['j', 'Down      ', '下移'],
    ['k', 'Up        ', '上移'],
    ['h', 'Back      ', '后退'],
    ['l', 'Forward   ', '前进'],
    ['u', 'Prev page ', '上一页'],
    ['d', 'Next page ', '下一页'],
    ['f', 'Search    ', '快速搜索'],
    ['[', 'Prev song ', '上一曲'],
    [']', 'Next song ', '下一曲'],
    [' ', 'Play/Pause', '播放/暂停'],
    ['?', 'Shuffle          ', '手气不错'],
    ['=', 'Volume+          ', '音量增加'],
    ['-', 'Volume-          ', '音量减少'],
    ['m', 'Menu             ', '主菜单'],
    ['p', 'Present/History  ', '当前/历史播放列表'],
    ['i', 'Music Info       ', '当前音乐信息'],
    ['Shift+p', 'Playing Mode     ', '播放模式切换'],
    ['Shift+a', 'Enter album      ', '进入专辑'],
    ['a', 'Add              ', '添加曲目到打碟'],
    ['z', 'DJ list          ', '打碟列表（退出后清空）'],
    ['s', 'Star      ', '添加到本地收藏'],
    ['c', 'Collection', '本地收藏列表'],
    ['r', 'Remove    ', '删除当前条目'],
    ['Shift+j', 'Move Down ', '向下移动当前条目'],
    ['Shift+k', 'Move Up   ', '向上移动当前条目'],
    [',', 'Like      ', '喜爱'],
    ['Shfit+c', 'Cache     ', '缓存歌曲到本地'],
    ['.', 'Trash FM  ', '删除 FM'],
    ['/', 'Next FM   ', '下一 FM'],
    ['q', 'Quit      ', '退出'],
    ['w', 'Quit&Clear', '退出并清除用户信息']
]


class Menu(object):

    def __init__(self):
        self.config = Config()
        self.datatype = 'main'
        self.title = '网易云音乐'
        self.datalist = [
            '排行榜', '艺术家', '新碟上架', '精选歌单', '我的歌单',
            '主播电台', '每日推荐歌曲', '每日推荐歌单', '私人FM', '搜索', '帮助'
        ]
        self.offset = 0
        self.index = 0
        self.storage = Storage()
        self.storage.load()
        self.collection = self.storage.database['collections']
        self.player = Player()
        self.player.playing_song_changed_callback = self.song_changed_callback
        self.cache = Cache()
        self.ui = Ui()
        self.api = NetEase()
        self.screen = C.initscr()
        self.screen.keypad(1)
        self.step = 10
        self.stack = []
        self.djstack = []
        self.at_playing_list = False
        self.enter_flag = True
        signal.signal(signal.SIGWINCH, self.change_term)
        signal.signal(signal.SIGINT, self.send_kill)
        self.menu_starts = time.time()
        self.countdown_start = time.time()
        self.countdown = -1
        self.is_in_countdown = False
        self.key_list = []
        self.pre_keylist = []

    @property
    def user(self):
        return self.storage.database['user']

    @property
    def account(self):
        return self.user['username']

    @property
    def md5pass(self):
        return self.user['password']

    @property
    def userid(self):
        return self.user['user_id']

    @property
    def username(self):
        return self.user['nickname']

    def login(self):
        if self.account and self.md5pass:
            account, md5pass = self.account, self.md5pass
        else:
            account, md5pass = self.ui.build_login()

        resp = self.api.login(account, md5pass)
        if resp['code'] == 200:
            userid = resp['account']['id']
            nickname = resp['profile']['nickname']
            self.storage.login(account, md5pass, userid, nickname)
            return True
        else:
            self.storage.logout()
            x = self.ui.build_login_error()
            if x != ord('1'):
                return False
            return self.login()

    def search(self, category):
        self.ui.screen.timeout(-1)
        SearchArg = namedtuple(
            'SearchArg', ['prompt', 'api_type', 'post_process'])
        category_map = {
            'songs': SearchArg('搜索歌曲：', 1, lambda datalist: datalist),
            'albums': SearchArg('搜索专辑：', 10, lambda datalist: datalist),
            'artists': SearchArg('搜索艺术家：', 100, lambda datalist: datalist),
            'playlists': SearchArg('搜索网易精选集：', 1000, lambda datalist: datalist)
        }

        prompt, api_type, post_process = category_map[category]
        keyword = self.ui.get_param(prompt)
        if not keyword:
            return []

        data = self.api.search(keyword, api_type)
        if not data:
            return data

        datalist = post_process(data.get(category, []))
        return self.api.dig_info(datalist, category)

    def change_term(self, signum, frame):
        self.ui.screen.clear()
        self.ui.screen.refresh()

    def send_kill(self, signum, fram):
        self.player.stop()
        self.cache.quit()
        self.storage.save()
        C.endwin()
        sys.exit()

    def update_alert(self, version):
        latest = Menu().check_version()
        if latest != version and latest != 0:
            notify('MusicBox Update is available', 1)
            time.sleep(0.5)
            notify('NetEase-MusicBox installed version:' + version +
                   '\nNetEase-MusicBox latest version:' + latest, 0)

    def check_version(self):
        # 检查更新 && 签到
        try:
            mobile = self.api.daily_task(is_mobile=True)
            pc = self.api.daily_task(is_mobile=False)

            if mobile['code'] == 200:
                notify('移动端签到成功', 1)
            if pc['code'] == 200:
                notify('PC端签到成功', 1)

            data = self.api.get_version()
            return data['info']['version']
        except KeyError as e:
            return 0

    def start_fork(self, version):
        pid = os.fork()
        if pid == 0:
            Menu().update_alert(version)
        else:
            Menu().start()

    def play_pause(self):
        if self.player.is_empty:
            return
        if not self.player.playing_flag:
            self.player.resume()
        else:
            self.player.pause()

    def next_song(self):
        if self.player.is_empty:
            return
        self.player.next()

    def previous_song(self):
        if self.player.is_empty:
            return
        self.player.prev()

    def up_key_event(self):
        datalist = self.datalist
        offset = self.offset
        idx = self.index
        step = self.step
        if idx == offset:
            if offset == 0:
                return
            self.offset -= step
            # 移动光标到最后一列
            self.index = offset - 1
        else:
            self.index = carousel(offset, min(
                len(datalist), offset + step) - 1, idx - 1)
        self.menu_starts = time.time()

    def jump_key_event(self):
        datalist = self.datalist
        offset = self.offset
        idx = self.index
        step = self.step
        if idx == min(len(datalist), offset + step) - 1:
            if offset + step >= len(datalist):
                return
            self.offset += step
            # 移动光标到第一列
            self.index = offset + step
        else:
            self.index = carousel(offset, min(
                len(datalist), offset + step) - 1, idx + 1)
        self.menu_starts = time.time()

    def space_key_event(self):
        idx = self.index
        datatype = self.datatype
        if not self.datalist:
            return
        if idx < 0 or idx >= len(self.datalist):
            self.player.info['idx'] = 0

        # If change to a new playing list. Add playing list and play.
        if datatype == 'songs':
            self.player.new_player_list('songs', self.title,
                                        self.datalist, -1)
            self.player.end_callback = None
            self.player.play_or_pause(idx, self.at_playing_list)
            self.at_playing_list = True
        elif datatype == 'djchannels':
            self.player.new_player_list('djchannels', self.title,
                                        self.datalist, -1)
            self.player.end_callback = None
            self.player.play_or_pause(idx, self.at_playing_list)
            self.at_playing_list = True
        elif datatype == 'fmsongs':
            self.player.change_mode(0)
            self.player.new_player_list('fmsongs', self.title,
                                        self.datalist, -1)
            self.player.end_callback = self.fm_callback
            self.player.play_or_pause(idx, self.at_playing_list)
            self.at_playing_list = True
        else:
            # 所在列表类型不是歌曲
            isNotSongs = True
            self.player.play_or_pause(
                self.player.info['idx'], isNotSongs)
        self.build_menu_processbar()

    def like_event(self):
        return_data = self.request_api(self.api.fm_like,
                                       self.player.playing_id)
        if return_data:
            song_name = self.player.playing_name
            notify('%s added successfully!' % song_name, 0)
        else:
            notify('Adding song failed!', 0)

    def back_page_event(self):
        if len(self.stack) == 1:
            return
        self.menu_starts = time.time()
        self.datatype, self.title, self.datalist,\
            self.offset, self.index = self.stack.pop()
        self.at_playing_list = False

    def enter_page_event(self):
        idx = self.index
        self.enter_flag = True
        if len(self.datalist) <= 0:
            return
        self.menu_starts = time.time()
        self.ui.build_loading()
        self.dispatch_enter(idx)
        if self.enter_flag is True:
            self.index = 0
            self.offset = 0

    def album_key_event(self):
        datatype = self.datatype
        title = self.title
        datalist = self.datalist
        offset = self.offset
        idx = self.index
        step = self.step
        if datatype == 'album':
            return
        if datatype in ['songs', 'fmsongs']:
            song_id = datalist[idx]['song_id']
            album_id = datalist[idx]['album_id']
            album_name = datalist[idx]['album_name']
        elif self.player.playing_flag:
            song_id = self.player.playing_id
            song_info = self.player.songs.get(str(song_id), {})
            album_id = song_info.get('album_id', '')
            album_name = song_info.get('album_name', '')
        else:
            album_id = 0
        if album_id:
            self.stack.append(
                [datatype, title, datalist, offset, self.index])
            songs = self.api.album(album_id)
            self.datatype = 'songs'
            self.datalist = self.api.dig_info(songs, 'songs')
            self.title = '网易云音乐 > 专辑 > %s' % album_name
            for i in range(len(self.datalist)):
                if self.datalist[i]['song_id'] == song_id:
                    self.offset = i - i % step
                    self.index = i
                    return
        self.build_menu_processbar()

    def num_jump_key_event(self):
        # 键盘映射ascii编码 91 [ 93 ] 258<KEY_DOWN> 259 <KEY_UP> 106 j 107 k
        # 歌单快速跳跃
        result = parse_keylist(self.key_list)
        num, cmd = result
        if num == 0:  # 0j -> 1j
            num = 1
        for i in range(num):
            if cmd in (259, 107, 91):
                self.up_key_event()
            elif cmd in (258, 106, 93):
                self.jump_key_event()
        if cmd in (91, 93):
            self.space_key_event()
        self.build_menu_processbar()

    def digit_key_song_event(self):
        step = self.step
        song_index = parse_keylist(self.key_list)
        self.index = song_index
        self.offset = self.index - self.index % step
        self.build_menu_processbar()

    def time_key_event(self):
        self.countdown_start = time.time()
        countdown = self.ui.build_timing()
        if not countdown.isdigit():
            notify('The input should be digit')

        countdown = int(countdown)
        if countdown > 0:
            notify(
                'The musicbox will exit in {} minutes'.format(countdown))
            self.countdown = countdown * 60
            self.is_in_countdown = True
        else:
            notify('The timing exit has been canceled')
            self.is_in_countdown = False
        self.build_menu_processbar()

    def down_page_event(self):
        offset = self.offset
        step = self.step
        if offset + step >= len(datalist):
            return
        self.menu_starts = time.time()
        self.offset += step

        # e.g. 23 + 10 = 33 --> 30
        self.index = (self.index + step) // step * step

    def up_page_event(self):
        offset = self.offset
        step = self.step
        if offset == 0:
            return
        self.menu_starts = time.time()
        self.offset -= step

        # e.g. 23 - 10 = 13 --> 10
        self.index = (self.index - step) // step * step

    def resize_key_event(self):
        self.player.update_size()

    def build_menu_processbar(self):
        self.ui.build_process_bar(
            self.player.current_song,
            self.player.process_location, self.player.process_length,
            self.player.playing_flag, self.player.info['playing_mode']
        )
        self.ui.build_menu(self.datatype, self.title, self.datalist,
                           self.offset, self.index, self.step, self.menu_starts)

    def quit_event(self):
        sys.exit(0)

    def start(self):
        self.menu_starts = time.time()
        self.ui.build_menu(self.datatype, self.title, self.datalist,
                           self.offset, self.index, self.step, self.menu_starts)
        self.stack.append([
            self.datatype, self.title, self.datalist, self.offset, self.index
        ])

        show_lyrics_new_process()
        pre_key = -1
        keylist = self.key_list
        parser = cmd_parser(keylist)
        next(parser)  # start generator
        while True:
            self.screen.timeout(500)
            key = self.screen.getch()
            parser.send(key)
            if keylist:
                self.pre_keylist = deepcopy(keylist)

            # log.warn(datatype)
            if self.datatype == 'songs' and keylist and \
                    (set(keylist) | set(range(48, 58))) == set(range(48, 58)):
                # 歌曲数字映射
                self.digit_key_song_event()
                self.ui.screen.refresh()
                self.space_key_event()
                continue

            if len(keylist) > 1:
                # log.warn(keylist)
                if parse_keylist(keylist):
                    self.num_jump_key_event()
            else:
                # 单键映射
                # term resize
                if key == -1:
                    self.player.update_size()
                    self.build_menu_processbar()

                if self.is_in_countdown:
                    if time.time() - self.countdown_start > self.countdown:
                        key = ord('q')
                # 退出
                if key == ord('q'):
                    break

                # 退出并清除用户信息
                if key == ord('w'):
                    self.api.logout()
                    break

                # 上移
                elif key in (ord('k'), C.KEY_UP) and not (pre_key in range(48, 58)):
                    self.up_key_event()
                    self.build_menu_processbar()

                # 下移
                elif key in (ord('j'), C.KEY_DOWN) and pre_key not in range(48, 58):
                    self.jump_key_event()
                    self.build_menu_processbar()

                # 数字快捷键
                elif ord('0') <= key <= ord('9') and self.datatype != 'songs':
                    idx = key - ord('0')
                    self.ui.build_menu(self.datatype, self.title, self.datalist,
                                       self.offset, idx, self.step, self.menu_starts)
                    self.ui.build_loading()
                    self.dispatch_enter(idx)
                    self.index = 0
                    self.offset = 0
                    self.build_menu_processbar()

                # 向上翻页
                elif key == ord('u'):
                    self.up_page_event()
                    self.build_menu_processbar()
                # 向下翻页
                elif key == ord('d'):
                    self.down_page_event()
                    self.build_menu_processbar()

                # 前进  10 为mac return键
                elif key in (ord('l'), C.KEY_RIGHT, 10):
                    self.enter_page_event()
                    self.build_menu_processbar()

                # 回退
                elif key in (ord('h'), C.KEY_LEFT):
                    self.back_page_event()
                    self.build_menu_processbar()

                # 搜索
                elif key == ord('f'):
                    # 8 is the 'search' menu
                    self.dispatch_enter(8)
                    self.build_menu_processbar()

                # 播放下一曲
                elif key == ord(']'):
                    # self.next_song()
                    self.jump_key_event()
                    self.build_menu_processbar()

                # 播放上一曲
                elif key == ord('['):
                    # self.previous_song()
                    self.up_key_event()
                    self.build_menu_processbar()
                elif pre_key in (ord('['), ord(']')) and key == -1 and\
                        self.datatype == 'songs' and sum(self.pre_keylist) % 92 != 0:
                    self.space_key_event()
                    self.build_menu_processbar()

                # 增加音量
                elif key == ord('='):
                    self.player.volume_up()
                    self.build_menu_processbar()

                # 减少音量
                elif key == ord('-'):
                    self.player.volume_down()
                    self.build_menu_processbar()

                # 随机播放
                elif key == ord('?'):
                    if len(self.player.info['player_list']) == 0:
                        continue
                    self.player.shuffle()
                    self.build_menu_processbar()

                # 喜爱
                elif key == ord(','):
                    return_data = self.request_api(self.api.fm_like,
                                                   self.player.playing_id)
                    if return_data:
                        song_name = self.player.playing_name
                        notify('%s added successfully!' % song_name, 0)
                    else:
                        notify('Adding song failed!', 0)
                    self.build_menu_processbar()

                # 删除FM
                elif key == ord('.'):
                    if self.datatype == 'fmsongs':
                        if len(self.player.info['player_list']) == 0:
                            continue
                        self.player.next()
                        return_data = self.request_api(
                            self.api.fm_trash, self.player.playing_id)
                        if return_data:
                            notify('Deleted successfully!', 0)
                    self.build_menu_processbar()

                # 下一FM
                elif key == ord('/'):
                    if self.datatype == 'fmsongs':
                        if len(self.player.info['player_list']) == 0:
                            continue
                        if self.player.end_callback:
                            self.player.end_callback()
                    self.build_menu_processbar()

                # 播放、暂停
                elif key == ord(' '):
                    self.space_key_event()
                    self.build_menu_processbar()

                # 加载当前播放列表
                elif key == ord('p'):
                    self.show_playing_song()
                    self.build_menu_processbar()

                # 播放模式切换
                elif key == ord('P'):
                    self.player.change_mode()
                    self.build_menu_processbar()

                # 进入专辑
                elif key == ord('A'):
                    self.album_key_event()
                # 添加到打碟歌单
                elif key == ord('a'):
                    datatype = self.datatype
                    idx = self.index
                    if datatype == 'songs' and len(self.datalist) != 0:
                        self.djstack.append(self.datalist[idx])
                    elif datatype == 'artists':
                        pass
                    self.build_menu_processbar()

                # 加载打碟歌单
                elif key == ord('z'):
                    self.stack.append(
                        [datatype, title, datalist, offset, self.index])
                    self.datatype = 'songs'
                    self.title = '网易云音乐 > 打碟'
                    self.datalist = self.djstack
                    self.offset = 0
                    self.index = 0
                    self.build_menu_processbar()

                # 添加到本地收藏
                elif key == ord('s'):
                    if (self.datatype == 'songs' or
                            self.datatype == 'djchannels') and len(self.datalist) != 0:
                        self.collection.append(self.datalist[self.index])
                        notify('Added successfully', 0)
                    self.build_menu_processbar()

                # 加载本地收藏
                elif key == ord('c'):
                    self.stack.append(
                        [self.datatype, self.title, self.datalist, self.offset, self.index])
                    self.datatype = 'songs'
                    self.title = '网易云音乐 > 本地收藏'
                    self.datalist = self.collection
                    self.offset = 0
                    self.index = 0
                    self.build_menu_processbar()

                # 从当前列表移除
                elif key == ord('r'):
                    if (self.datatype in ('songs', 'djchannels', 'fmsongs') and
                            len(self.datalist) != 0):
                        self.datalist.pop(self.index)
                        self.index = carousel(self.offset, min(
                            len(self.datalist), self.offset + self.step) - 1, self.index)
                    self.build_menu_processbar()

                elif key == ord('t'):
                    self.time_key_event()

                # 当前项目下移
                elif key == ord('J'):
                    if self.datatype != 'main' and len(self.datalist) != 0 and\
                            self.index + 1 != len(self.datalist):
                        self.menu_starts = time.time()
                        song = self.datalist.pop(self.index)
                        self.datalist.insert(self.index + 1, song)
                        self.index = self.index + 1
                        # 翻页
                        if self.index >= self.offset + self.step:
                            self.offset = self.offset + self.step
                    self.build_menu_processbar()

                # 当前项目上移
                elif key == ord('K'):
                    if self.datatype != 'main' and len(self.datalist) != 0 and self.index != 0:
                        self.menu_starts = time.time()
                        song = self.datalist.pop(self.index)
                        self.datalist.insert(self.index - 1, song)
                        self.index = self.index - 1
                        # 翻页
                        if self.index < self.offset:
                            self.offset = self.offset - self.step
                    self.build_menu_processbar()

                elif key == ord('m'):
                    if self.datatype != 'main':
                        self.stack.append(
                            [self.datatype, self.title, self.datalist, self.offset, self.index])
                        self.datatype = self.stack[0][0]
                        self.title = self.stack[0][1]
                        self.datalist = self.stack[0][2]
                        self.offset = 0
                        self.index = 0
                    self.build_menu_processbar()

                elif key == ord('g'):
                    if self.datatype == 'help':
                        webbrowser.open_new_tab(
                            'https://github.com/wangjianyuan10/musicbox')
                    else:
                        self.index = 0
                        self.offset = 0
                    self.build_menu_processbar()

                elif key == ord('G'):
                    self.index = len(self.datalist) - 1
                    self.offset = self.index - self.index % self.step
                    self.build_menu_processbar()

                # 开始下载
                elif key == ord('C'):
                    s = self.datalist[self.index]
                    cache_thread = threading.Thread(
                        target=self.player.cache_song,
                        args=(s['song_id'], s['song_name'],
                              s['artist'], s['mp3_url'])
                    )
                    cache_thread.start()
                    self.build_menu_processbar()

                elif key == ord('i'):
                    if self.player.playing_id != -1:
                        webbrowser.open_new_tab(
                            'http://music.163.com/song?id={}'.format(
                                self.player.playing_id)
                        )
                    self.build_menu_processbar()

                pre_key = key
                self.ui.screen.refresh()
                # keylist.clear()

        self.player.stop()
        self.cache.quit()
        self.storage.save()
        C.endwin()

    def dispatch_enter(self, idx):
        # The end of stack
        netease = self.api
        datatype = self.datatype
        title = self.title
        datalist = self.datalist
        offset = self.offset
        index = self.index
        self.stack.append([datatype, title, datalist, offset, index])

        if idx >= len(self.datalist):
            return False

        if datatype == 'main':
            self.choice_channel(idx)

        # 该艺术家的热门歌曲
        elif datatype == 'artists':
            artist_name = datalist[idx]['artists_name']
            artist_id = datalist[idx]['artist_id']

            self.datatype = 'artist_info'
            self.title += ' > ' + artist_name
            self.datalist = [{
                'item': '{}的热门歌曲'.format(artist_name),
                'id': artist_id,
            }, {
                'item': '{}的所有专辑'.format(artist_name),
                'id': artist_id,
            }]

        elif datatype == 'artist_info':
            self.title += ' > ' + datalist[idx]['item']
            artist_id = datalist[0]['id']
            if idx == 0:
                self.datatype = 'songs'
                songs = netease.artists(artist_id)
                self.datalist = netease.dig_info(songs, 'songs')

            elif idx == 1:
                albums = netease.get_artist_album(artist_id)
                self.datatype = 'albums'
                self.datalist = netease.dig_info(albums, 'albums')

        elif datatype == 'djchannels':
            radio_id = datalist[idx]['id']
            programs = netease.djprograms(radio_id)
            self.title += ' > ' + datalist[idx]['name']
            self.datatype = 'songs'
            self.datalist = netease.dig_info(programs, 'songs')

        # 该专辑包含的歌曲
        elif datatype == 'albums':
            album_id = datalist[idx]['album_id']
            songs = netease.album(album_id)
            self.datatype = 'songs'
            self.datalist = netease.dig_info(songs, 'songs')
            self.title += ' > ' + datalist[idx]['albums_name']

        # 精选歌单选项
        elif datatype == 'recommend_lists':
            data = self.datalist[idx]
            self.datatype = data['datatype']
            self.datalist = netease.dig_info(data['callback'](), self.datatype)
            self.title += ' > ' + data['title']

        # 全站置顶歌单包含的歌曲
        elif datatype in ['top_playlists', 'playlists']:
            playlist_id = datalist[idx]['playlist_id']
            songs = netease.playlist_detail(playlist_id)
            self.datatype = 'songs'
            self.datalist = netease.dig_info(songs, 'songs')
            self.title += ' > ' + datalist[idx]['playlist_name']

        # 分类精选
        elif datatype == 'playlist_classes':
            # 分类名称
            data = self.datalist[idx]
            self.datatype = 'playlist_class_detail'
            self.datalist = netease.dig_info(data, self.datatype)
            self.title += ' > ' + data

        # 某一分类的详情
        elif datatype == 'playlist_class_detail':
            # 子类别
            data = self.datalist[idx]
            self.datatype = 'top_playlists'
            log.error(data)
            self.datalist = netease.dig_info(
                netease.top_playlists(data), self.datatype)
            self.title += ' > ' + data

        # 歌曲评论
        elif datatype in ['songs', 'fmsongs']:
            song_id = datalist[idx]['song_id']
            comments = self.api.song_comments(song_id, limit=100)
            try:
                hotcomments = comments['hotComments']
                comcomments = comments['comments']
            except KeyError:
                hotcomments = comcomments = []
            self.datalist = []
            for one_comment in hotcomments:
                self.datalist.append(
                    u'(热评 %s❤️ ️)%s:%s' % (one_comment['likedCount'], one_comment['user']['nickname'],
                                           one_comment['content']))
            for one_comment in comcomments:
                self.datalist.append(one_comment['content'])
            self.datatype = 'comments'
            self.title = '网易云音乐 > 评论:%s' % datalist[idx]['song_name']
            self.offset = 0
            self.index = 0

        # 歌曲榜单
        elif datatype == 'toplists':
            songs = netease.top_songlist(idx)
            self.title += ' > ' + self.datalist[idx]
            self.datalist = netease.dig_info(songs, 'songs')
            self.datatype = 'songs'

        # 搜索菜单
        elif datatype == 'search':
            self.index = 0
            self.offset = 0
            SearchCategory = namedtuple('SearchCategory', ['type', 'title'])
            idx_map = {
                0: SearchCategory('playlists', '精选歌单搜索列表'),
                1: SearchCategory('songs', '歌曲搜索列表'),
                2: SearchCategory('artists', '艺术家搜索列表'),
                3: SearchCategory('albums', '专辑搜索列表')
            }
            self.datatype, self.title = idx_map[idx]
            self.datalist = self.search(self.datatype)
        else:
            self.enter_flag = False

    def show_playing_song(self):
        if self.player.is_empty:
            return

        if not self.at_playing_list:
            self.stack.append([self.datatype, self.title, self.datalist,
                               self.offset, self.index])
            self.at_playing_list = True

        self.datatype = self.player.info['player_list_type']
        self.title = self.player.info['player_list_title']
        self.datalist = [
            self.player.songs[i] for i in self.player.info['player_list']
        ]
        self.index = self.player.info['idx']
        self.offset = self.index // self.step * self.step

    def song_changed_callback(self):
        if self.at_playing_list:
            self.show_playing_song()

    def fm_callback(self):
        # log.debug('FM CallBack.')
        data = self.get_new_fm()
        self.player.append_songs(data)
        if self.datatype == 'fmsongs':
            if self.player.is_empty:
                return
            self.datatype = self.player.info['player_list_type']
            self.title = self.player.info['player_list_title']
            self.datalist = []
            for i in self.player.info['player_list']:
                self.datalist.append(self.player.songs[i])
            self.index = self.player.info['idx']
            self.offset = self.index // self.step * self.step
            if not self.player.playing_flag:
                switch_flag = False
                self.player.play_or_pause(self.index, switch_flag)

    def request_api(self, func, *args):
        result = func(*args)
        if result:
            return result
        if not self.login():
            notify('You need to log in')
            return False
        return func(*args)

    def get_new_fm(self):
        data = self.request_api(self.api.personal_fm)
        if not data:
            return []
        return self.api.dig_info(data, 'fmsongs')

    def choice_channel(self, idx):
        self.offset = 0
        self.index = 0

        if idx == 0:
            self.datalist = self.api.toplists
            self.title += ' > 排行榜'
            self.datatype = 'toplists'
        elif idx == 1:
            artists = self.api.top_artists()
            self.datalist = self.api.dig_info(artists, 'artists')
            self.title += ' > 艺术家'
            self.datatype = 'artists'
        elif idx == 2:
            albums = self.api.new_albums()
            self.datalist = self.api.dig_info(albums, 'albums')
            self.title += ' > 新碟上架'
            self.datatype = 'albums'
        elif idx == 3:
            self.datalist = [{
                'title': '全站置顶',
                'datatype': 'top_playlists',
                'callback': self.api.top_playlists
            }, {
                'title': '分类精选',
                'datatype': 'playlist_classes',
                'callback': lambda: []
            }]
            self.title += ' > 精选歌单'
            self.datatype = 'recommend_lists'
        elif idx == 4:
            myplaylist = self.request_api(self.api.user_playlist, self.userid)
            self.datatype = 'top_playlists'
            self.datalist = self.api.dig_info(myplaylist, self.datatype)
            self.title += ' > ' + self.username + ' 的歌单'
        elif idx == 5:
            self.datatype = 'djchannels'
            self.title += ' > 主播电台'
            self.datalist = self.api.djchannels()
        elif idx == 6:
            self.datatype = 'songs'
            self.title += ' > 每日推荐歌曲'
            myplaylist = self.request_api(self.api.recommend_playlist)
            if myplaylist == -1:
                return
            self.datalist = self.api.dig_info(myplaylist, self.datatype)
        elif idx == 7:
            myplaylist = self.request_api(self.api.recommend_resource)
            self.datatype = 'top_playlists'
            self.title += ' > 每日推荐歌单'
            self.datalist = self.api.dig_info(myplaylist, self.datatype)
        elif idx == 8:
            self.datatype = 'fmsongs'
            self.title += ' > 私人FM'
            self.datalist = self.get_new_fm()
        elif idx == 9:
            self.datatype = 'search'
            self.title += ' > 搜索'
            self.datalist = ['歌曲', '艺术家', '专辑', '网易精选集']
        elif idx == 10:
            self.datatype = 'help'
            self.title += ' > 帮助'
            self.datalist = shortcut
