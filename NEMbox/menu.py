#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57
# KenHuang:
# 1.增加按键映射功能；
# 2.修复搜索按键功能映射错误；
# 3.使用定时器实现自动关闭功能；
"""
网易云音乐 Menu
"""
import curses as C
import locale
import os
import signal
import sys
import threading
import time
import webbrowser
from collections import namedtuple
from copy import deepcopy
from threading import Timer

from fuzzywuzzy import process

from . import logger
from .api import NetEase
from .cache import Cache
from .cmd_parser import cmd_parser
from .cmd_parser import erase_coroutine
from .cmd_parser import parse_keylist
from .config import Config
from .osdlyrics import pyqt_activity
from .osdlyrics import show_lyrics_new_process
from .player import Player
from .storage import Storage
from .ui import Ui
from .utils import notify


locale.setlocale(locale.LC_ALL, "")

log = logger.getLogger(__name__)


def carousel(left, right, x):
    # carousel x in [left, right]
    if x > right:
        return left
    elif x < left:
        return right
    else:
        return x


keyMap = Config().get("keymap")
commandList = list(map(ord, keyMap.values()))

if Config().get("mouse_movement"):
    keyMap["mouseUp"] = 259
    keyMap["mouseDown"] = 258
else:
    keyMap["mouseUp"] = -259
    keyMap["mouseDown"] = -258

shortcut = [
    [keyMap["down"], "Down", "下移"],
    [keyMap["up"], "Up", "上移"],
    ["<Num>+" + keyMap["up"], "<num> Up", "上移num"],
    ["<Num>+" + keyMap["down"], "<num> Down", "下移num"],
    [keyMap["back"], "Back", "后退"],
    [keyMap["forward"], "Forward", "前进"],
    [keyMap["prevPage"], "Prev page", "上一页"],
    [keyMap["nextPage"], "Next page", "下一页"],
    [keyMap["search"], "Search", "快速搜索"],
    [keyMap["prevSong"], "Prev song", "上一曲"],
    [keyMap["nextSong"], "Next song", "下一曲"],
    ["<Num>+" + keyMap["nextSong"], "<Num> Next Song", "下num曲"],
    ["<Num>+" + keyMap["prevSong"], "<Num> Prev song", "上num曲"],
    ["<Num>", "Goto song <num>", "跳转指定歌曲id"],
    [keyMap["playPause"], "Play/Pause", "播放/暂停"],
    [keyMap["shuffle"], "Shuffle", "手气不错"],
    [keyMap["volume+"], "Volume+", "音量增加"],
    [keyMap["volume-"], "Volume-", "音量减少"],
    [keyMap["menu"], "Menu", "主菜单"],
    [keyMap["presentHistory"], "Present/History", "当前/历史播放列表"],
    [keyMap["musicInfo"], "Music Info", "当前音乐信息"],
    [keyMap["playingMode"], "Playing Mode", "播放模式切换"],
    [keyMap["enterAlbum"], "Enter album", "进入专辑"],
    [keyMap["add"], "Add", "添加曲目到打碟"],
    [keyMap["djList"], "DJ list", "打碟列表（退出后清空）"],
    [keyMap["star"], "Star", "添加到本地收藏"],
    [keyMap["collection"], "Collection", "本地收藏列表"],
    [keyMap["remove"], "Remove", "删除当前条目"],
    [keyMap["moveDown"], "Move Down", "向下移动当前条目"],
    [keyMap["moveUp"], "Move Up", "向上移动当前条目"],
    [keyMap["like"], "Like", "喜爱"],
    [keyMap["cache"], "Cache", "缓存歌曲到本地"],
    [keyMap["nextFM"], "Next FM", "下一 FM"],
    [keyMap["trashFM"], "Trash FM", "删除 FM"],
    [keyMap["quit"], "Quit", "退出"],
    [keyMap["quitClear"], "Quit&Clear", "退出并清除用户信息"],
    [keyMap["help"], "Help", "帮助"],
    [keyMap["top"], "Top", "回到顶部"],
    [keyMap["bottom"], "Bottom", "跳转到底部"],
    [keyMap["countDown"], "Count Down", "定时"],
]


class Menu(object):
    def __init__(self):
        self.quit = False
        self.config = Config()
        self.datatype = "main"
        self.title = "网易云音乐"
        self.datalist = [
            {"entry_name": "排行榜"},
            {"entry_name": "艺术家"},
            {"entry_name": "新碟上架"},
            {"entry_name": "精选歌单"},
            {"entry_name": "我的歌单"},
            {"entry_name": "主播电台"},
            {"entry_name": "每日推荐歌曲"},
            {"entry_name": "每日推荐歌单"},
            {"entry_name": "私人FM"},
            {"entry_name": "搜索"},
            {"entry_name": "帮助"},
        ]
        self.offset = 0
        self.index = 0
        self.storage = Storage()
        self.storage.load()
        self.collection = self.storage.database["collections"]
        self.player = Player()
        self.player.playing_song_changed_callback = self.song_changed_callback
        self.cache = Cache()
        self.ui = Ui()
        self.api = NetEase()
        self.screen = C.initscr()
        self.screen.keypad(1)
        self.step = Config().get("page_length")
        if self.step == 0:
            self.step = max(int(self.ui.y * 4 / 5) - 10, 1)
        self.stack = []
        self.djstack = []
        self.at_playing_list = False
        self.enter_flag = True
        signal.signal(signal.SIGWINCH, self.change_term)
        signal.signal(signal.SIGINT, self.send_kill)
        signal.signal(signal.SIGTERM, self.send_kill)
        self.menu_starts = time.time()
        self.countdown_start = time.time()
        self.countdown = -1
        self.is_in_countdown = False
        self.timer = 0
        self.key_list = []
        self.pre_keylist = []
        self.parser = None
        self.at_search_result = False

    @property
    def user(self):
        return self.storage.database["user"]

    @property
    def account(self):
        return self.user["username"]

    @property
    def md5pass(self):
        return self.user["password"]

    @property
    def userid(self):
        return self.user["user_id"]

    @property
    def username(self):
        return self.user["nickname"]

    def login(self):
        if self.account and self.md5pass:
            account, md5pass = self.account, self.md5pass
        else:
            account, md5pass = self.ui.build_login()

        resp = self.api.login(account, md5pass)
        if resp["code"] == 200:
            userid = resp["account"]["id"]
            nickname = resp["profile"]["nickname"]
            self.storage.login(account, md5pass, userid, nickname)
            return True
        else:
            self.storage.logout()
            x = self.ui.build_login_error()
            if x >= 0 and C.keyname(x).decode("utf-8") != keyMap["forward"]:
                return False
            return self.login()

    def in_place_search(self):
        self.ui.screen.timeout(-1)
        prompt = "模糊搜索："
        keyword = self.ui.get_param(prompt)
        if not keyword:
            return [], ""
        if self.datalist == []:
            return [], keyword
        origin_index = 0
        for item in self.datalist:
            item["origin_index"] = origin_index
            origin_index += 1
        try:
            search_result = process.extract(
                keyword, self.datalist, limit=max(10, 2 * self.step)
            )
        except Exception as e:
            log.warn(e)
        if not search_result:
            return search_result, keyword
        search_result.sort(key=lambda ele: ele[1], reverse=True)
        return (list(map(lambda ele: ele[0], search_result)), keyword)

    def search(self, category):
        self.ui.screen.timeout(-1)
        SearchArg = namedtuple("SearchArg", ["prompt", "api_type", "post_process"])
        category_map = {
            "songs": SearchArg("搜索歌曲：", 1, lambda datalist: datalist),
            "albums": SearchArg("搜索专辑：", 10, lambda datalist: datalist),
            "artists": SearchArg("搜索艺术家：", 100, lambda datalist: datalist),
            "playlists": SearchArg("搜索网易精选集：", 1000, lambda datalist: datalist),
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
        if str(latest) > str(version) and latest != 0:
            notify("MusicBox Update == available", 1)
            time.sleep(0.5)
            notify(
                "NetEase-MusicBox installed version:"
                + version
                + "\nNetEase-MusicBox latest version:"
                + latest,
                0,
            )

    def check_version(self):
        # 检查更新 && 签到
        try:
            mobile = self.api.daily_task(is_mobile=True)
            pc = self.api.daily_task(is_mobile=False)

            if mobile["code"] == 200:
                notify("移动端签到成功", 1)
            if pc["code"] == 200:
                notify("PC端签到成功", 1)

            data = self.api.get_version()
            return data["info"]["version"]
        except KeyError:
            return 0

    def start_fork(self, version):
        pid = os.fork()
        if pid == 0:
            Menu().update_alert(version)
        else:
            Menu().start()

    def next_song(self):
        if self.player.is_empty:
            return
        self.player.next()

    def previous_song(self):
        if self.player.is_empty:
            return
        self.player.prev()

    def prev_key_event(self):
        self.player.prev_idx()

    def next_key_event(self):
        self.player.next_idx()

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
            self.index = carousel(
                offset, min(len(datalist), offset + step) - 1, idx - 1
            )
        self.menu_starts = time.time()

    def down_key_event(self):
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
            self.index = carousel(
                offset, min(len(datalist), offset + step) - 1, idx + 1
            )
        self.menu_starts = time.time()

    def space_key_event_in_search_result(self):
        origin_index = self.datalist[self.index]["origin_index"]
        (datatype, title, datalist, offset, index) = self.stack[-1]
        if datatype == "songs":
            self.player.new_player_list("songs", title, datalist, -1)
            self.player.end_callback = None
            self.player.play_or_pause(origin_index, self.at_playing_list)
            self.at_playing_list = False
        elif datatype == "djchannels":
            self.player.new_player_list("djchannels", title, datalist, -1)
            self.player.end_callback = None
            self.player.play_or_pause(origin_index, self.at_playing_list)
            self.at_playing_list = False
        elif datatype == "fmsongs":
            self.player.change_mode(0)
            self.player.new_player_list("fmsongs", title, datalist, -1)
            self.player.end_callback = self.fm_callback
            self.player.play_or_pause(origin_index, self.at_playing_list)
            self.at_playing_list = False
        else:
            # 所在列表类型不是歌曲
            is_not_songs = True
            self.player.play_or_pause(self.player.info["idx"], is_not_songs)
        self.build_menu_processbar()

    def space_key_event(self):
        idx = self.index
        datatype = self.datatype
        if not self.datalist:
            return
        if idx < 0 or idx >= len(self.datalist):
            self.player.info["idx"] = 0

        # If change to a new playing list. Add playing list and play.
        datatype_callback = {
            "songs": None,
            "djchannels": None,
            "fmsongs": self.fm_callback,
        }

        if datatype in ["songs", "djchannels", "fmsongs"]:
            self.player.new_player_list(datatype, self.title, self.datalist, -1)
            self.player.end_callback = datatype_callback[datatype]
            self.player.play_or_pause(idx, self.at_playing_list)
            self.at_playing_list = True

        else:
            # 所在列表类型不是歌曲
            is_not_songs = True
            self.player.play_or_pause(self.player.info["idx"], is_not_songs)
        self.build_menu_processbar()

    def like_event(self):
        return_data = self.request_api(self.api.fm_like, self.player.playing_id)
        if return_data:
            song_name = self.player.playing_name
            notify("%s added successfully!" % song_name, 0)
        else:
            notify("Adding song failed!", 0)

    def back_page_event(self):
        if len(self.stack) == 1:
            return
        self.menu_starts = time.time()
        (
            self.datatype,
            self.title,
            self.datalist,
            self.offset,
            self.index,
        ) = self.stack.pop()
        self.at_playing_list = False
        self.at_search_result = False

    def enter_page_event(self):
        idx = self.index
        self.enter_flag = True
        if len(self.datalist) <= 0:
            return
        if self.datatype == "comments":
            return
        self.menu_starts = time.time()
        self.ui.build_loading()
        self.dispatch_enter(idx)
        if self.enter_flag:
            self.index = 0
            self.offset = 0

    def album_key_event(self):
        datatype = self.datatype
        title = self.title
        datalist = self.datalist
        offset = self.offset
        idx = self.index
        step = self.step
        if datatype == "album":
            return
        if datatype in ["songs", "fmsongs"]:
            song_id = datalist[idx]["song_id"]
            album_id = datalist[idx]["album_id"]
            album_name = datalist[idx]["album_name"]
        elif self.player.playing_flag:
            song_id = self.player.playing_id
            song_info = self.player.songs.get(str(song_id), {})
            album_id = song_info.get("album_id", "")
            album_name = song_info.get("album_name", "")
        else:
            album_id = 0
        if album_id:
            self.stack.append([datatype, title, datalist, offset, self.index])
            songs = self.api.album(album_id)
            self.datatype = "songs"
            self.datalist = self.api.dig_info(songs, "songs")
            self.title = "网易云音乐 > 专辑 > %s" % album_name
            for i in range(len(self.datalist)):
                if self.datalist[i]["song_id"] == song_id:
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
        for _ in range(num):
            if cmd in (keyMap["mouseUp"], ord(keyMap["up"])):
                self.up_key_event()
            elif cmd in (keyMap["mouseDown"], ord(keyMap["down"])):
                self.down_key_event()
            elif cmd == ord(keyMap["nextSong"]):
                self.next_key_event()
            elif cmd == ord(keyMap["prevSong"]):
                self.prev_key_event()
        if cmd in (ord(keyMap["nextSong"]), ord(keyMap["prevSong"])):
            self.player.stop()
            self.player.replay()
        self.build_menu_processbar()

    def digit_key_song_event(self):
        """ 直接跳到指定id 歌曲 """
        step = self.step
        self.key_list.pop()
        song_index = parse_keylist(self.key_list)
        if self.index != song_index:
            self.index = song_index
            self.offset = self.index - self.index % step
            self.build_menu_processbar()
            self.ui.screen.refresh()

    def time_key_event(self):
        self.countdown_start = time.time()
        countdown = self.ui.build_timing()
        if not countdown.isdigit():
            notify("The input should be digit")

        countdown = int(countdown)
        if countdown > 0:
            notify("The musicbox will exit in {} minutes".format(countdown))
            self.countdown = countdown * 60
            self.is_in_countdown = True
            self.timer = Timer(self.countdown, self.stop, ())
            self.timer.start()
        else:
            notify("The timing exit has been canceled")
            self.is_in_countdown = False
            if self.timer:
                self.timer.cancel()
        self.build_menu_processbar()

    def down_page_event(self):
        offset = self.offset
        datalist = self.datalist
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
            self.player.process_location,
            self.player.process_length,
            self.player.playing_flag,
            self.player.info["playing_mode"],
        )
        self.ui.build_menu(
            self.datatype,
            self.title,
            self.datalist,
            self.offset,
            self.index,
            self.step,
            self.menu_starts,
        )

    def quit_event(self):
        self.config.save_config_file()
        sys.exit(0)

    def stop(self):
        self.quit = True
        self.player.stop()
        self.cache.quit()
        self.storage.save()
        C.endwin()

    def start(self):
        self.menu_starts = time.time()
        self.ui.build_menu(
            self.datatype,
            self.title,
            self.datalist,
            self.offset,
            self.index,
            self.step,
            self.menu_starts,
        )
        self.stack.append(
            [self.datatype, self.title, self.datalist, self.offset, self.index]
        )
        if pyqt_activity:
            show_lyrics_new_process()
        pre_key = -1
        keylist = self.key_list
        self.parser = cmd_parser(keylist)
        erase_cmd_list = []
        erase_coro = erase_coroutine(erase_cmd_list)
        next(self.parser)  # start generator
        next(erase_coro)
        while not self.quit:
            datatype = self.datatype
            title = self.title
            datalist = self.datalist
            offset = self.offset
            idx = self.index
            step = self.step
            self.screen.timeout(self.config.get("input_timeout"))
            key = self.screen.getch()

            if (
                key in commandList
                and key != ord(keyMap["nextSong"])
                and key != ord(keyMap["prevSong"])
            ):
                if not (
                    (
                        set(self.pre_keylist)
                        | {ord(keyMap["prevSong"]), ord(keyMap["nextSong"])}
                    )
                    == {ord(keyMap["prevSong"]), ord(keyMap["nextSong"])}
                ):
                    self.pre_keylist.append(key)
                self.key_list = deepcopy(self.pre_keylist)
                self.pre_keylist.clear()
            elif (
                key in range(48, 58)
                or key == ord(keyMap["nextSong"])
                or key == ord(keyMap["prevSong"])
            ):
                self.pre_keylist.append(key)
            elif key == -1 and (
                pre_key == ord(keyMap["nextSong"]) or pre_key == ord(keyMap["prevSong"])
            ):
                self.key_list = deepcopy(self.pre_keylist)
                self.pre_keylist.clear()
            # <Esc> 取消当前输入
            elif key == 27:
                self.pre_keylist.clear()
                self.key_list.clear()

            keylist = self.key_list

            # 如果 keylist 全都是数字 + G
            if keylist and (
                set(keylist) | set(range(48, 58)) | {ord(keyMap["jumpIndex"])}
            ) == set(range(48, 58)) | {ord(keyMap["jumpIndex"])}:
                # 歌曲数字映射
                self.digit_key_song_event()
                self.key_list.clear()
                continue

            # 如果 keylist 只有 [ ]
            if len(keylist) > 0 and (
                set(keylist) | {ord(keyMap["prevSong"]), ord(keyMap["nextSong"])}
            ) == {ord(keyMap["prevSong"]), ord(keyMap["nextSong"])}:
                self.player.stop()
                self.player.replay()
                self.key_list.clear()
                continue

            # 如果是 数字+ [ ] j k
            if len(keylist) > 1:
                if parse_keylist(keylist):
                    self.num_jump_key_event()
                    self.key_list.clear()
                    continue
            # if self.is_in_countdown:
            #     if time.time() - self.countdown_start > self.countdown:
            #         break
            if key == -1:
                self.player.update_size()

            # 退出
            elif C.keyname(key).decode("utf-8") == keyMap["quit"]:
                break

            # 退出并清除用户信息
            elif C.keyname(key).decode("utf-8") == keyMap["quitClear"]:
                self.api.logout()
                break

            # 上移
            elif C.keyname(key).decode("utf-8") == keyMap[
                "up"
            ] and pre_key not in range(ord("0"), ord("9")):
                self.up_key_event()
            elif self.config.get("mouse_movement") and key == keyMap["mouseUp"]:
                self.up_key_event()

            # 下移
            elif C.keyname(key).decode("utf-8") == keyMap[
                "down"
            ] and pre_key not in range(ord("0"), ord("9")):
                self.down_key_event()
            elif self.config.get("mouse_movement") and key == keyMap["mouseDown"]:
                self.down_key_event()

            # 向上翻页
            elif C.keyname(key).decode("utf-8") == keyMap["prevPage"]:
                self.up_page_event()

            # 向下翻页
            elif C.keyname(key).decode("utf-8") == keyMap["nextPage"]:
                self.down_page_event()

            # 前进
            elif C.keyname(key).decode("utf-8") == keyMap["forward"] or key == 10:
                self.enter_page_event()

            # 回退
            elif C.keyname(key).decode("utf-8") == keyMap["back"]:
                self.back_page_event()

            # 模糊搜索
            elif C.keyname(key).decode("utf-8") == keyMap["search"]:
                if self.at_search_result:
                    self.back_page_event()
                self.stack.append(
                    [self.datatype, self.title, self.datalist, self.offset, self.index]
                )
                self.datalist, keyword = self.in_place_search()
                self.title += " > " + keyword + " 的搜索结果"
                self.offset = 0
                self.index = 0
                self.at_search_result = True

            # 播放下一曲
            elif C.keyname(key).decode("utf-8") == keyMap[
                "nextSong"
            ] and pre_key not in range(ord("0"), ord("9")):
                self.next_key_event()

            # 播放上一曲
            elif C.keyname(key).decode("utf-8") == keyMap[
                "prevSong"
            ] and pre_key not in range(ord("0"), ord("9")):
                self.prev_key_event()

            # 增加音量
            elif C.keyname(key).decode("utf-8") == keyMap["volume+"]:
                self.player.volume_up()

            # 减少音量
            elif C.keyname(key).decode("utf-8") == keyMap["volume-"]:
                self.player.volume_down()

            # 随机播放
            elif C.keyname(key).decode("utf-8") == keyMap["shuffle"]:
                if len(self.player.info["player_list"]) == 0:
                    continue
                self.player.shuffle()

            # 喜爱
            elif C.keyname(key).decode("utf-8") == keyMap["like"]:
                return_data = self.request_api(self.api.fm_like, self.player.playing_id)
                if return_data:
                    song_name = self.player.playing_name
                    notify("%s added successfully!" % song_name, 0)
                else:
                    notify("Adding song failed!", 0)

            # 删除FM
            elif C.keyname(key).decode("utf-8") == keyMap["trashFM"]:
                if self.datatype == "fmsongs":
                    if len(self.player.info["player_list"]) == 0:
                        continue
                    self.player.next()
                    return_data = self.request_api(
                        self.api.fm_trash, self.player.playing_id
                    )
                    if return_data:
                        notify("Deleted successfully!", 0)

            # 更多FM
            elif C.keyname(key).decode("utf-8") == keyMap["nextFM"]:
                if self.datatype == "fmsongs":
                    # if len(self.player.info['player_list']) == 0:
                    #     continue
                    if self.player.end_callback:
                        self.player.end_callback()
                    else:
                        self.datalist.extend(self.get_new_fm())
                self.build_menu_processbar()
                self.index = len(self.datalist) - 1
                self.offset = self.index - self.index % self.step

            # 播放、暂停
            elif C.keyname(key).decode("utf-8") == keyMap["playPause"]:
                if self.at_search_result:
                    self.space_key_event_in_search_result()
                else:
                    self.space_key_event()

            # 加载当前播放列表
            elif C.keyname(key).decode("utf-8") == keyMap["presentHistory"]:
                self.show_playing_song()

            # 播放模式切换
            elif C.keyname(key).decode("utf-8") == keyMap["playingMode"]:
                self.player.change_mode()

            # 进入专辑
            elif C.keyname(key).decode("utf-8") == keyMap["enterAlbum"]:
                if datatype == "album":
                    continue
                if datatype in ["songs", "fmsongs"]:
                    song_id = datalist[idx]["song_id"]
                    album_id = datalist[idx]["album_id"]
                    album_name = datalist[idx]["album_name"]
                elif self.player.playing_flag:
                    song_id = self.player.playing_id
                    song_info = self.player.songs.get(str(song_id), {})
                    album_id = song_info.get("album_id", "")
                    album_name = song_info.get("album_name", "")
                else:
                    album_id = 0
                if album_id:
                    self.stack.append([datatype, title, datalist, offset, self.index])
                    songs = self.api.album(album_id)
                    self.datatype = "songs"
                    self.datalist = self.api.dig_info(songs, "songs")
                    self.title = "网易云音乐 > 专辑 > %s" % album_name
                    for i in range(len(self.datalist)):
                        if self.datalist[i]["song_id"] == song_id:
                            self.offset = i - i % step
                            self.index = i
                            break

            # 添加到打碟歌单
            elif C.keyname(key).decode("utf-8") == keyMap["add"]:
                if datatype == "songs" and len(datalist) != 0:
                    self.djstack.append(datalist[idx])
                elif datatype == "artists":
                    pass

            # 加载打碟歌单
            elif C.keyname(key).decode("utf-8") == keyMap["djList"]:
                self.stack.append(
                    [self.datatype, self.title, self.datalist, self.offset, self.index]
                )
                self.datatype = "songs"
                self.title = "网易云音乐 > 打碟"
                self.datalist = self.djstack
                self.offset = 0
                self.index = 0

            # 添加到本地收藏
            elif C.keyname(key).decode("utf-8") == keyMap["star"]:
                if (self.datatype == "songs" or self.datatype == "djchannels") and len(
                    self.datalist
                ) != 0:
                    self.collection.append(self.datalist[self.index])
                    notify("Added successfully", 0)

            # 加载本地收藏
            elif C.keyname(key).decode("utf-8") == keyMap["collection"]:
                self.stack.append(
                    [self.datatype, self.title, self.datalist, self.offset, self.index]
                )
                self.datatype = "songs"
                self.title = "网易云音乐 > 本地收藏"
                self.datalist = self.collection
                self.offset = 0
                self.index = 0

            # 从当前列表移除
            elif C.keyname(key).decode("utf-8") == keyMap["remove"]:
                if (
                    self.datatype in ("songs", "djchannels", "fmsongs")
                    and len(self.datalist) != 0
                ):
                    self.datalist.pop(self.index)
                    log.warn(self.index)
                    log.warn(len(self.datalist))
                    if self.index == len(self.datalist):
                        self.up_key_event()
                    self.index = carousel(
                        self.offset,
                        min(len(self.datalist), self.offset + self.step) - 1,
                        self.index,
                    )

            # 倒计时
            elif C.keyname(key).decode("utf-8") == keyMap["countDown"]:
                self.time_key_event()

            # 当前项目下移
            elif C.keyname(key).decode("utf-8") == keyMap["moveDown"]:
                if (
                    self.datatype != "main"
                    and len(self.datalist) != 0
                    and self.index + 1 != len(self.datalist)
                ):
                    self.menu_starts = time.time()
                    song = self.datalist.pop(self.index)
                    self.datalist.insert(self.index + 1, song)
                    self.index = self.index + 1
                    # 翻页
                    if self.index >= self.offset + self.step:
                        self.offset = self.offset + self.step

            # 当前项目上移
            elif C.keyname(key).decode("utf-8") == keyMap["moveUp"]:
                if (
                    self.datatype != "main"
                    and len(self.datalist) != 0
                    and self.index != 0
                ):
                    self.menu_starts = time.time()
                    song = self.datalist.pop(self.index)
                    self.datalist.insert(self.index - 1, song)
                    self.index = self.index - 1
                    # 翻页
                    if self.index < self.offset:
                        self.offset = self.offset - self.step

            # 菜单
            elif C.keyname(key).decode("utf-8") == keyMap["menu"]:
                if self.datatype != "main":
                    self.stack.append(
                        [
                            self.datatype,
                            self.title,
                            self.datalist,
                            self.offset,
                            self.index,
                        ]
                    )
                    self.datatype, self.title, self.datalist, *_ = self.stack[0]
                    self.offset = 0
                    self.index = 0
            # 跳到开头 g键
            elif C.keyname(key).decode("utf-8") == keyMap["top"]:
                if self.datatype == "help":
                    webbrowser.open_new_tab("https://github.com/darknessomi/musicbox")
                else:
                    self.index = 0
                    self.offset = 0

            # 跳到末尾ord('G') 键
            elif C.keyname(key).decode("utf-8") == keyMap["bottom"]:
                self.index = len(self.datalist) - 1
                self.offset = self.index - self.index % self.step

            # 开始下载
            elif C.keyname(key).decode("utf-8") == keyMap["cache"]:
                s = self.datalist[self.index]
                cache_thread = threading.Thread(
                    target=self.player.cache_song,
                    args=(s["song_id"], s["song_name"], s["artist"], s["mp3_url"]),
                )
                cache_thread.start()
            # 在网页打开 ord(i)
            elif C.keyname(key).decode("utf-8") == keyMap["musicInfo"]:
                if self.player.playing_id != -1:
                    webbrowser.open_new_tab(
                        "http://music.163.com/song?id={}".format(self.player.playing_id)
                    )
            # term resize
            # 刷新屏幕  按下某个键或者默认5秒刷新空白区
            #            erase_coro.send(key)
            #            if erase_cmd_list:
            #                self.screen.erase()
            self.player.update_size()

            pre_key = key
            self.ui.screen.refresh()
            self.ui.update_size()
            current_step = max(int(self.ui.y * 4 / 5) - 10, 1)
            if self.step != current_step and self.config.get("page_length") == 0:
                self.step = current_step
                self.index = 0
            self.build_menu_processbar()
        self.stop()

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

        if datatype == "main":
            self.choice_channel(idx)

        # 该艺术家的热门歌曲
        elif datatype == "artists":
            artist_name = datalist[idx]["artists_name"]
            artist_id = datalist[idx]["artist_id"]

            self.datatype = "artist_info"
            self.title += " > " + artist_name
            self.datalist = [
                {"item": "{}的热门歌曲".format(artist_name), "id": artist_id},
                {"item": "{}的所有专辑".format(artist_name), "id": artist_id},
            ]

        elif datatype == "artist_info":
            self.title += " > " + datalist[idx]["item"]
            artist_id = datalist[0]["id"]
            if idx == 0:
                self.datatype = "songs"
                songs = netease.artists(artist_id)
                self.datalist = netease.dig_info(songs, "songs")

            elif idx == 1:
                albums = netease.get_artist_album(artist_id)
                self.datatype = "albums"
                self.datalist = netease.dig_info(albums, "albums")

        elif datatype == "djchannels":
            radio_id = datalist[idx]["id"]
            programs = netease.djprograms(radio_id)
            self.title += " > " + datalist[idx]["name"]
            self.datatype = "songs"
            self.datalist = netease.dig_info(programs, "songs")

        # 该专辑包含的歌曲
        elif datatype == "albums":
            album_id = datalist[idx]["album_id"]
            songs = netease.album(album_id)
            self.datatype = "songs"
            self.datalist = netease.dig_info(songs, "songs")
            self.title += " > " + datalist[idx]["albums_name"]

        # 精选歌单选项
        elif datatype == "recommend_lists":
            data = self.datalist[idx]
            self.datatype = data["datatype"]
            self.datalist = netease.dig_info(data["callback"](), self.datatype)
            self.title += " > " + data["title"]

        # 全站置顶歌单包含的歌曲
        elif datatype in ["top_playlists", "playlists"]:
            playlist_id = datalist[idx]["playlist_id"]
            songs = netease.playlist_detail(playlist_id)
            self.datatype = "songs"
            self.datalist = netease.dig_info(songs, "songs")
            self.title += " > " + datalist[idx]["playlist_name"]

        # 分类精选
        elif datatype == "playlist_classes":
            # 分类名称
            data = self.datalist[idx]
            self.datatype = "playlist_class_detail"
            self.datalist = netease.dig_info(data, self.datatype)
            self.title += " > " + data

        # 某一分类的详情
        elif datatype == "playlist_class_detail":
            # 子类别
            data = self.datalist[idx]
            self.datatype = "top_playlists"
            self.datalist = netease.dig_info(netease.top_playlists(data), self.datatype)
            self.title += " > " + data

        # 歌曲评论
        elif datatype in ["songs", "fmsongs"]:
            song_id = datalist[idx]["song_id"]
            comments = self.api.song_comments(song_id, limit=100)
            try:
                hotcomments = comments["hotComments"]
                comcomments = comments["comments"]
            except KeyError:
                hotcomments = comcomments = []
            self.datalist = []
            for one_comment in hotcomments:
                self.datalist.append(
                    {
                        "comment_content": "(热评 %s❤️ ️) %s: %s"
                        % (
                            one_comment["likedCount"],
                            one_comment["user"]["nickname"],
                            one_comment["content"],
                        )
                    }
                )
            for one_comment in comcomments:
                # self.datalist.append(one_comment["content"])
                self.datalist.append(
                    {
                        "comment_content": "(%s❤️ ️) %s: %s"
                        % (
                            one_comment["likedCount"],
                            one_comment["user"]["nickname"],
                            one_comment["content"],
                        )
                    }
                )
            self.datatype = "comments"
            self.title = "网易云音乐 > 评论: %s" % datalist[idx]["song_name"]
            self.offset = 0
            self.index = 0

        # 歌曲榜单
        elif datatype == "toplists":
            songs = netease.top_songlist(idx)
            self.title += " > " + self.datalist[idx]
            self.datalist = netease.dig_info(songs, "songs")
            self.datatype = "songs"

        # 搜索菜单
        elif datatype == "search":
            self.index = 0
            self.offset = 0
            SearchCategory = namedtuple("SearchCategory", ["type", "title"])
            idx_map = {
                0: SearchCategory("playlists", "精选歌单搜索列表"),
                1: SearchCategory("songs", "歌曲搜索列表"),
                2: SearchCategory("artists", "艺术家搜索列表"),
                3: SearchCategory("albums", "专辑搜索列表"),
            }
            self.datatype, self.title = idx_map[idx]
            self.datalist = self.search(self.datatype)
        else:
            self.enter_flag = False

    #        self.parser.send(-1)

    def show_playing_song(self):
        if self.player.is_empty:
            return

        if (not self.at_playing_list) and (not self.at_search_result):
            self.stack.append(
                [self.datatype, self.title, self.datalist, self.offset, self.index]
            )
            self.at_playing_list = True

        if self.at_search_result:
            self.back_page_event()

        self.datatype = self.player.info["player_list_type"]
        self.title = self.player.info["player_list_title"]
        self.datalist = [self.player.songs[i] for i in self.player.info["player_list"]]
        self.index = self.player.info["idx"]
        self.offset = self.index // self.step * self.step

    def song_changed_callback(self):
        if self.at_playing_list:
            self.show_playing_song()

    def fm_callback(self):
        # log.debug('FM CallBack.')
        data = self.get_new_fm()
        self.player.append_songs(data)
        if self.datatype == "fmsongs":
            if self.player.is_empty:
                return
            self.datatype = self.player.info["player_list_type"]
            self.title = self.player.info["player_list_title"]
            self.datalist = []
            for i in self.player.info["player_list"]:
                self.datalist.append(self.player.songs[i])
            self.index = self.player.info["idx"]
            self.offset = self.index // self.step * self.step
            if not self.player.playing_flag:
                switch_flag = False
                self.player.play_or_pause(self.index, switch_flag)

    def request_api(self, func, *args):
        result = func(*args)
        if result:
            return result
        if not self.login():
            notify("You need to log in")
            return False
        return func(*args)

    def get_new_fm(self):
        data = self.request_api(self.api.personal_fm)
        if not data:
            return []
        return self.api.dig_info(data, "fmsongs")

    def choice_channel(self, idx):
        self.offset = 0
        self.index = 0

        if idx == 0:
            self.datalist = self.api.toplists
            self.title += " > 排行榜"
            self.datatype = "toplists"
        elif idx == 1:
            artists = self.api.top_artists()
            self.datalist = self.api.dig_info(artists, "artists")
            self.title += " > 艺术家"
            self.datatype = "artists"
        elif idx == 2:
            albums = self.api.new_albums()
            self.datalist = self.api.dig_info(albums, "albums")
            self.title += " > 新碟上架"
            self.datatype = "albums"
        elif idx == 3:
            self.datalist = [
                {
                    "title": "全站置顶",
                    "datatype": "top_playlists",
                    "callback": self.api.top_playlists,
                },
                {
                    "title": "分类精选",
                    "datatype": "playlist_classes",
                    "callback": lambda: [],
                },
            ]
            self.title += " > 精选歌单"
            self.datatype = "recommend_lists"
        elif idx == 4:
            myplaylist = self.request_api(self.api.user_playlist, self.userid)
            self.datatype = "top_playlists"
            self.datalist = self.api.dig_info(myplaylist, self.datatype)
            self.title += " > " + self.username + " 的歌单"
        elif idx == 5:
            self.datatype = "djchannels"
            self.title += " > 主播电台"
            self.datalist = self.api.djchannels()
        elif idx == 6:
            self.datatype = "songs"
            self.title += " > 每日推荐歌曲"
            myplaylist = self.request_api(self.api.recommend_playlist)
            if myplaylist == -1:
                return
            self.datalist = self.api.dig_info(myplaylist, self.datatype)
        elif idx == 7:
            myplaylist = self.request_api(self.api.recommend_resource)
            self.datatype = "top_playlists"
            self.title += " > 每日推荐歌单"
            self.datalist = self.api.dig_info(myplaylist, self.datatype)
        elif idx == 8:
            self.datatype = "fmsongs"
            self.title += " > 私人FM"
            self.datalist = self.get_new_fm()
        elif idx == 9:
            self.datatype = "search"
            self.title += " > 搜索"
            self.datalist = ["歌曲", "艺术家", "专辑", "网易精选集"]
        elif idx == 10:
            self.datatype = "help"
            self.title += " > 帮助"
            self.datalist = shortcut
