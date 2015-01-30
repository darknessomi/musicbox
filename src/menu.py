#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57
# @Last Modified by:   omi
# @Last Modified time: 2014-08-25 18:02:04


'''
网易云音乐 Menu
'''

import curses
import locale
import sys
import os
import json
import time
import webbrowser
from api import NetEase
from player import Player
from ui import Ui
from const import Constant
import logger

home = os.path.expanduser("~")
if os.path.isdir(Constant.conf_dir) is False:
    os.mkdir(Constant.conf_dir)

locale.setlocale(locale.LC_ALL, "")
code = locale.getpreferredencoding()

# carousel x in [left, right]
carousel = lambda left, right, x: left if (x > right) else (right if x < left else x)

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
    ['?', 'Shuffle   ', '手气不错'],
    ['=', 'Volume+   ', '音量增加'],
    ['-', 'Volume-   ', '音量减少'],
    ['m', 'Menu      ', '主菜单'],
    ['p', 'Present   ', '当前播放列表'],
    ['a', 'Add       ', '添加曲目到打碟'],
    ['z', 'DJ list   ', '打碟列表'],
    ['s', 'Star      ', '添加到收藏'],
    ['c', 'Collection', '收藏列表'],
    ['r', 'Remove    ', '删除当前条目'],
    ['q', 'Quit      ', '退出'],
    ["w", 'Quit&Clear', '退出并清除用户信息']
]

log = logger.getLogger(__name__)


class Menu:
    def __init__(self):
        reload(sys)
        sys.setdefaultencoding('UTF-8')
        self.datatype = 'main'
        self.title = '网易云音乐'
        self.datalist = ['排行榜', '艺术家', '新碟上架', '精选歌单', '我的歌单', 'DJ节目', '打碟', '收藏', '搜索', '帮助']
        self.offset = 0
        self.index = 0
        self.presentsongs = []
        self.player = Player()
        self.ui = Ui()
        self.netease = NetEase()
        self.screen = curses.initscr()
        self.screen.keypad(1)
        self.step = 10
        self.stack = []
        self.djstack = []
        self.userid = None
        self.username = None
        signal.signal(signal.SIGWINCH, self.change_term)
        try:
            sfile = file(Constant.conf_dir + "/flavor.json", 'r')
            data = json.loads(sfile.read())
            self.collection = data['collection']
            self.account = data['account']
            sfile.close()
        except:
            self.collection = []
            self.account = {}
                
    def change_term(self,signum, frame):
        self.ui.screen.clear()
        self.ui.screen.refresh()

    def start(self):
        self.ui.build_menu(self.datatype, self.title, self.datalist, self.offset, self.index, self.step)
        self.stack.append([self.datatype, self.title, self.datalist, self.offset, self.index])
        while True:
            datatype = self.datatype
            title = self.title
            datalist = self.datalist
            offset = self.offset
            idx = index = self.index
            step = self.step
            stack = self.stack
            djstack = self.djstack
            key = self.screen.getch()
            self.ui.screen.refresh()

            # 退出
            if key == ord('q'):
                break

            # 退出并清除用户信息
            if key == ord('w'):
                self.account = {}
                break

            # 上移
            elif key == ord('k'):
                self.index = carousel(offset, min(len(datalist), offset + step) - 1, idx - 1)

            # 下移
            elif key == ord('j'):
                self.index = carousel(offset, min(len(datalist), offset + step) - 1, idx + 1)

            # 数字快捷键
            elif ord('0') <= key <= ord('9'):
                if self.datatype == 'songs' or self.datatype == 'djchannels' or self.datatype == 'help':
                    continue
                idx = key - ord('0')
                self.ui.build_menu(self.datatype, self.title, self.datalist, self.offset, idx, self.step)
                self.ui.build_loading()
                self.dispatch_enter(idx)
                self.index = 0
                self.offset = 0

            # 向上翻页
            elif key == ord('u'):
                if offset == 0:
                    continue
                self.offset -= step

                # e.g. 23 - 10 = 13 --> 10
                self.index = (index - step) // step * step

            # 向下翻页
            elif key == ord('d'):
                if offset + step >= len(datalist):
                    continue
                self.offset += step

                # e.g. 23 + 10 = 33 --> 30
                self.index = (index + step) // step * step

            # 前进
            elif key == ord('l') or key == 10:
                if self.datatype == 'songs' or self.datatype == 'djchannels' or self.datatype == 'help':
                    continue
                self.ui.build_loading()
                self.dispatch_enter(idx)
                self.index = 0
                self.offset = 0

            # 回退
            elif key == ord('h'):
                # if not main menu
                if len(self.stack) == 1:
                    continue
                up = stack.pop()
                self.datatype = up[0]
                self.title = up[1]
                self.datalist = up[2]
                self.offset = up[3]
                self.index = up[4]

            # 搜索
            elif key == ord('f'):
                # 8 is the 'search' menu
                self.dispatch_enter(8)

            # 播放下一曲
            elif key == ord(']'):
                if len(self.presentsongs) == 0:
                    continue
                self.player.next()
                time.sleep(0.1)

            # 播放上一曲
            elif key == ord('['):
                if len(self.presentsongs) == 0:
                    continue
                self.player.prev()
                time.sleep(0.1)

            # 增加音量
            elif key == ord('='):
                if len(self.presentsongs) == 0:
                    continue
                self.player.volume_up()

            # 减少音量
            elif key == ord('-'):
                if len(self.presentsongs) == 0:
                    continue
                self.player.volume_down()

            # 随机播放
            elif key == ord('?'):
                if len(self.presentsongs) == 0:
                    continue
                self.player.shuffle()
                time.sleep(0.1)

            # 播放、暂停
            elif key == ord(' '):
                if datatype == 'songs':
                    self.presentsongs = ['songs', title, datalist, offset, index]
                elif datatype == 'djchannels':
                    self.presentsongs = ['djchannels', title, datalist, offset, index]
                self.player.play(datatype, datalist, idx)
                time.sleep(0.1)

            # 加载当前播放列表
            elif key == ord('p'):
                if len(self.presentsongs) == 0:
                    continue
                self.stack.append([datatype, title, datalist, offset, index])
                self.datatype = self.presentsongs[0]
                self.title = self.presentsongs[1]
                self.datalist = self.presentsongs[2]
                self.offset = self.presentsongs[3]
                self.index = self.presentsongs[4]

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

            # 添加到收藏歌曲
            elif key == ord('s'):
                if (datatype == 'songs' or datatype == 'djchannels') and len(datalist) != 0:
                    self.collection.append(datalist[idx])

            # 加载收藏歌曲
            elif key == ord('c'):
                self.stack.append([datatype, title, datalist, offset, index])
                self.datatype = 'songs'
                self.title = '网易云音乐 > 收藏'
                self.datalist = self.collection
                self.offset = 0
                self.index = 0

            # 从当前列表移除
            elif key == ord('r'):
                if datatype != 'main' and len(datalist) != 0:
                    self.datalist.pop(idx)
                    self.index = carousel(offset, min(len(datalist), offset + step) - 1, idx)

            elif key == ord('m'):
                if datatype != 'main':
                    self.stack.append([datatype, title, datalist, offset, index])
                    self.datatype = self.stack[0][0]
                    self.title = self.stack[0][1]
                    self.datalist = self.stack[0][2]
                    self.offset = 0
                    self.index = 0

            elif key == ord('g'):
                if datatype == 'help':
                    webbrowser.open_new_tab('https://github.com/darknessomi/musicbox')

            self.ui.build_menu(self.datatype, self.title, self.datalist, self.offset, self.index, self.step)

        self.player.stop()
        sfile = file(Constant.conf_dir + "/flavor.json", 'w')
        data = {
            'account': self.account,
            'collection': self.collection
        }
        sfile.write(json.dumps(data))
        sfile.close()
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

        if datatype == 'main':
            self.choice_channel(idx)

        # 该艺术家的热门歌曲
        elif datatype == 'artists':
            artist_id = datalist[idx]['artist_id']
            songs = netease.artists(artist_id)
            self.datatype = 'songs'
            self.datalist = netease.dig_info(songs, 'songs')
            self.title += ' > ' + datalist[idx]['artists_name']

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
            log.debug(datalist)
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
            log.debug(self.datalist)

        # 某一分类的详情
        elif datatype == 'playlist_class_detail':
            # 子类别
            data = self.datalist[idx]
            self.datatype = 'top_playlists'
            self.datalist = netease.dig_info(netease.top_playlists(data), self.datatype)
            log.debug(self.datalist)
            self.title += ' > ' + data

        # 搜索菜单
        elif datatype == 'search':
            ui = self.ui
            # no need to do stack.append, Otherwise there will be a bug when you input key 'h' to return
            # if idx in range(1, 5):
            #    self.stack.append([self.datatype, self.title, self.datalist, self.offset, self.index])
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


    def choice_channel(self, idx):
        # 排行榜
        netease = self.netease
        if idx == 0:
            songs = netease.top_songlist()
            self.datalist = netease.dig_info(songs, 'songs')
            self.title += ' > 排行榜'
            self.datatype = 'songs'

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
                },
                {
                    'title': '分类精选',
                    'datatype': 'playlist_classes',
                    'callback': netease.playlist_classes
                }
            ]
            self.title += ' > 精选歌单'
            self.datatype = 'playlists'

        # 我的歌单
        elif idx == 4:
            # 未登录
            if self.userid is None:
                # 使用本地存储了账户登录
                if self.account:
                    user_info = netease.login(self.account[0], self.account[1])

                # 本地没有存储账户，或本地账户失效，则引导录入
                if self.account == {} or user_info['code'] != 200:
                    data = self.ui.build_login()
                    # 取消登录
                    if data == -1:
                        return
                    user_info = data[0]
                    self.account = data[1]

                self.username = user_info['profile']['nickname']
                self.userid = user_info['account']['id']
            # 读取登录之后的用户歌单
            myplaylist = netease.user_playlist(self.userid)
            self.datatype = 'top_playlists'
            self.datalist = netease.dig_info(myplaylist, self.datatype)
            self.title += ' > ' + self.username + ' 的歌单'

        # DJ节目
        elif idx == 5:
            self.datatype = 'djchannels'
            self.title += ' > DJ节目'
            self.datalist = netease.djchannels()

        # 打碟
        elif idx == 6:
            self.datatype = 'songs'
            self.title += ' > 打碟'
            self.datalist = self.djstack

        # 收藏
        elif idx == 7:
            self.datatype = 'songs'
            self.title += ' > 收藏'
            self.datalist = self.collection

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

