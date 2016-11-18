#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57
'''
网易云音乐 Menu
'''
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import range
from builtins import str
from future import standard_library
standard_library.install_aliases()

import curses
import threading
import sys
import os
import time
import signal
import webbrowser
import locale
import xml.etree.cElementTree as ET


from .api import NetEase
from .player import Player
from .ui import Ui
from .osdlyrics import show_lyrics_new_process
from .const import Constant
from .config import Config
from .utils import notify
from .storage import Storage
from .cache import Cache
from . import logger


locale.setlocale(locale.LC_ALL, '')

log = logger.getLogger(__name__)

try:
    # import keybinder
    BINDABLE = False
except ImportError:
    BINDABLE = False
    log.warn('keybinder module not installed.')
    log.warn('Not binding global hotkeys.')

home = os.path.expanduser('~')
if os.path.isdir(Constant.conf_dir) is False:
    os.mkdir(Constant.conf_dir)


def carousel(left, right, x):
    # carousel x in [left, right]
    if x > right:
        return left
    elif x < left:
        return right
    else:
        return x


# yapf: disable
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


# yapf: enable
class Menu(object):

    def __init__(self):
        self.config = Config()
        self.datatype = 'main'
        self.title = '网易云音乐'
        self.datalist = ['排行榜', '艺术家', '新碟上架', '精选歌单', '我的歌单', '主播电台', '每日推荐',
                         '私人FM', '搜索', '帮助']
        self.offset = 0
        self.index = 0
        self.storage = Storage()
        self.storage.load()
        self.collection = self.storage.database['collections'][0]
        self.player = Player()
        self.player.playing_song_changed_callback = self.song_changed_callback
        self.cache = Cache()
        self.ui = Ui()
        self.netease = NetEase()
        self.screen = curses.initscr()
        self.screen.keypad(1)
        self.step = 10
        self.stack = []
        self.djstack = []
        self.userid = self.storage.database['user']['user_id']
        self.username = self.storage.database['user']['nickname']
        self.resume_play = True
        self.at_playing_list = False
        signal.signal(signal.SIGWINCH, self.change_term)
        signal.signal(signal.SIGINT, self.send_kill)
        self.START = time.time()

    def change_term(self, signum, frame):
        self.ui.screen.clear()
        self.ui.screen.refresh()

    def send_kill(self, signum, fram):
        self.player.stop()
        self.cache.quit()
        self.storage.save()
        curses.endwin()
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
            mobilesignin = self.netease.daily_signin(0)
            if mobilesignin != -1 and mobilesignin['code'] not in (-2, 301):
                notify('移动端签到成功', 1)
            time.sleep(0.5)
            pcsignin = self.netease.daily_signin(1)
            if pcsignin != -1 and pcsignin['code'] not in (-2, 301):
                notify('PC端签到成功', 1)
            tree = ET.ElementTree(ET.fromstring(self.netease.get_version()))
            root = tree.getroot()
            return root[0][4][0][0].text
        except (ET.ParseError, TypeError) as e:
            log.error(e)
            return 0

    def start_fork(self, version):
        pid = os.fork()
        if pid == 0:
            Menu().update_alert(version)
        else:
            Menu().start()

    def _is_playlist_empty(self):
        return len(self.storage.database['player_info']['player_list']) == 0

    def play_pause(self):
        if self._is_playlist_empty():
            return
        if self.player.pause_flag:
            self.player.resume()
        else:
            self.player.pause()
        time.sleep(0.1)

    def next_song(self):
        if self._is_playlist_empty():
            return
        self.player.next()
        time.sleep(0.5)

    def previous_song(self):
        if self._is_playlist_empty():
            return
        self.player.prev()
        time.sleep(0.5)

    def bind_keys(self):
        if BINDABLE:
            keybinder.bind(self.config.get_item('global_play_pause'), self.play_pause)  # noqa
            keybinder.bind(self.config.get_item('global_next'), self.next_song)  # noqa
            keybinder.bind(self.config.get_item('global_previous'), self.previous_song)  # noqa

    def unbind_keys(self):
        if BINDABLE:
            keybinder.unbind(self.config.get_item('global_play_pause'))  # noqa
            keybinder.unbind(self.config.get_item('global_next'))  # noqa
            keybinder.unbind(self.config.get_item('global_previous'))  # noqa

    def start(self):
        self.START = time.time() // 1
        self.ui.build_menu(self.datatype, self.title, self.datalist,
                           self.offset, self.index, self.step, self.START)
        self.ui.build_process_bar(
            self.player.process_location, self.player.process_length,
            self.player.playing_flag, self.player.pause_flag,
            self.storage.database['player_info']['playing_mode'])
        self.stack.append([self.datatype, self.title, self.datalist, self.offset, self.index])

        self.bind_keys()  # deprecated keybinder
        show_lyrics_new_process()
        while True:
            datatype = self.datatype
            title = self.title
            datalist = self.datalist
            offset = self.offset
            idx = index = self.index
            step = self.step
            stack = self.stack
            self.screen.timeout(500)
            key = self.screen.getch()
            if BINDABLE:
                keybinder.gtk.main_iteration(False)  # noqa
            self.ui.screen.refresh()

            # term resize
            if key == -1:
                self.player.update_size()

            # 退出
            if key == ord('q'):
                self.unbind_keys()
                break

            # 退出并清除用户信息
            if key == ord('w'):
                self.storage.database['user'] = {
                    'username': '',
                    'password': '',
                    'user_id': '',
                    'nickname': '',
                }
                try:
                    os.remove(self.storage.cookie_path)
                except OSError as e:
                    log.error(e)
                    break
                break

            # 上移
            elif key == ord('k'):
                # turn page if at beginning
                if idx == offset:
                    if offset == 0:
                        continue
                    self.offset -= step
                    # 移动光标到最后一列
                    self.index = offset - 1
                else:
                    self.index = carousel(offset, min(
                        len(datalist), offset + step) - 1, idx - 1)
                self.START = time.time()

            # 下移
            elif key == ord('j'):
                # turn page if at end
                if idx == min(len(datalist), offset + step) - 1:
                    if offset + step >= len(datalist):
                        continue
                    self.offset += step
                    # 移动光标到第一列
                    self.index = offset + step
                else:
                    self.index = carousel(offset, min(
                        len(datalist), offset + step) - 1, idx + 1)
                self.START = time.time()

            # 数字快捷键
            elif ord('0') <= key <= ord('9'):
                idx = key - ord('0')
                self.ui.build_menu(self.datatype, self.title, self.datalist,
                                   self.offset, idx, self.step, self.START)
                self.ui.build_loading()
                self.dispatch_enter(idx)
                self.index = 0
                self.offset = 0

            # 向上翻页
            elif key == ord('u'):
                if offset == 0:
                    continue
                self.START = time.time()
                self.offset -= step

                # e.g. 23 - 10 = 13 --> 10
                self.index = (index - step) // step * step

            # 向下翻页
            elif key == ord('d'):
                if offset + step >= len(datalist):
                    continue
                self.START = time.time()
                self.offset += step

                # e.g. 23 + 10 = 33 --> 30
                self.index = (index + step) // step * step

            # 前进
            elif key == ord('l') or key == 10:
                if len(self.datalist) <= 0:
                    continue
                self.START = time.time()
                self.ui.build_loading()
                self.dispatch_enter(idx)
                self.index = 0
                self.offset = 0

            # 回退
            elif key == ord('h'):
                # if not main menu
                if len(self.stack) == 1:
                    continue
                self.START = time.time()
                up = stack.pop()
                self.datatype = up[0]
                self.title = up[1]
                self.datalist = up[2]
                self.offset = up[3]
                self.index = up[4]
                self.at_playing_list = False

            # 搜索
            elif key == ord('f'):
                # 8 is the 'search' menu
                self.dispatch_enter(8)

            # 播放下一曲
            elif key == ord(']'):
                self.next_song()

            # 播放上一曲
            elif key == ord('['):
                self.previous_song()

            # 增加音量
            elif key == ord('='):
                self.player.volume_up()

            # 减少音量
            elif key == ord('-'):
                self.player.volume_down()

            # 随机播放
            elif key == ord('?'):
                if len(self.storage.database['player_info'][
                        'player_list']) == 0:
                    continue
                self.player.shuffle()
                time.sleep(0.1)

            # 喜爱
            elif key == ord(','):
                return_data = self.request_api(self.netease.fm_like,
                                               self.player.get_playing_id())
                if return_data != -1:
                    song_name = self.player.get_playing_name()
                    notify('%s added successfully!' % song_name, 0)
                else:
                    notify('Adding song failed!', 0)

            # 删除FM
            elif key == ord('.'):
                if self.datatype == 'fmsongs':
                    if len(self.storage.database['player_info'][
                            'player_list']) == 0:
                        continue
                    self.player.next()
                    return_data = self.request_api(
                        self.netease.fm_trash, self.player.get_playing_id())
                    if return_data != -1:
                        notify('Deleted successfully!', 0)
                    time.sleep(0.1)

            # 下一FM
            elif key == ord('/'):
                if self.datatype == 'fmsongs':
                    if len(self.storage.database['player_info'][
                            'player_list']) == 0:
                        continue
                    if self.player.end_callback:
                        self.player.end_callback()
                    time.sleep(0.1)

            # 播放、暂停
            elif key == ord(' '):
                # If not open a new playing list, just play and pause.
                try:
                    if isinstance(self.datalist[idx], dict) and self.datalist[idx]['song_id'] == self.player.playing_id:
                        self.player.play_and_pause(self.storage.database['player_info']['idx'])
                        time.sleep(0.1)
                        continue
                except (TypeError, KeyError) as e:
                    log.error(e)

                # If change to a new playing list. Add playing list and play.
                if datatype == 'songs':
                    self.resume_play = False
                    self.player.new_player_list('songs', self.title,
                                                self.datalist, -1)
                    self.player.end_callback = None
                    self.player.play_and_pause(idx)
                    self.at_playing_list = True
                elif datatype == 'djchannels':
                    self.resume_play = False
                    self.player.new_player_list('djchannels', self.title,
                                                self.datalist, -1)
                    self.player.end_callback = None
                    self.player.play_and_pause(idx)
                    self.at_playing_list = True
                elif datatype == 'fmsongs':
                    self.resume_play = False
                    self.storage.database['player_info']['playing_mode'] = 0
                    self.player.new_player_list('fmsongs', self.title,
                                                self.datalist, -1)
                    self.player.end_callback = self.fm_callback
                    self.player.play_and_pause(idx)
                    self.at_playing_list = True
                else:
                    self.player.play_and_pause(self.storage.database['player_info']['idx'])
                time.sleep(0.1)

            # 加载当前播放列表
            elif key == ord('p'):
                self.show_playing_song()

            # 播放模式切换
            elif key == ord('P'):
                self.storage.database['player_info']['playing_mode'] = (
                    self.storage.database['player_info']['playing_mode'] +
                    1) % 5

            # 进入专辑
            elif key == ord('A'):
                if datatype == 'album':
                    continue
                if datatype in ['songs', 'fmsongs']:
                    song_id = datalist[idx]['song_id']
                    album_id = datalist[idx]['album_id']
                    album_name = datalist[idx]['album_name']
                elif self.player.playing_flag:
                    song_id = self.player.playing_id
                    song_info = self.storage.database['songs'].get(str(song_id), {})
                    album_id = song_info.get('album_id', '')
                    album_name = song_info.get('album_name', '')
                else:
                    album_id = 0
                if album_id:
                    self.stack.append([datatype, title, datalist, offset, index])
                    songs = self.netease.album(album_id)
                    self.datatype = 'songs'
                    self.datalist = self.netease.dig_info(songs, 'songs')
                    self.title = '网易云音乐 > 专辑 > %s' % album_name
                    for i in range(len(self.datalist)):
                        if self.datalist[i]['song_id'] == song_id:
                            self.offset = i - i % step
                            self.index = i
                            break

            # 添加到打碟歌单
            elif key == ord('a'):
                if datatype == 'songs' and len(datalist) != 0:
                    self.djstack.append(datalist[idx])
                elif datatype == 'artists':
                    pass

            # 加载打碟歌单
            elif key == ord('z'):
                self.stack.append([datatype, title, datalist, offset, index])
                self.datatype = 'songs'
                self.title = '网易云音乐 > 打碟'
                self.datalist = self.djstack
                self.offset = 0
                self.index = 0

            # 添加到本地收藏
            elif key == ord('s'):
                if (datatype == 'songs' or
                        datatype == 'djchannels') and len(datalist) != 0:
                    self.collection.append(datalist[idx])
                    notify('Added successfully', 0)

            # 加载本地收藏
            elif key == ord('c'):
                self.stack.append([datatype, title, datalist, offset, index])
                self.datatype = 'songs'
                self.title = '网易云音乐 > 本地收藏'
                self.datalist = self.collection
                self.offset = 0
                self.index = 0

            # 从当前列表移除
            elif key == ord('r'):
                if (datatype in ('songs', 'djchannels', 'fmsongs') and
                        len(datalist) != 0):
                    self.datalist.pop(idx)
                    self.index = carousel(offset, min(
                        len(datalist), offset + step) - 1, idx)

            # 当前项目下移
            elif key == ord('J'):
                if datatype != 'main' and len(
                        datalist) != 0 and idx + 1 != len(self.datalist):
                    self.START = time.time()
                    song = self.datalist.pop(idx)
                    self.datalist.insert(idx + 1, song)
                    self.index = idx + 1
                    # 翻页
                    if self.index >= offset + step:
                        self.offset = offset + step

            # 当前项目上移
            elif key == ord('K'):
                if datatype != 'main' and len(datalist) != 0 and idx != 0:
                    self.START = time.time()
                    song = self.datalist.pop(idx)
                    self.datalist.insert(idx - 1, song)
                    self.index = idx - 1
                    # 翻页
                    if self.index < offset:
                        self.offset = offset - step

            elif key == ord('m'):
                if datatype != 'main':
                    self.stack.append([datatype, title, datalist, offset, index
                                       ])
                    self.datatype = self.stack[0][0]
                    self.title = self.stack[0][1]
                    self.datalist = self.stack[0][2]
                    self.offset = 0
                    self.index = 0

            elif key == ord('g'):
                if datatype == 'help':
                    webbrowser.open_new_tab(
                        'https://github.com/darknessomi/musicbox')
                else:
                    self.index = 0
                    self.offset = 0

            elif key == ord('G'):
                self.index = len(self.datalist) - 1
                self.offset = self.index - self.index % step

            # 开始下载
            elif key == ord('C'):
                s = self.datalist[idx]
                cache_thread = threading.Thread(
                    target=self.player.cacheSong1time,
                    args=(s['song_id'], s['song_name'], s['artist'], s[
                        'mp3_url']))
                cache_thread.start()

            elif key == ord('i'):
                if self.player.playing_id != -1:
                    webbrowser.open_new_tab('http://music.163.com/song?id=' +
                                            str(self.player.playing_id))

            self.ui.build_process_bar(
                self.player.process_location, self.player.process_length,
                self.player.playing_flag, self.player.pause_flag,
                self.storage.database['player_info']['playing_mode'])
            self.ui.build_menu(self.datatype, self.title, self.datalist,
                               self.offset, self.index, self.step, self.START)

        self.player.stop()
        self.cache.quit()
        self.storage.save()
        curses.endwin()

    def dispatch_enter(self, idx):
        # The end of stack
        netease = self.netease
        datatype = self.datatype
        title = self.title
        datalist = self.datalist
        offset = self.offset
        index = self.index
        self.stack.append([datatype, title, datalist, offset, index])

        if idx > len(self.datalist):
            return False

        if datatype == 'main':
            self.choice_channel(idx)

        # 该艺术家的热门歌曲
        elif datatype == 'artists':
            artist_name = datalist[idx]['artists_name']
            artist_id = datalist[idx]['artist_id']

            self.datatype = 'artist_info'
            self.title += ' > ' + artist_name
            self.datalist = [
                {
                    'item': '{}的热门歌曲'.format(artist_name),
                    'id': artist_id,
                }, {
                    'item': '{}的所有专辑'.format(artist_name),
                    'id': artist_id,
                }
            ]

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

        # 该专辑包含的歌曲
        elif datatype == 'albums':
            album_id = datalist[idx]['album_id']
            songs = netease.album(album_id)
            self.datatype = 'songs'
            self.datalist = netease.dig_info(songs, 'songs')
            self.title += ' > ' + datalist[idx]['albums_name']

        # 精选歌单选项
        elif datatype == 'playlists':
            data = self.datalist[idx]
            self.datatype = data['datatype']
            self.datalist = netease.dig_info(data['callback'](), self.datatype)
            self.title += ' > ' + data['title']

        # 全站置顶歌单包含的歌曲
        elif datatype == 'top_playlists':
            playlist_id = datalist[idx]['playlist_id']
            songs = netease.playlist_detail(playlist_id)
            self.datatype = 'songs'
            self.datalist = netease.dig_info(songs, 'songs')
            self.title += ' > ' + datalist[idx]['playlists_name']

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
            self.datalist = netease.dig_info(
                netease.top_playlists(data), self.datatype)
            self.title += ' > ' + data

        # 歌曲评论
        elif datatype in ['songs', 'fmsongs']:
            song_id = datalist[idx]['song_id']
            comments = self.netease.song_comments(song_id, limit=100)
            try:
                hotcomments = comments['hotComments']
                comcomments = comments['comments']
            except KeyError:
                hotcomments = comcomments = []
            self.datalist = []
            for one_comment in hotcomments:
                self.datalist.append(
                    u'(热门评论)%s:%s' % (one_comment['user']['nickname'],
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
            ui = self.ui
            self.index = 0
            self.offset = 0
            if idx == 0:
                # 搜索结果可以用top_playlists处理
                self.datatype = 'top_playlists'
                self.datalist = ui.build_search('search_playlist')
                self.title = '精选歌单搜索列表'

            elif idx == 1:
                self.datatype = 'songs'
                self.datalist = ui.build_search('songs')
                self.title = '歌曲搜索列表'

            elif idx == 2:
                self.datatype = 'artists'
                self.datalist = ui.build_search('artists')
                self.title = '艺术家搜索列表'

            elif idx == 3:
                self.datatype = 'albums'
                self.datalist = ui.build_search('albums')
                self.title = '专辑搜索列表'

    def show_playing_song(self):
        if self._is_playlist_empty():
            return
        if not self.at_playing_list:
            self.stack.append([self.datatype, self.title, self.datalist,
                               self.offset, self.index])
            self.at_playing_list = True
        self.datatype = self.storage.database['player_info'][
            'player_list_type']
        self.title = self.storage.database['player_info']['player_list_title']
        self.datalist = []
        for i in self.storage.database['player_info']['player_list']:
            self.datalist.append(self.storage.database['songs'][i])
        self.index = self.storage.database['player_info']['idx']
        self.offset = self.storage.database[
            'player_info']['idx'] // self.step * self.step
        if self.resume_play:
            if self.datatype == 'fmsongs':
                self.player.end_callback = self.fm_callback
            else:
                self.player.end_callback = None
            self.storage.database['player_info']['idx'] = -1
            self.player.play_and_pause(self.index)
            self.resume_play = False

    def song_changed_callback(self):
        if self.at_playing_list:
            self.show_playing_song()

    def fm_callback(self):
        log.debug('FM CallBack.')
        data = self.get_new_fm()
        self.player.append_songs(data)
        if self.datatype == 'fmsongs':
            if self._is_playlist_empty():
                return
            self.datatype = self.storage.database['player_info'][
                'player_list_type']
            self.title = self.storage.database['player_info'][
                'player_list_title']
            self.datalist = []
            for i in self.storage.database['player_info']['player_list']:
                self.datalist.append(self.storage.database['songs'][i])
            self.index = self.storage.database['player_info']['idx']
            self.offset = self.storage.database['player_info'][
                'idx'] // self.step * self.step

    def request_api(self, func, *args):
        if self.storage.database['user']['user_id'] != '':
            result = func(*args)
            if result != -1:
                return result
        notify('You need to log in')
        user_info = {}
        if self.storage.database['user']['username'] != '':
            user_info = self.netease.login(
                self.storage.database['user']['username'],
                self.storage.database['user']['password'])
        if self.storage.database['user']['username'] == '' or user_info['code'] != 200:
            data = self.ui.build_login()
            # 取消登录
            if data == -1:
                return -1
            user_info = data[0]
            self.storage.database['user']['username'] = data[1][0]
            self.storage.database['user']['password'] = data[1][1]
            self.storage.database['user']['user_id'] = user_info['account']['id']
            self.storage.database['user']['nickname'] = user_info['profile']['nickname']
        self.userid = self.storage.database['user']['user_id']
        self.username = self.storage.database['user']['nickname']
        return func(*args)

    def get_new_fm(self):
        myplaylist = []
        for count in range(0, 1):
            data = self.request_api(self.netease.personal_fm)
            if data == -1:
                break
            myplaylist += data
            time.sleep(0.2)
        return self.netease.dig_info(myplaylist, 'fmsongs')

    def choice_channel(self, idx):
        # 排行榜
        netease = self.netease
        if idx == 0:
            self.datalist = netease.return_toplists()
            self.title += ' > 排行榜'
            self.datatype = 'toplists'

        # 艺术家
        elif idx == 1:
            artists = netease.top_artists()
            self.datalist = netease.dig_info(artists, 'artists')
            self.title += ' > 艺术家'
            self.datatype = 'artists'

        # 新碟上架
        elif idx == 2:
            albums = netease.new_albums()
            self.datalist = netease.dig_info(albums, 'albums')
            self.title += ' > 新碟上架'
            self.datatype = 'albums'

        # 精选歌单
        elif idx == 3:
            self.datalist = [
                {
                    'title': '全站置顶',
                    'datatype': 'top_playlists',
                    'callback': netease.top_playlists
                }, {
                    'title': '分类精选',
                    'datatype': 'playlist_classes',
                    'callback': netease.playlist_classes
                }
            ]
            self.title += ' > 精选歌单'
            self.datatype = 'playlists'

        # 我的歌单
        elif idx == 4:
            myplaylist = self.request_api(self.netease.user_playlist, self.userid)
            if myplaylist == -1:
                return
            self.datatype = 'top_playlists'
            self.datalist = netease.dig_info(myplaylist, self.datatype)
            self.title += ' > ' + self.username + ' 的歌单'

        # 主播电台
        elif idx == 5:
            self.datatype = 'djchannels'
            self.title += ' > 主播电台'
            self.datalist = netease.djchannels()

        # 每日推荐
        elif idx == 6:
            self.datatype = 'songs'
            self.title += ' > 每日推荐'
            myplaylist = self.request_api(self.netease.recommend_playlist)
            if myplaylist == -1:
                return
            self.datalist = self.netease.dig_info(myplaylist, self.datatype)

        # 私人FM
        elif idx == 7:
            self.datatype = 'fmsongs'
            self.title += ' > 私人FM'
            self.datalist = self.get_new_fm()

        # 搜索
        elif idx == 8:
            self.datatype = 'search'
            self.title += ' > 搜索'
            self.datalist = ['歌曲', '艺术家', '专辑', '网易精选集']

        # 帮助
        elif idx == 9:
            self.datatype = 'help'
            self.title += ' > 帮助'
            self.datalist = shortcut

        self.offset = 0
        self.index = 0
