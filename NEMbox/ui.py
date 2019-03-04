#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57
"""
网易云音乐 Ui
"""
from __future__ import print_function, unicode_literals, division, absolute_import

import hashlib
import re
import curses
import datetime

from future.builtins import range, str, int

from .scrollstring import truelen, scrollstring
from .storage import Storage
from .config import Config

from . import logger
from . import terminalsize

log = logger.getLogger(__name__)

try:
    import dbus

    dbus_activity = True
except ImportError:
    dbus_activity = False
    log.warn("Qt dbus module is not installed.")
    log.warn("Osdlyrics is not available.")


def break_str(s, start, max_len=80):
    length = len(s)
    i, x = 0, max_len
    res = []
    while i < length:
        res.append(s[i : i + max_len])
        i += x
    return "\n{}".format(" " * start).join(res)


class Ui(object):
    def __init__(self):
        self.screen = curses.initscr()
        self.screen.timeout(100)  # the screen refresh every 100ms
        # charactor break buffer
        curses.cbreak()
        self.screen.keypad(1)

        curses.start_color()
        if Config().get("curses_transparency"):
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_CYAN, -1)
            curses.init_pair(3, curses.COLOR_RED, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
        else:
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        # term resize handling
        size = terminalsize.get_terminal_size()
        self.x = max(size[0], 10)
        self.y = max(size[1], 25)
        self.startcol = int(float(self.x) / 5)
        self.indented_startcol = max(self.startcol - 3, 0)
        self.update_space()
        self.lyric = ""
        self.now_lyric = ""
        self.post_lyric = ""
        self.now_lyric_index = 0
        self.tlyric = ""
        self.storage = Storage()
        self.config = Config()
        self.newversion = False

    def addstr(self, *args):
        if len(args) == 1:
            self.screen.addstr(args[0])
        else:
            try:
                self.screen.addstr(args[0], args[1], args[2].encode("utf-8"), *args[3:])
            except Exception as e:
                log.error(e)

    def build_playinfo(
        self, song_name, artist, album_name, quality, start, pause=False
    ):
        curses.noecho()
        # refresh top 2 line
        self.screen.move(1, 1)
        self.screen.clrtoeol()
        self.screen.move(2, 1)
        self.screen.clrtoeol()
        if pause:
            self.addstr(
                1, self.indented_startcol, "_ _ z Z Z " + quality, curses.color_pair(3)
            )
        else:
            self.addstr(
                1, self.indented_startcol, "♫  ♪ ♫  ♪ " + quality, curses.color_pair(3)
            )

        self.addstr(
            1,
            min(self.indented_startcol + 18, self.x - 1),
            song_name + self.space + artist + "  < " + album_name + " >",
            curses.color_pair(4),
        )

        self.screen.refresh()

    def build_process_bar(
        self, song, now_playing, total_length, playing_flag, playing_mode
    ):

        if not song or not playing_flag:
            return
        name, artist = song["song_name"], song["artist"]
        lyrics, tlyrics = song.get("lyric", []), song.get("tlyric", [])

        curses.noecho()
        self.screen.move(3, 1)
        self.screen.clrtoeol()
        self.screen.move(4, 1)
        self.screen.clrtoeol()
        self.screen.move(5, 1)
        self.screen.clrtoeol()
        if total_length <= 0:
            total_length = 1
        if now_playing > total_length or now_playing <= 0:
            now_playing = 0
        if now_playing == 0:
            self.now_lyric_index = 0
            self.now_lyric = ""
            self.post_lyric = ""
        process = "["
        for i in range(0, 33):
            if i < now_playing / total_length * 33:
                if (i + 1) > now_playing / total_length * 33:
                    if playing_flag:
                        process += ">"
                        continue
                process += "="
            else:
                process += " "
        process += "] "

        now = str(datetime.timedelta(seconds=now_playing)).lstrip("0").lstrip(":")
        total = str(datetime.timedelta(seconds=total_length)).lstrip("0").lstrip(":")
        process += "({}/{})".format(now, total)

        if playing_mode == 0:
            process = "顺序播放 " + process
        elif playing_mode == 1:
            process = "顺序循环 " + process
        elif playing_mode == 2:
            process = "单曲循环 " + process
        elif playing_mode == 3:
            process = "随机播放 " + process
        elif playing_mode == 4:
            process = "随机循环 " + process
        else:
            pass
        self.addstr(3, self.startcol - 2, process, curses.color_pair(1))
        if not lyrics:
            self.now_lyric = "暂无歌词 ~>_<~ \n"
            self.post_lyric = ""
            if dbus_activity and self.config.get("osdlyrics"):
                self.now_playing = "{} - {}\n".format(name, artist)

        else:
            key = now
            index = 0
            for line in lyrics:
                if key in line:
                    # 计算下一句歌词，判断刷新时的歌词和上一次是否相同来进行index计算
                    if not (self.now_lyric == re.sub("\[.*?\]", "", line)):
                        self.now_lyric_index = self.now_lyric_index + 1
                    if index < len(lyrics) - 1:
                        self.post_lyric = lyrics[index + 1]
                    else:
                        self.post_lyric = ""
                    if not tlyrics:
                        self.now_lyric = line
                    else:
                        self.now_lyric = line
                        for tindex, tline in enumerate(tlyrics):
                            if key in tline and self.config.get("translation"):
                                self.now_lyric = tline + " || " + self.now_lyric
                                if (
                                    not (self.post_lyric == "")
                                    and tindex < len(tlyrics) - 1
                                ):
                                    self.post_lyric = (
                                        tlyrics[tindex + 1] + " || " + self.post_lyric
                                    )
                                # 此处已经拿到，直接break即可
                                break
                    # 此处已经拿到，直接break即可
                    break
                index += 1
        self.now_lyric = re.sub("\[.*?\]", "", self.now_lyric)
        self.post_lyric = re.sub("\[.*?\]", "", self.post_lyric)
        if dbus_activity and self.config.get("osdlyrics"):
            try:
                bus = dbus.SessionBus().get_object("org.musicbox.Bus", "/")
                # TODO 环境问题，没有试过桌面歌词，此处需要了解的人加个刷界面操作
                if self.now_lyric == "暂无歌词 ~>_<~ \n":
                    bus.refresh_lyrics(
                        self.now_playing, dbus_interface="local.musicbox.Lyrics"
                    )
                else:
                    bus.refresh_lyrics(
                        self.now_lyric, dbus_interface="local.musicbox.Lyrics"
                    )
            except Exception as e:
                log.error(e)
                pass
        # 根据索引计算双行歌词的显示，其中当前歌词颜色为红色，下一句歌词颜色为白色；
        # 当前歌词从下一句歌词刷新颜色变换，所以当前歌词和下一句歌词位置会交替
        if self.now_lyric_index % 2 == 0:
            self.addstr(4, self.startcol - 2, str(self.now_lyric), curses.color_pair(3))
            self.addstr(5, self.startcol + 1, str(self.post_lyric), curses.A_DIM)
        else:
            self.addstr(4, self.startcol - 2, str(self.post_lyric), curses.A_DIM)
            self.addstr(5, self.startcol + 1, str(self.now_lyric), curses.color_pair(3))
        self.screen.refresh()

    def build_loading(self):
        self.addstr(7, self.startcol, "享受高品质音乐，loading...", curses.color_pair(1))
        self.screen.refresh()

    def build_submenu(self, data):
        pass

    # start is the called timestamp of this function
    def build_menu(self, datatype, title, datalist, offset, index, step, start):
        # keep playing info in line 1
        curses.noecho()
        self.screen.move(7, 1)
        self.screen.clrtobot()
        self.addstr(7, self.startcol, title, curses.color_pair(1))

        if len(datalist) == 0:
            self.addstr(8, self.startcol, "这里什么都没有 -，-")
            return self.screen.refresh()

        if datatype == "main":
            for i in range(offset, min(len(datalist), offset + step)):
                if i == index:
                    self.addstr(
                        i - offset + 9,
                        self.indented_startcol,
                        "-> " + str(i) + ". " + datalist[i],
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 9, self.startcol, str(i) + ". " + datalist[i]
                    )

        elif datatype == "songs" or datatype == "fmsongs":
            iter_range = min(len(datalist), offset + step)
            for i in range(offset, iter_range):
                if isinstance(datalist[i], str):
                    raise ValueError(datalist)
                # this item is focus
                if i == index:
                    self.addstr(i - offset + 8, 0, " " * self.startcol)
                    lead = "-> " + str(i) + ". "
                    self.addstr(
                        i - offset + 8,
                        self.indented_startcol,
                        lead,
                        curses.color_pair(2),
                    )
                    name = "{}{}{}  < {} >".format(
                        datalist[i]["song_name"],
                        self.space,
                        datalist[i]["artist"],
                        datalist[i]["album_name"],
                    )

                    # the length decides whether to scoll
                    if truelen(name) < self.x - self.startcol - 1:
                        self.addstr(
                            i - offset + 8,
                            self.indented_startcol + len(lead),
                            name,
                            curses.color_pair(2),
                        )
                    else:
                        name = scrollstring(name + "  ", start)
                        self.addstr(
                            i - offset + 8,
                            self.indented_startcol + len(lead),
                            str(name),
                            curses.color_pair(2),
                        )
                else:
                    self.addstr(i - offset + 8, 0, " " * self.startcol)
                    self.addstr(
                        i - offset + 8,
                        self.startcol,
                        "{}. {}{}{}  < {} >".format(
                            i,
                            datalist[i]["song_name"],
                            self.space,
                            datalist[i]["artist"],
                            datalist[i]["album_name"],
                        )[: int(self.x * 2)],
                    )

            self.addstr(iter_range - offset + 8, 0, " " * self.x)

        elif datatype == "comments":
            # 被选中的评论在最下方显示全部字符，其余评论仅显示一行
            for i in range(offset, min(len(datalist), offset + step)):
                maxlength = min(int(1.8 * self.startcol), len(datalist[i]))
                if i == index:
                    self.addstr(
                        20,
                        self.indented_startcol,
                        "-> "
                        + str(i)
                        + ". "
                        + break_str(datalist[i], self.indented_startcol, maxlength),
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 9,
                        self.startcol,
                        str(i) + ". " + datalist[i][:maxlength],
                    )

        elif datatype == "artists":
            for i in range(offset, min(len(datalist), offset + step)):
                if i == index:
                    self.addstr(
                        i - offset + 9,
                        self.indented_startcol,
                        "-> "
                        + str(i)
                        + ". "
                        + datalist[i]["artists_name"]
                        + self.space
                        + str(datalist[i]["alias"]),
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 9,
                        self.startcol,
                        str(i)
                        + ". "
                        + datalist[i]["artists_name"]
                        + self.space
                        + datalist[i]["alias"],
                    )

        elif datatype == "artist_info":
            for i in range(offset, min(len(datalist), offset + step)):
                if i == index:
                    self.addstr(
                        i - offset + 9,
                        self.indented_startcol,
                        "-> " + str(i) + ". " + datalist[i]["item"],
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 9,
                        self.startcol,
                        str(i) + ". " + datalist[i]["item"],
                    )

        elif datatype == "albums":
            for i in range(offset, min(len(datalist), offset + step)):
                if i == index:
                    self.addstr(
                        i - offset + 9,
                        self.indented_startcol,
                        "-> "
                        + str(i)
                        + ". "
                        + datalist[i]["albums_name"]
                        + self.space
                        + datalist[i]["artists_name"],
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 9,
                        self.startcol,
                        str(i)
                        + ". "
                        + datalist[i]["albums_name"]
                        + self.space
                        + datalist[i]["artists_name"],
                    )

        elif datatype == "recommend_lists":
            for i in range(offset, min(len(datalist), offset + step)):
                if i == index:
                    self.addstr(
                        i - offset + 9,
                        self.indented_startcol,
                        "-> " + str(i) + ". " + datalist[i]["title"],
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 9,
                        self.startcol,
                        str(i) + ". " + datalist[i]["title"],
                    )

        elif datatype in ("top_playlists", "playlists"):
            for i in range(offset, min(len(datalist), offset + step)):
                if i == index:
                    self.addstr(
                        i - offset + 9,
                        self.indented_startcol,
                        "-> "
                        + str(i)
                        + ". "
                        + datalist[i]["playlist_name"]
                        + self.space
                        + datalist[i]["creator_name"],
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 9,
                        self.startcol,
                        str(i)
                        + ". "
                        + datalist[i]["playlist_name"]
                        + self.space
                        + datalist[i]["creator_name"],
                    )

        elif datatype in ("toplists", "playlist_classes", "playlist_class_detail"):
            for i in range(offset, min(len(datalist), offset + step)):
                if i == index:
                    self.addstr(
                        i - offset + 9,
                        self.indented_startcol,
                        "-> " + str(i) + ". " + datalist[i],
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 9, self.startcol, str(i) + ". " + datalist[i]
                    )

        elif datatype == "djchannels":
            for i in range(offset, min(len(datalist), offset + step)):
                if i == index:
                    self.addstr(
                        i - offset + 8,
                        self.indented_startcol,
                        "-> " + str(i) + ". " + datalist[i]["name"],
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 8,
                        self.startcol,
                        str(i) + ". " + datalist[i]["name"],
                    )

        elif datatype == "search":
            self.screen.move(6, 1)
            self.screen.clrtobot()
            self.screen.timeout(-1)
            self.addstr(8, self.startcol, "选择搜索类型:", curses.color_pair(1))
            for i in range(offset, min(len(datalist), offset + step)):
                if i == index:
                    self.addstr(
                        i - offset + 10,
                        self.indented_startcol,
                        "-> " + str(i) + "." + datalist[i - 1],
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 10, self.startcol, str(i) + "." + datalist[i - 1]
                    )
            self.screen.timeout(100)

        elif datatype == "help":
            for i in range(offset, min(len(datalist), offset + step)):
                if i == index:
                    self.addstr(
                        i - offset + 9,
                        self.indented_startcol,
                        "-> {}. '{}{}   {}".format(
                            i,
                            (datalist[i][0] + "'").ljust(11),
                            datalist[i][1],
                            datalist[i][2],
                        ),
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 9,
                        self.startcol,
                        "{}. '{}{}   {}".format(
                            i,
                            (datalist[i][0] + "'").ljust(11),
                            datalist[i][1],
                            datalist[i][2],
                        ),
                    )

            self.addstr(20, 6, "NetEase-MusicBox 基于Python，所有版权音乐来源于网易，本地不做任何保存")
            self.addstr(21, 10, "按 [G] 到 Github 了解更多信息，帮助改进，或者Star表示支持~~")
            self.addstr(22, self.startcol, "Build with love to music by omi")

        self.screen.refresh()

    def build_login(self):
        self.build_login_bar()
        account = self.get_account()
        password = hashlib.md5(self.get_password().encode("utf-8")).hexdigest()
        return account, password

    def build_login_bar(self):
        curses.noecho()
        self.screen.move(4, 1)
        self.screen.clrtobot()
        self.addstr(5, self.startcol, "请输入登录信息(支持手机登录)", curses.color_pair(1))
        self.addstr(8, self.startcol, "账号:", curses.color_pair(1))
        self.addstr(9, self.startcol, "密码:", curses.color_pair(1))
        self.screen.move(8, 24)
        self.screen.refresh()

    def build_login_error(self):
        self.screen.move(4, 1)
        self.screen.timeout(-1)  # disable the screen timeout
        self.screen.clrtobot()
        self.addstr(8, self.startcol, "艾玛，登录信息好像不对呢 (O_O)#", curses.color_pair(1))
        self.addstr(10, self.startcol, "[1] 再试一次")
        self.addstr(11, self.startcol, "[2] 稍后再试")
        self.addstr(14, self.startcol, "请键入对应数字:", curses.color_pair(2))
        self.screen.refresh()
        x = self.screen.getch()
        self.screen.timeout(100)  # restore the screen timeout
        return x

    def build_timing(self):
        self.screen.move(6, 1)
        self.screen.clrtobot()
        self.screen.timeout(-1)
        self.addstr(8, self.startcol, "输入定时时间(min):", curses.color_pair(1))
        self.addstr(11, self.startcol, "ps:定时时间为整数，输入0代表取消定时退出", curses.color_pair(1))
        self.screen.timeout(-1)  # disable the screen timeout
        curses.echo()
        timing_time = self.screen.getstr(8, self.startcol + 19, 60)
        self.screen.timeout(100)  # restore the screen timeout
        return timing_time

    def get_account(self):
        self.screen.timeout(-1)  # disable the screen timeout
        curses.echo()
        account = self.screen.getstr(8, self.startcol + 6, 60)
        self.screen.timeout(100)  # restore the screen timeout
        return account.decode("utf-8")

    def get_password(self):
        self.screen.timeout(-1)  # disable the screen timeout
        curses.noecho()
        password = self.screen.getstr(9, self.startcol + 6, 60)
        self.screen.timeout(100)  # restore the screen timeout
        return password.decode("utf-8")

    def get_param(self, prompt_string):
        # keep playing info in line 1
        curses.echo()
        self.screen.move(4, 1)
        self.screen.clrtobot()
        self.addstr(5, self.startcol, prompt_string, curses.color_pair(1))
        self.screen.refresh()
        keyword = self.screen.getstr(10, self.startcol, 60)
        return keyword.decode("utf-8").strip()

    def update_size(self):
        # get terminal size
        size = terminalsize.get_terminal_size()
        x = max(size[0], 10)
        y = max(size[1], 25)
        if (x, y) == (self.x, self.y):  # no need to resize
            return
        self.x, self.y = x, y

        # update intendations
        curses.resizeterm(self.y, self.x)
        self.startcol = int(float(self.x) / 5)
        self.indented_startcol = max(self.startcol - 3, 0)
        self.update_space()
        self.screen.clear()
        self.screen.refresh()

    def update_space(self):
        if self.x > 140:
            self.space = "   -   "
        elif self.x > 80:
            self.space = "  -  "
        else:
            self.space = " - "
        self.screen.refresh()
