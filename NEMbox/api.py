#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57
"""
网易云音乐 Api
"""
from __future__ import print_function, unicode_literals, division, absolute_import

import json
from collections import OrderedDict
from http.cookiejar import LWPCookieJar
from http.cookiejar import Cookie

import platform
import time
import requests
import requests_cache

from .config import Config
from .const import Constant
from .storage import Storage
from .encrypt import encrypted_request
from . import logger

requests_cache.install_cache(Constant.cache_path, expire_after=3600)

log = logger.getLogger(__name__)

# 歌曲榜单地址
TOP_LIST_ALL = {
    0: ["云音乐新歌榜", "3779629"],
    1: ["云音乐热歌榜", "3778678"],
    2: ["网易原创歌曲榜", "2884035"],
    3: ["云音乐飙升榜", "19723756"],
    4: ["云音乐电音榜", "10520166"],
    5: ["UK排行榜周榜", "180106"],
    6: ["美国Billboard周榜", "60198"],
    7: ["KTV嗨榜", "21845217"],
    8: ["iTunes榜", "11641012"],
    9: ["Hit FM Top榜", "120001"],
    10: ["日本Oricon周榜", "60131"],
    11: ["韩国Melon排行榜周榜", "3733003"],
    12: ["韩国Mnet排行榜周榜", "60255"],
    13: ["韩国Melon原声周榜", "46772709"],
    14: ["中国TOP排行榜(港台榜)", "112504"],
    15: ["中国TOP排行榜(内地榜)", "64016"],
    16: ["香港电台中文歌曲龙虎榜", "10169002"],
    17: ["华语金曲榜", "4395559"],
    18: ["中国嘻哈榜", "1899724"],
    19: ["法国 NRJ EuroHot 30周榜", "27135204"],
    20: ["台湾Hito排行榜", "112463"],
    21: ["Beatport全球电子舞曲榜", "3812895"],
    22: ["云音乐ACG音乐榜", "71385702"],
    23: ["云音乐嘻哈榜", "991319590"],
}


PLAYLIST_CLASSES = OrderedDict(
    [
        ("语种", ["华语", "欧美", "日语", "韩语", "粤语", "小语种"]),
        (
            "风格",
            [
                "流行",
                "摇滚",
                "民谣",
                "电子",
                "舞曲",
                "说唱",
                "轻音乐",
                "爵士",
                "乡村",
                "R&B/Soul",
                "古典",
                "民族",
                "英伦",
                "金属",
                "朋克",
                "蓝调",
                "雷鬼",
                "世界音乐",
                "拉丁",
                "另类/独立",
                "New Age",
                "古风",
                "后摇",
                "Bossa Nova",
            ],
        ),
        (
            "场景",
            ["清晨", "夜晚", "学习", "工作", "午休", "下午茶", "地铁", "驾车", "运动", "旅行", "散步", "酒吧"],
        ),
        (
            "情感",
            [
                "怀旧",
                "清新",
                "浪漫",
                "性感",
                "伤感",
                "治愈",
                "放松",
                "孤独",
                "感动",
                "兴奋",
                "快乐",
                "安静",
                "思念",
            ],
        ),
        (
            "主题",
            [
                "影视原声",
                "ACG",
                "儿童",
                "校园",
                "游戏",
                "70后",
                "80后",
                "90后",
                "网络歌曲",
                "KTV",
                "经典",
                "翻唱",
                "吉他",
                "钢琴",
                "器乐",
                "榜单",
                "00后",
            ],
        ),
    ]
)

DEFAULT_TIMEOUT = 10

BASE_URL = "http://music.163.com"


class Parse(object):
    @classmethod
    def _song_url_by_id(cls, sid):
        # 128k
        url = "http://music.163.com/song/media/outer/url?id={}.mp3".format(sid)
        quality = "LD 128k"
        return url, quality

    @classmethod
    def song_url(cls, song):
        if "url" in song:
            # songs_url resp
            url = song["url"]
            if url is None:
                return Parse._song_url_by_id(song["id"])
            br = song["br"]
            if br >= 320000:
                quality = "HD"
            elif br >= 192000:
                quality = "MD"
            else:
                quality = "LD"
            return url, "{} {}k".format(quality, br // 1000)
        else:
            # songs_detail resp
            return Parse._song_url_by_id(song["id"])

    @classmethod
    def song_album(cls, song):
        # 对新老接口进行处理
        if "al" in song:
            if song["al"] is not None:
                album_name = song["al"]["name"]
                album_id = song["al"]["id"]
            else:
                album_name = "未知专辑"
                album_id = ""
        elif "album" in song:
            if song["album"] is not None:
                album_name = song["album"]["name"]
                album_id = song["album"]["id"]
            else:
                album_name = "未知专辑"
                album_id = ""
        else:
            raise ValueError
        return album_name, album_id

    @classmethod
    def song_artist(cls, song):
        artist = ""
        # 对新老接口进行处理
        if "ar" in song:
            artist = ", ".join([a["name"] for a in song["ar"] if a["name"] is not None])
            # 某些云盘的音乐会出现 'ar' 的 'name' 为 None 的情况
            # 不过会多个 ’pc' 的字段
            # {'name': '简单爱', 'id': 31393663, 'pst': 0, 't': 1, 'ar': [{'id': 0, 'name': None, 'tns': [], 'alias': []}],
            #  'alia': [], 'pop': 0.0, 'st': 0, 'rt': None, 'fee': 0, 'v': 5, 'crbt': None, 'cf': None,
            #  'al': {'id': 0, 'name': None, 'picUrl': None, 'tns': [], 'pic': 0}, 'dt': 273000, 'h': None, 'm': None,
            #  'l': {'br': 193000, 'fid': 0, 'size': 6559659, 'vd': 0.0}, 'a': None, 'cd': None, 'no': 0, 'rtUrl': None,
            #  'ftype': 0, 'rtUrls': [], 'djId': 0, 'copyright': 0, 's_id': 0, 'rtype': 0, 'rurl': None, 'mst': 9,
            #  'cp': 0, 'mv': 0, 'publishTime': 0,
            #  'pc': {'nickname': '', 'br': 192, 'fn': '简单爱.mp3', 'cid': '', 'uid': 41533322, 'alb': 'The One 演唱会',
            #         'sn': '简单爱', 'version': 2, 'ar': '周杰伦'}, 'url': None, 'br': 0}
            if artist == "" and "pc" in song:
                artist = "未知艺术家" if song["pc"]["ar"] is None else song["pc"]["ar"]
        elif "artists" in song:
            artist = ", ".join([a["name"] for a in song["artists"]])
        else:
            artist = "未知艺术家"

        return artist

    @classmethod
    def songs(cls, songs):
        song_info_list = []
        for song in songs:
            url, quality = Parse.song_url(song)
            if not url:
                continue

            album_name, album_id = Parse.song_album(song)
            song_info = {
                "song_id": song["id"],
                "artist": Parse.song_artist(song),
                "song_name": song["name"],
                "album_name": album_name,
                "album_id": album_id,
                "mp3_url": url,
                "quality": quality,
                "expires": song["expires"],
                "get_time": song["get_time"],
            }
            song_info_list.append(song_info)
        return song_info_list

    @classmethod
    def artists(cls, artists):
        return [
            {
                "artist_id": artist["id"],
                "artists_name": artist["name"],
                "alias": "".join(artist["alias"]),
            }
            for artist in artists
        ]

    @classmethod
    def albums(cls, albums):
        return [
            {
                "album_id": album["id"],
                "albums_name": album["name"],
                "artists_name": album["artist"]["name"],
            }
            for album in albums
        ]

    @classmethod
    def playlists(cls, playlists):
        return [
            {
                "playlist_id": pl["id"],
                "playlist_name": pl["name"],
                "creator_name": pl["creator"]["nickname"],
            }
            for pl in playlists
        ]


class NetEase(object):
    def __init__(self):
        self.header = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip,deflate,sdch",
            "Accept-Language": "zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "music.163.com",
            "Referer": "http://music.163.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
        }

        self.storage = Storage()
        cookie_jar = LWPCookieJar(self.storage.cookie_path)
        cookie_jar.load()
        self.session = requests.Session()
        self.session.cookies = cookie_jar
        for cookie in cookie_jar:
            if cookie.is_expired():
                cookie_jar.clear()
                self.storage.database["user"] = {
                    "username": "",
                    "password": "",
                    "user_id": "",
                    "nickname": "",
                }
                self.storage.save()
                break

    @property
    def toplists(self):
        return [l[0] for l in TOP_LIST_ALL.values()]

    def logout(self):
        self.session.cookies.clear()
        self.storage.database["user"] = {
            "username": "",
            "password": "",
            "user_id": "",
            "nickname": "",
        }
        self.session.cookies.save()
        self.storage.save()

    def _raw_request(self, method, endpoint, data=None):
        if method == "GET":
            resp = self.session.get(
                endpoint, params=data, headers=self.header, timeout=DEFAULT_TIMEOUT
            )
        elif method == "POST":
            resp = self.session.post(
                endpoint, data=data, headers=self.header, timeout=DEFAULT_TIMEOUT
            )
        return resp

    # 生成Cookie对象
    def make_cookie(self, name, value):
        return Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain="music.163.com",
            domain_specified=True,
            domain_initial_dot=False,
            path="/",
            path_specified=True,
            secure=False,
            expires=None,
            discard=False,
            comment=None,
            comment_url=None,
            rest={},
        )

    def request(self, method, path, params={}, default={"code": -1}, custom_cookies={'os':'pc'}):
        endpoint = "{}{}".format(BASE_URL, path)
        csrf_token = ""
        for cookie in self.session.cookies:
            if cookie.name == "__csrf":
                csrf_token = cookie.value
                break
        params.update({"csrf_token": csrf_token})
        data = default

        for key, value in custom_cookies.items():
            cookie = self.make_cookie(key, value)
            self.session.cookies.set_cookie(cookie)

        params = encrypted_request(params)
        try:
            resp = self._raw_request(method, endpoint, params)
            data = resp.json()
        except requests.exceptions.RequestException as e:
            log.error(e)
        except ValueError as e:
            log.error("Path: {}, response: {}".format(path, resp.text[:200]))
        finally:
            return data

    def login(self, username, password):
        self.session.cookies.load()
        if username.isdigit():
            path = "/weapi/login/cellphone"
            params = dict(phone=username, password=password, rememberLogin="true")
        else:
            # magic token for login
            # see https://github.com/Binaryify/NeteaseCloudMusicApi/blob/master/router/login.js#L15
            client_token = (
                "1_jVUMqWEPke0/1/Vu56xCmJpo5vP1grjn_SOVVDzOc78w8OKLVZ2JH7IfkjSXqgfmh"
            )
            path = "/weapi/login"
            params = dict(
                username=username,
                password=password,
                rememberLogin="true",
                clientToken=client_token,
            )
        data = self.request("POST", path, params)
        self.session.cookies.save()
        return data

    # 每日签到
    def daily_task(self, is_mobile=True):
        path = "/weapi/point/dailyTask"
        params = dict(type=0 if is_mobile else 1)
        return self.request("POST", path, params)

    # 用户歌单
    def user_playlist(self, uid, offset=0, limit=50):
        path = "/weapi/user/playlist"
        params = dict(uid=uid, offset=offset, limit=limit, csrf_token="")
        return self.request("POST", path, params).get("playlist", [])

    # 每日推荐歌单
    def recommend_resource(self):
        path = "/weapi/v1/discovery/recommend/resource"
        return self.request("POST", path).get("recommend", [])

    # 每日推荐歌曲
    def recommend_playlist(self, total=True, offset=0, limit=20):
        path = "/weapi/v1/discovery/recommend/songs"  # NOQA
        params = dict(total=total, offset=offset, limit=limit, csrf_token="")
        return self.request("POST", path, params).get("recommend", [])

    # 私人FM
    def personal_fm(self):
        path = "/weapi/v1/radio/get"
        return self.request("POST", path).get("data", [])

    # like
    def fm_like(self, songid, like=True, time=25, alg="itembased"):
        path = "/weapi/radio/like"
        params = dict(
            alg=alg, trackId=songid, like="true" if like else "false", time=time
        )
        return self.request("POST", path, params)["code"] == 200

    # FM trash
    def fm_trash(self, songid, time=25, alg="RT"):
        path = "/weapi/radio/trash/add"
        params = dict(songId=songid, alg=alg, time=time)
        return self.request("POST", path, params)["code"] == 200

    # 搜索单曲(1)，歌手(100)，专辑(10)，歌单(1000)，用户(1002) *(type)*
    def search(self, keywords, stype=1, offset=0, total="true", limit=50):
        path = "/weapi/search/get"
        params = dict(s=keywords, type=stype, offset=offset, total=total, limit=limit)
        return self.request("POST", path, params).get("result", {})

    # 新碟上架
    def new_albums(self, offset=0, limit=50):
        path = "/weapi/album/new"
        params = dict(area="ALL", offset=offset, total=True, limit=limit)
        return self.request("POST", path, params).get("albums", [])

    # 歌单（网友精选碟） hot||new http://music.163.com/#/discover/playlist/
    def top_playlists(self, category="全部", order="hot", offset=0, limit=50):
        path = "/weapi/playlist/list"
        params = dict(
            cat=category, order=order, offset=offset, total="true", limit=limit
        )
        return self.request("POST", path, params).get("playlists", [])

    def playlist_catelogs(self):
        path = "/weapi/playlist/catalogue"
        return self.request("POST", path)

    # 歌单详情
    def playlist_detail(self, playlist_id):
        path = "/weapi/v3/playlist/detail"
        params = dict(id=playlist_id, total="true", limit=1000, n=1000, offest=0)
        # cookie添加os字段
        custom_cookies = dict(os=platform.system())
        return (
            self.request("POST", path, params, {"code": -1}, custom_cookies)
            .get("playlist", {})
            .get("tracks", [])
        )

    # 热门歌手 http://music.163.com/#/discover/artist/
    def top_artists(self, offset=0, limit=100):
        path = "/weapi/artist/top"
        params = dict(offset=offset, total=True, limit=limit)
        return self.request("POST", path, params).get("artists", [])

    # 热门单曲 http://music.163.com/discover/toplist?id=
    def top_songlist(self, idx=0, offset=0, limit=100):
        playlist_id = TOP_LIST_ALL[idx][1]
        return self.playlist_detail(playlist_id)

    # 歌手单曲
    def artists(self, artist_id):
        path = "/weapi/v1/artist/{}".format(artist_id)
        return self.request("POST", path).get("hotSongs", [])

    def get_artist_album(self, artist_id, offset=0, limit=50):
        path = "/weapi/artist/albums/{}".format(artist_id)
        params = dict(offset=offset, total=True, limit=limit)
        return self.request("POST", path, params).get("hotAlbums", [])

    # album id --> song id set
    def album(self, album_id):
        path = "/weapi/v1/album/{}".format(album_id)
        return self.request("POST", path).get("songs", [])

    def song_comments(self, music_id, offset=0, total="false", limit=100):
        path = "/weapi/v1/resource/comments/R_SO_4_{}/".format(music_id)
        params = dict(rid=music_id, offset=offset, total=total, limit=limit)
        return self.request("POST", path, params)

    # song ids --> song urls ( details )
    def songs_detail(self, ids):
        path = "/weapi/v3/song/detail"
        params = dict(c=json.dumps([{"id": _id} for _id in ids]), ids=json.dumps(ids))
        return self.request("POST", path, params).get("songs", [])

    def songs_url(self, ids):
        quality = Config().get("music_quality")
        rate_map = {0: 320000, 1: 192000, 2: 128000}

        path = "/weapi/song/enhance/player/url"
        params = dict(ids=ids, br=rate_map[quality])
        return self.request("POST", path, params).get("data", [])

    # lyric http://music.163.com/api/song/lyric?os=osx&id= &lv=-1&kv=-1&tv=-1
    def song_lyric(self, music_id):
        path = "/weapi/song/lyric"
        params = dict(os="osx", id=music_id, lv=-1, kv=-1, tv=-1)
        lyric = self.request("POST", path, params).get("lrc", {}).get("lyric", [])
        if not lyric:
            return []
        else:
            return lyric.split("\n")

    def song_tlyric(self, music_id):
        path = "/weapi/song/lyric"
        params = dict(os="osx", id=music_id, lv=-1, kv=-1, tv=-1)
        lyric = self.request("POST", path, params).get("tlyric", {}).get("lyric", [])
        if not lyric:
            return []
        else:
            return lyric.split("\n")

    # 今日最热（0）, 本周最热（10），历史最热（20），最新节目（30）
    def djchannels(self, offset=0, limit=50):
        path = "/weapi/djradio/hot/v1"
        params = dict(limit=limit, offset=offset)
        channels = self.request("POST", path, params).get("djRadios", [])
        return channels

    def djprograms(self, radio_id, asc=False, offset=0, limit=50):
        path = "/weapi/dj/program/byradio"
        params = dict(asc=asc, radioId=radio_id, offset=offset, limit=limit)
        programs = self.request("POST", path, params).get("programs", [])
        return [p["mainSong"] for p in programs]

    # 获取版本
    def get_version(self):
        action = "https://pypi.org/pypi/NetEase-MusicBox/json"
        try:
            return requests.get(action).json()
        except requests.exceptions.RequestException as e:
            log.error(e)
            return {}

    def dig_info(self, data, dig_type):
        if not data:
            return []
        if dig_type == "songs" or dig_type == "fmsongs":
            urls = self.songs_url([s["id"] for s in data])
            timestamp = time.time()
            # api 返回的 urls 的 id 顺序和 data 的 id 顺序不一致
            # 为了获取到对应 id 的 url，对返回的 urls 做一个 id2index 的缓存
            # 同时保证 data 的 id 顺序不变
            url_id_index = {}
            for index, url in enumerate(urls):
                url_id_index[url["id"]] = index
            for s in data:
                url_index = url_id_index.get(s["id"])
                if url_index is None:
                    log.error("can't get song url, id: %s", s["id"])
                    continue
                s["url"] = urls[url_index]["url"]
                s["br"] = urls[url_index]["br"]
                s["expires"] = urls[url_index]["expi"]
                s["get_time"] = timestamp
            return Parse.songs(data)

        elif dig_type == "refresh_urls":
            urls_info = self.songs_url(data)
            timestamp = time.time()

            songs = []
            for url_info in urls_info:
                song = {}
                song["song_id"] = url_info["id"]
                song["mp3_url"] = url_info["url"]
                song["expires"] = url_info["expi"]
                song["get_time"] = timestamp
                songs.append(song)
            return songs

        elif dig_type == "artists":
            return Parse.artists(data)

        elif dig_type == "albums":
            return Parse.albums(data)

        elif dig_type == "playlists" or dig_type == "top_playlists":
            return Parse.playlists(data)

        elif dig_type == "playlist_classes":
            return list(PLAYLIST_CLASSES.keys())

        elif dig_type == "playlist_class_detail":
            return PLAYLIST_CLASSES[data]
        else:
            raise ValueError("Invalid dig type")
