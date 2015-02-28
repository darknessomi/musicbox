#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57
# @Last Modified by:   omi
# @Last Modified time: 2015-01-30 18:02:34


'''
网易云音乐 Ui
'''

import curses
from api import NetEase


class Ui:
    def __init__(self):
        self.screen = curses.initscr()
        # charactor break buffer
        curses.cbreak()
        self.screen.keypad(1)
        self.netease = NetEase()
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)


    def build_playinfo(self, song_name, artist, album_name, pause=False):
        curses.noecho()
        # refresh top 2 line
        self.screen.move(1, 1)
        self.screen.clrtoeol()
        self.screen.move(2, 1)
        self.screen.clrtoeol()
        if pause:
            self.screen.addstr(1, 6, '_ _ z Z Z', curses.color_pair(3))
        else:
            self.screen.addstr(1, 6, '♫  ♪ ♫  ♪', curses.color_pair(3))
        self.screen.addstr(1, 19, song_name + '   -   ' + artist + '  < ' + album_name + ' >', curses.color_pair(4))
        self.screen.refresh()

    def build_loading(self):
        self.screen.addstr(6, 19, '享受高品质音乐，loading...', curses.color_pair(1))
        self.screen.refresh()


    def build_menu(self, datatype, title, datalist, offset, index, step):
        # keep playing info in line 1
        curses.noecho()
        self.screen.move(4, 1)
        self.screen.clrtobot()
        self.screen.addstr(4, 19, title, curses.color_pair(1))

        if len(datalist) == 0:
            self.screen.addstr(8, 19, '这里什么都没有 -，-')

        else:
            if datatype == 'main':
                for i in range(offset, min(len(datalist), offset + step)):
                    if i == index:
                        self.screen.addstr(i - offset + 8, 16, '-> ' + str(i) + '. ' + datalist[i],
                                           curses.color_pair(2))
                    else:
                        self.screen.addstr(i - offset + 8, 19, str(i) + '. ' + datalist[i])

            elif datatype == 'songs':
                for i in range(offset, min(len(datalist), offset + step)):
                    # this item is focus
                    if i == index:
                        self.screen.addstr(i - offset + 8, 16,
                                           '-> ' + str(i) + '. ' + datalist[i]['song_name'] + '   -   ' + datalist[i][
                                               'artist'] + '  < ' + datalist[i]['album_name'] + ' >',
                                           curses.color_pair(2))
                    else:
                        self.screen.addstr(i - offset + 8, 19,
                                           str(i) + '. ' + datalist[i]['song_name'] + '   -   ' + datalist[i][
                                               'artist'] + '  < ' + datalist[i]['album_name'] + ' >')

            elif datatype == 'artists':
                for i in range(offset, min(len(datalist), offset + step)):
                    if i == index:
                        self.screen.addstr(i - offset + 8, 16,
                                           '-> ' + str(i) + '. ' + datalist[i]['artists_name'] + '   -   ' + str(
                                               datalist[i]['alias']), curses.color_pair(2))
                    else:
                        self.screen.addstr(i - offset + 8, 19,
                                           str(i) + '. ' + datalist[i]['artists_name'] + '   -   ' + datalist[i][
                                               'alias'])

            elif datatype == 'albums':
                for i in range(offset, min(len(datalist), offset + step)):
                    if i == index:
                        self.screen.addstr(i - offset + 8, 16,
                                           '-> ' + str(i) + '. ' + datalist[i]['albums_name'] + '   -   ' + datalist[i][
                                               'artists_name'], curses.color_pair(2))
                    else:
                        self.screen.addstr(i - offset + 8, 19,
                                           str(i) + '. ' + datalist[i]['albums_name'] + '   -   ' + datalist[i][
                                               'artists_name'])

            elif datatype == 'playlists':
                for i in range(offset, min(len(datalist), offset + step)):
                    if i == index:
                        self.screen.addstr(i - offset + 8, 16, '-> ' + str(i) + '. ' + datalist[i]['title'],
                                           curses.color_pair(2))
                    else:
                        self.screen.addstr(i - offset + 8, 19, str(i) + '. ' + datalist[i]['title'])


            elif datatype == 'top_playlists':
                for i in range(offset, min(len(datalist), offset + step)):
                    if i == index:
                        self.screen.addstr(i - offset + 8, 16,
                                           '-> ' + str(i) + '. ' + datalist[i]['playlists_name'] + '   -   ' +
                                           datalist[i]['creator_name'], curses.color_pair(2))
                    else:
                        self.screen.addstr(i - offset + 8, 19,
                                           str(i) + '. ' + datalist[i]['playlists_name'] + '   -   ' + datalist[i][
                                               'creator_name'])

            elif datatype == 'playlist_classes' or datatype == 'playlist_class_detail':
                for i in range(offset, min(len(datalist), offset + step)):
                    if i == index:
                        self.screen.addstr(i - offset + 8, 16, '-> ' + str(i) + '. ' + datalist[i],
                                           curses.color_pair(2))
                    else:
                        self.screen.addstr(i - offset + 8, 19, str(i) + '. ' + datalist[i])

            elif datatype == 'djchannels':
                for i in range(offset, min(len(datalist), offset + step)):
                    if i == index:
                        self.screen.addstr(i - offset + 8, 16, '-> ' + str(i) + '. ' + datalist[i]['song_name'],
                                           curses.color_pair(2))
                    else:
                        self.screen.addstr(i - offset + 8, 19, str(i) + '. ' + datalist[i]['song_name'])

            elif datatype == 'search':
                self.screen.move(4, 1)
                self.screen.clrtobot()
                self.screen.addstr(8, 19, '选择搜索类型:', curses.color_pair(1))
                for i in range(offset, min(len(datalist), offset + step)):
                    if i == index:
                        self.screen.addstr(i - offset + 10, 16, '-> ' + str(i) + '.' + datalist[i - 1],
                                           curses.color_pair(2))
                    else:
                        self.screen.addstr(i - offset + 10, 19, str(i) + '.' + datalist[i - 1])
            elif datatype == 'help':
                for i in range(offset, min(len(datalist), offset + step)):
                    if i == index:
                        self.screen.addstr(i - offset + 8, 16,
                                           '-> ' + str(i) + '. \'' + datalist[i][0].upper() + '\'   ' + datalist[i][
                                               1] + '   ' + datalist[i][2], curses.color_pair(2))
                    else:
                        self.screen.addstr(i - offset + 8, 19,
                                           str(i) + '. \'' + datalist[i][0].upper() + '\'   ' + datalist[i][1] + '   ' +
                                           datalist[i][2])
                self.screen.addstr(20, 6, 'NetEase-MusicBox 基于Python，所有版权音乐来源于网易，本地不做任何保存')
                self.screen.addstr(21, 10, '按 [G] 到 Github 了解更多信息，帮助改进，或者Star表示支持~~')
                self.screen.addstr(22, 19, 'Build with love to music by omi')

        self.screen.refresh()

    def build_search(self, stype):
        netease = self.netease
        if stype == 'songs':
            song_name = self.get_param('搜索歌曲：')
            try:
                data = netease.search(song_name, stype=1)
                song_ids = []
                if 'songs' in data['result']:
                    if 'mp3Url' in data['result']['songs']:
                        songs = data['result']['songs']

                    # if search song result do not has mp3Url
                    # send ids to get mp3Url
                    else:
                        for i in range(0, len(data['result']['songs'])):
                            song_ids.append(data['result']['songs'][i]['id'])
                        songs = netease.songs_detail(song_ids)
                    return netease.dig_info(songs, 'songs')
            except:
                return []

        elif stype == 'artists':
            artist_name = self.get_param('搜索艺术家：')
            try:
                data = netease.search(artist_name, stype=100)
                if 'artists' in data['result']:
                    artists = data['result']['artists']
                    return netease.dig_info(artists, 'artists')
            except:
                return []

        elif stype == 'albums':
            artist_name = self.get_param('搜索专辑：')
            try:
                data = netease.search(artist_name, stype=10)
                if 'albums' in data['result']:
                    albums = data['result']['albums']
                    return netease.dig_info(albums, 'albums')
            except:
                return []

        elif stype == 'search_playlist':
            artist_name = self.get_param('搜索网易精选集：')
            try:
                data = netease.search(artist_name, stype=1000)
                if 'playlists' in data['result']:
                    playlists = data['result']['playlists']
                    return netease.dig_info(playlists, 'top_playlists')
            except:
                return []

        return []

    def build_choose_login_mehod(self):
        self.screen.move(4, 1)
        self.screen.clrtobot()
        self.screen.addstr(8, 19, '请选择登录方式', curses.color_pair(1))
        self.screen.addstr(10, 19, '[1] 手机号码登录')
        self.screen.addstr(11, 19, '[2] 其他登录方式')
        self.screen.addstr(14, 19, '请键入对应数字:', curses.color_pair(2))
        self.screen.refresh()
        x = self.screen.getch()
        return x

    def build_login(self):
        x = self.build_choose_login_mehod()

        self.build_login_bar()
        local_account = self.get_account()
        local_password = self.get_password()
        if x == ord("1") :
            login_info = self.netease.phone_login(local_account, local_password)
        else :
            login_info = self.netease.login(local_account, local_password)
        account = [local_account,local_password]
        if login_info['code'] != 200:
            x = self.build_login_error()
            if x == ord('1'):
                return self.build_login()
            else:
                return -1
        else:
            return [login_info, account]

    def build_login_bar(self):
        curses.noecho()
        self.screen.move(4, 1)
        self.screen.clrtobot()
        self.screen.addstr(5, 19, '请输入登录信息',curses.color_pair(1))
        self.screen.addstr(8, 19, "账号:", curses.color_pair(1))
        self.screen.addstr(9, 19, "密码:", curses.color_pair(1))
        self.screen.move(8,24)
        self.screen.refresh()

    def build_login_error(self):
        self.screen.move(4, 1)
        self.screen.clrtobot()
        self.screen.addstr(8, 19, '艾玛，登录信息好像不对呢 (O_O)#', curses.color_pair(1))
        self.screen.addstr(10, 19, '[1] 再试一次')
        self.screen.addstr(11, 19, '[2] 稍后再试')
        self.screen.addstr(14, 19, '请键入对应数字:', curses.color_pair(2))
        self.screen.refresh()
        x = self.screen.getch()
        return x

    def get_account(self):
        curses.echo()
        account = self.screen.getstr(8,24,60)
        return account

    def get_password(self):
        curses.noecho()
        password = self.screen.getstr(9,24,60)
        return password

    def get_param(self, prompt_string):
        # keep playing info in line 1
        curses.echo()
        self.screen.move(4, 1)
        self.screen.clrtobot()
        self.screen.addstr(5, 19, prompt_string, curses.color_pair(1))
        self.screen.refresh()
        info = self.screen.getstr(10, 19, 60)
        if info.strip() is '':
            return self.get_param(prompt_string)
        else:
            return info
