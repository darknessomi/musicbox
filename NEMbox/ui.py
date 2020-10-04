#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57
# KenHuang:
# 1.增加显示颜色自定义；
# 2.调整显示格式；
"""
网易云音乐 Ui
"""
import curses
import datetime
import hashlib
import os
import re
from shutil import get_terminal_size

from . import logger
from .config import Config
from .scrollstring import scrollstring
from .scrollstring import truelen
from .scrollstring import truelen_cut
from .storage import Storage

log = logger.getLogger(__name__)

try:
    import dbus

    dbus_activity = True
except ImportError:
    dbus_activity = False
    log.warn("Qt dbus module is not installed.")
    log.warn("Osdlyrics is not available.")


def break_substr(s, start, max_len=80):
    if truelen(s) <= max_len:
        return s
    res = []
    current_truelen = 0
    start_pos = 0
    end_pos = 0
    for c in s:
        current_truelen += 2 if c > chr(127) else 1
        if current_truelen > max_len:
            res.append(s[start_pos:end_pos])
            current_truelen = 0
            start_pos = end_pos + 1
            end_pos += 1
        else:
            end_pos += 1
    try:
        res.append(s[start_pos:end_pos])
    except Exception:
        pass
    return "\n{}".format(" " * start).join(res)


def break_str(s, start, max_len=80):
    res = []
    for substr in s.splitlines():
        res.append(break_substr(substr, start, max_len))
    return "\n{}".format(" " * start).join(res)


class Ui(object):
    def __init__(self):
        self.screen = curses.initscr()
        curses.start_color()
        if Config().get("curses_transparency"):
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_CYAN, -1)
            curses.init_pair(3, curses.COLOR_RED, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
        else:
            colors = Config().get("colors")
            if (
                "TERM" in os.environ
                and os.environ["TERM"] == "xterm-256color"
                and colors
            ):
                curses.use_default_colors()
                for i in range(1, 6):
                    color = colors["pair" + str(i)]
                    curses.init_pair(i, color[0], color[1])
                self.screen.bkgd(32, curses.color_pair(5))
            else:
                curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
                curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
                curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
                curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        # term resize handling
        self.config = Config()
        size = get_terminal_size()
        self.x = size[0]
        self.y = size[1]
        self.playerX = 1  # terminalsize.get_terminal_size()[1] - 10
        self.playerY = 0
        self.update_margin()
        self.update_space()
        self.lyric = ""
        self.now_lyric = ""
        self.post_lyric = ""
        self.now_lyric_index = 0
        self.now_tlyric_index = 0
        self.tlyric = ""
        self.storage = Storage()
        self.newversion = False

    def addstr(self, *args):
        if len(args) == 1:
            self.screen.addstr(args[0])
        else:
            try:
                self.screen.addstr(args[0], args[1], args[2].encode("utf-8"), *args[3:])
            except Exception as e:
                log.error(e)

    def update_margin(self):
        # Left margin
        self.left_margin_ratio = self.config.get("left_margin_ratio")
        if self.left_margin_ratio == 0:
            self.startcol = 0
        else:
            self.startcol = max(int(float(self.x) / self.left_margin_ratio), 0)
        self.indented_startcol = max(self.startcol - 3, 0)
        # Right margin
        self.right_margin_ratio = self.config.get("right_margin_ratio")
        if self.right_margin_ratio == 0:
            self.endcol = 0
        else:
            self.endcol = max(
                int(float(self.x) - float(self.x) / self.right_margin_ratio),
                self.startcol + 1,
            )

        self.indented_endcol = max(self.endcol - 3, 0)
        self.content_width = self.endcol - self.startcol - 1

    def build_playinfo(
        self, song_name, artist, album_name, quality, start, pause=False
    ):
        curses.noecho()
        curses.curs_set(0)
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

        song_info = song_name + self.space + artist + "  < " + album_name + " >"
        if truelen(song_info) <= self.endcol - self.indented_startcol - 19:
            self.addstr(
                1,
                min(self.indented_startcol + 18, self.indented_endcol - 1),
                song_info,
                curses.color_pair(4),
            )
        else:
            song_info = scrollstring(song_info + " ", start)
            self.addstr(
                1,
                min(self.indented_startcol + 18, self.indented_endcol - 1),
                truelen_cut(str(song_info), self.endcol - self.indented_startcol - 19),
                curses.color_pair(4),
            )

        self.screen.refresh()

    def update_lyrics(self, now_playing, lyrics, tlyrics):

        timestap_regex = r"\d\d:\d\d\.[0-9]*"

        def get_timestap(lyric_line):
            match_ret = re.match(r"\[(" + timestap_regex + r")\]", lyric_line)
            if match_ret:
                return match_ret.group(1)
            else:
                return ""

        def get_lyric_time(lyric_line):
            lyric_timestap = get_timestap(lyric_line)
            if lyric_timestap == "":
                return datetime.timedelta(seconds=now_playing)
            else:
                return (
                    datetime.datetime.strptime(get_timestap(lyric_line), "%M:%S.%f")
                    - datetime.datetime.strptime("00:00", "%M:%S")
                    - lyric_time_offset
                )

        def strip_timestap(lyric_line):
            return re.sub(r"\[" + timestap_regex + r"\]", r"", lyric_line)

        def append_translation(translated_lyric, origin_lyric):
            translated_lyric = strip_timestap(translated_lyric)
            origin_lyric = strip_timestap(origin_lyric)
            if translated_lyric == "" or origin_lyric == "":
                return translated_lyric + origin_lyric
            return translated_lyric + " || " + origin_lyric

        if (
            tlyrics and self.now_tlyric_index >= len(tlyrics) - 1
        ) or self.now_lyric_index >= len(lyrics) - 1:
            self.post_lyric = ""
            return

        lyric_time_offset = datetime.timedelta(seconds=0.5)
        next_lyric_time = get_lyric_time(lyrics[self.now_lyric_index + 1])
        # now_lyric_time = get_lyric_time(lyrics[self.now_lyric_index])
        now_time = datetime.timedelta(seconds=now_playing)
        while now_time >= next_lyric_time and self.now_lyric_index < len(lyrics) - 2:
            self.now_lyric_index = self.now_lyric_index + 1
            next_lyric_time = get_lyric_time(lyrics[self.now_lyric_index + 1])

        if tlyrics:
            next_tlyric_time = get_lyric_time(tlyrics[self.now_tlyric_index + 1])
            while (
                now_time >= next_tlyric_time
                and self.now_tlyric_index < len(tlyrics) - 2
            ):
                self.now_tlyric_index = self.now_tlyric_index + 1
                next_tlyric_time = get_lyric_time(tlyrics[self.now_tlyric_index + 1])

        if tlyrics:
            self.now_lyric = append_translation(
                tlyrics[self.now_tlyric_index], lyrics[self.now_lyric_index]
            )
            if (
                self.now_tlyric_index < len(tlyrics) - 1
                and self.now_lyric_index < len(lyrics) - 1
            ):
                self.post_lyric = append_translation(
                    tlyrics[self.now_tlyric_index + 1], lyrics[self.now_lyric_index + 1]
                )
            else:
                self.post_lyric = ""
        else:
            self.now_lyric = strip_timestap(lyrics[self.now_lyric_index])
            if self.now_lyric_index < len(lyrics) - 1:
                self.post_lyric = strip_timestap(lyrics[self.now_lyric_index + 1])
            else:
                self.post_lyric = ""

    def build_process_bar(
        self, song, now_playing, total_length, playing_flag, playing_mode
    ):

        if not song or not playing_flag:
            return
        name, artist = song["song_name"], song["artist"]
        lyrics, tlyrics = song.get("lyric", []), song.get("tlyric", [])

        curses.noecho()
        curses.curs_set(0)
        self.screen.move(3, 1)
        self.screen.clrtoeol()
        self.screen.move(4, 1)
        self.screen.clrtoeol()
        self.screen.move(5, 1)
        self.screen.clrtoeol()
        self.screen.move(6, 1)
        self.screen.clrtoeol()
        if total_length <= 0:
            total_length = 1
        if now_playing > total_length or now_playing <= 0:
            now_playing = 0
        if int(now_playing) == 0:
            self.now_lyric_index = 0
            if tlyrics:
                self.now_tlyric_index = 0
            self.now_lyric = ""
            self.post_lyric = ""
        process = "["
        process_bar_width = self.content_width - 24
        for i in range(0, process_bar_width):
            if i < now_playing / total_length * process_bar_width:
                if (i + 1) > now_playing / total_length * process_bar_width:
                    if playing_flag:
                        process += ">"
                        continue
                process += "="
            else:
                process += " "
        process += "] "

        now = str(datetime.timedelta(seconds=int(now_playing))).lstrip("0").lstrip(":")
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
            self.update_lyrics(now_playing, lyrics, tlyrics)

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
            self.addstr(
                4, max(self.startcol - 2, 0), str(self.now_lyric), curses.color_pair(3)
            )
            self.addstr(
                5, max(self.startcol + 1, 0), str(self.post_lyric), curses.A_DIM
            )
        else:
            self.addstr(
                4, max(self.startcol - 2, 0), str(self.post_lyric), curses.A_DIM
            )
            self.addstr(
                5, max(self.startcol + 1, 0), str(self.now_lyric), curses.color_pair(3)
            )
        self.screen.refresh()

    def build_loading(self):
        curses.curs_set(0)
        self.addstr(7, self.startcol, "享受高品质音乐，loading...", curses.color_pair(1))
        self.screen.refresh()

    def build_submenu(self, data):
        pass

    # start is the called timestamp of this function
    def build_menu(self, datatype, title, datalist, offset, index, step, start):
        # keep playing info in line 1
        curses.noecho()
        curses.curs_set(0)
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
                        "-> " + str(i) + ". " + datalist[i]["entry_name"],
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 9,
                        self.startcol,
                        str(i) + ". " + datalist[i]["entry_name"],
                    )

        elif datatype == "songs" or datatype == "fmsongs":
            iter_range = min(len(datalist), offset + step)
            for i in range(offset, iter_range):
                if isinstance(datalist[i], str):
                    raise ValueError(datalist)
                # this item is focus
                if i == index:
                    self.addstr(i - offset + 9, 0, " " * self.startcol)
                    lead = "-> " + str(i) + ". "
                    self.addstr(
                        i - offset + 9,
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
                    if truelen(name) < self.content_width:
                        self.addstr(
                            i - offset + 9,
                            self.indented_startcol + len(lead),
                            name,
                            curses.color_pair(2),
                        )
                    else:
                        name = scrollstring(name + "  ", start)
                        self.addstr(
                            i - offset + 9,
                            self.indented_startcol + len(lead),
                            truelen_cut(
                                str(name), self.content_width - len(str(i)) - 2
                            ),
                            curses.color_pair(2),
                        )
                else:
                    self.addstr(i - offset + 9, 0, " " * self.startcol)
                    self.addstr(
                        i - offset + 9,
                        self.startcol,
                        truelen_cut(
                            "{}. {}{}{}  < {} >".format(
                                i,
                                datalist[i]["song_name"],
                                self.space,
                                datalist[i]["artist"],
                                datalist[i]["album_name"],
                            ),
                            self.content_width,
                        ),
                    )

            self.addstr(iter_range - offset + 9, 0, " " * self.x)

        elif datatype == "comments":
            # 被选中的评论在最下方显示全部字符，其余评论仅显示一行
            for i in range(offset, min(len(datalist), offset + step)):
                maxlength = min(
                    self.content_width, truelen(datalist[i]["comment_content"])
                )
                if i == index:
                    self.addstr(
                        i - offset + 9,
                        self.indented_startcol,
                        truelen_cut(
                            "-> "
                            + str(i)
                            + ". "
                            + datalist[i]["comment_content"].splitlines()[0],
                            self.content_width + len("-> " + str(i)),
                        ),
                        curses.color_pair(2),
                    )
                    self.addstr(
                        step + 10,
                        self.indented_startcol,
                        "-> "
                        + str(i)
                        + ". "
                        + datalist[i]["comment_content"].split(":", 1)[0]
                        + ":",
                        curses.color_pair(2),
                    )
                    self.addstr(
                        step + 12,
                        self.startcol + (len(str(i)) + 2),
                        break_str(
                            datalist[i]["comment_content"].split(":", 1)[1][1:],
                            self.startcol + (len(str(i)) + 2),
                            maxlength,
                        ),
                        curses.color_pair(2),
                    )
                else:
                    self.addstr(
                        i - offset + 9,
                        self.startcol,
                        truelen_cut(
                            str(i)
                            + ". "
                            + datalist[i]["comment_content"].splitlines()[0],
                            self.content_width,
                        ),
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
                            datalist[i][1].ljust(16),
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
                            datalist[i][1].ljust(16),
                            datalist[i][2],
                        ),
                    )

            self.addstr(
                20, self.startcol, "NetEase-MusicBox 基于Python，所有版权音乐来源于网易，本地不做任何保存"
            )
            self.addstr(21, self.startcol, "按 [G] 到 Github 了解更多信息，帮助改进，或者Star表示支持~~")
            self.addstr(22, self.startcol, "Build with love to music by omi")

        self.screen.refresh()

    def build_login(self):
        curses.curs_set(0)
        self.build_login_bar()
        account = self.get_account()
        password = hashlib.md5(self.get_password().encode("utf-8")).hexdigest()
        return account, password

    def build_login_bar(self):
        curses.curs_set(0)
        curses.noecho()
        self.screen.move(4, 1)
        self.screen.clrtobot()
        self.addstr(5, self.startcol, "请输入登录信息(支持手机登录)", curses.color_pair(1))
        self.addstr(8, self.startcol, "账号:", curses.color_pair(1))
        self.addstr(9, self.startcol, "密码:", curses.color_pair(1))
        self.screen.move(8, 24)
        self.screen.refresh()

    def build_login_error(self):
        curses.curs_set(0)
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

    def build_search_error(self):
        curses.curs_set(0)
        self.screen.move(4, 1)
        self.screen.timeout(-1)
        self.screen.clrtobot()
        self.addstr(8, self.startcol, "是不支持的搜索类型呢...", curses.color_pair(3))
        self.addstr(9, self.startcol, "（在做了，在做了，按任意键关掉这个提示）", curses.color_pair(3))
        self.screen.refresh()
        x = self.screen.getch()
        self.screen.timeout(100)
        return x

    def build_timing(self):
        curses.curs_set(0)
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
        curses.curs_set(0)
        # get terminal size
        size = get_terminal_size()
        x = size[0]
        y = size[1]
        if (x, y) == (self.x, self.y):  # no need to resize
            return
        self.x, self.y = x, y

        # update intendations
        curses.resizeterm(self.y, self.x)
        self.update_margin()
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
