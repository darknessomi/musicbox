#!/usr/bin/env python
# @Author: omi
# @Date:   2014-08-24 21:51:57
"""
网易云音乐 Api
"""

import json
import os
import random
import time
from collections import OrderedDict
from http.cookiejar import Cookie, MozillaCookieJar
from http.cookies import SimpleCookie
from typing import Any, cast

import requests
from requests_cache import CachedSession

from .config import Config
from .const import Constant
from .encrypt import (
    anonymous_username,
    eapi_encrypt,
    eapi_response_decrypt,
    encrypted_request,
)
from .logger import getLogger
from .storage import Storage

log = getLogger(__name__)

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
            [
                "清晨",
                "夜晚",
                "学习",
                "工作",
                "午休",
                "下午茶",
                "地铁",
                "驾车",
                "运动",
                "旅行",
                "散步",
                "酒吧",
            ],
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

BASE_URL = "https://music.163.com"
EAPI_BASE_URL = "https://interface.music.163.com"

# music_quality -> song/url/v1 level
QUALITY_LEVEL_MAP = {
    0: "exhigh",
    1: "higher",
    2: "standard",
    3: "lossless",
    4: "hires",
}
QUALITY_LEVELS = {
    "standard",
    "higher",
    "exhigh",
    "lossless",
    "hires",
    "jyeffect",
    "sky",
    "jymaster",
}
LOSSLESS_LEVELS = {"lossless", "hires", "jymaster"}


def music_quality_to_level(quality):
    if isinstance(quality, str):
        normalized = quality.strip().lower()
        if normalized.isdigit():
            return QUALITY_LEVEL_MAP.get(int(normalized), "exhigh")
        if normalized in QUALITY_LEVELS:
            return normalized
        return "exhigh"
    return QUALITY_LEVEL_MAP.get(quality, "exhigh")


def level_to_encode_type(level):
    return "flac" if level in LOSSLESS_LEVELS else "mp3"


EAPI_OS = {
    "os": "iphone",
    "appver": "9.0.90",
    "osver": "16.2",
    "channel": "distribution",
}


class Parse:
    @classmethod
    def _song_url_by_id(cls, sid):
        # 128k
        url = f"http://music.163.com/song/media/outer/url?id={sid}.mp3"
        quality = "LD 128k"
        return url, quality

    @classmethod
    def song_url(cls, song):
        if "url" in song:
            # songs_url resp
            url = song["url"]
            if url is None:
                return Parse._song_url_by_id(song["id"])
            level = str(song.get("level") or "").upper()
            song_type = str(song.get("type") or "").upper()
            if level in {"LOSSLESS", "HIRES", "JYMASTER"} and song_type:
                return url, f"{level} {song_type}"
            if song_type == "FLAC" and level:
                return url, f"{level} FLAC"
            if song_type == "FLAC":
                return url, "LOSSLESS FLAC"
            br = song.get("br", 0) or 0
            if br >= 999000:
                return url, "LOSSLESS"
            if br >= 320000:
                quality = "HD"
            elif br >= 192000:
                quality = "MD"
            else:
                quality = "LD"
            return url, f"{quality} {br // 1000}k"
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
                "type": song.get("type", ""),
                "level": song.get("level", ""),
                "duration": int((song.get("dt") or song.get("duration") or 0) / 1000),
                "quality": quality,
                "expires": song["expires"],
                "get_time": song["get_time"],
            }
            song_info_list.append(song_info)
        return song_info_list

    @classmethod
    def cloud_songs(cls, data):
        songs = []
        for item in data:
            if not isinstance(item, dict):
                continue
            song = (
                item.get("simpleSong")
                or item.get("song")
                or item.get("simple_song")
                or item
            )
            if isinstance(song, dict) and song.get("id"):
                songs.append(song)
        return songs

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


class NetEase:
    def __init__(self):
        self.header = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip,deflate,sdch",
            "Accept-Language": "zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "music.163.com",
            "Referer": "https://music.163.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_1_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.87 Safari/537.36",
        }
        # 注入随机中国 IP 规避网易风控（8821 行为验证码）
        cn_ip = self._gen_cn_ip()
        self.header["X-Real-IP"] = cn_ip
        self.header["X-Forwarded-For"] = cn_ip

        self.storage = Storage()
        self.cookie_jar = MozillaCookieJar(self.storage.cookie_path)
        self.cookie_jar.load()
        self.session = CachedSession(
            cache_name=Constant.cache_path,
            expire_after=3600,
        )
        self.session.cookies = cast(Any, self.cookie_jar)
        for cookie in self.cookie_jar:
            if cookie.is_expired():
                self.cookie_jar.clear()
                self.storage.database["user"] = {
                    "username": "",
                    "password": "",
                    "user_id": "",
                    "nickname": "",
                }
                self.storage.save()
                break
        self._device_id = self._get_cookie_value("deviceId") or self._gen_device_id()
        self._toplists_cache = None

    @staticmethod
    def _gen_device_id():
        # 52 位大写 hex，对照 api-enhanced util/index.js generateDeviceId
        return "".join(random.choice("0123456789ABCDEF") for _ in range(52))

    @staticmethod
    def _gen_cn_ip():
        # 随机中国 IP，用于 X-Real-IP 规避风控，对照 generateRandomChineseIP 兜底逻辑
        return f"116.{random.randint(25, 94)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

    def _get_cookie_value(self, name):
        for cookie in self.session.cookies:
            if cookie.name == name:
                return cookie.value
        return ""

    def _set_cookie(self, name, value):
        self.session.cookies.set_cookie(self.make_cookie(name, value))

    def _apply_cookie_string(self, cookie_text):
        if not cookie_text:
            return
        cookie = SimpleCookie()
        try:
            cookie.load(cookie_text)
        except Exception as e:
            log.error("failed to parse login cookie: %s", e)
            return
        for name, morsel in cookie.items():
            if morsel.value:
                self._set_cookie(name, morsel.value)

    def fetch_toplists(self):
        try:
            with self.session.cache_disabled():
                resp = self._raw_request("GET", f"{BASE_URL}/api/toplist")
            if resp is None:
                log.error("fetch_toplists: no response")
                return []
            data = resp.json()
        except requests.exceptions.RequestException as e:
            log.error("fetch_toplists: %s", e)
            return []
        except ValueError as e:
            log.error("fetch_toplists: invalid json: %s", e)
            return []
        items = data.get("list") or []
        if not items:
            log.error("fetch_toplists: empty list, code=%s", data.get("code"))
            return []
        return [(item["name"], str(item["id"])) for item in items if item.get("id")]

    @property
    def toplists(self):
        if self._toplists_cache is None:
            self._toplists_cache = self.fetch_toplists()
        return [name for name, _ in self._toplists_cache]

    def logout(self):
        self.session.cookies.clear()
        self.storage.database["user"] = {
            "username": "",
            "password": "",
            "user_id": "",
            "nickname": "",
        }
        self.cookie_jar.save()
        self.storage.save()

    def _raw_request(self, method, endpoint, data=None):
        resp = None
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

    def request(
        self,
        method,
        path,
        params: dict[str, Any] | None = None,
        default: dict[str, Any] | None = None,
        custom_cookies=None,
    ) -> dict[str, Any]:
        if custom_cookies is None:
            custom_cookies = {}
        if default is None:
            default = {"code": -1}
        if params is None:
            params = {}
        endpoint = f"{BASE_URL}{path}"
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
        resp = None
        try:
            resp = self._raw_request(method, endpoint, params)
            if resp is None:
                return data
            data = resp.json()
        except requests.exceptions.RequestException as e:
            log.error(e)
        except ValueError:
            preview = resp.text[:200] if resp is not None else ""
            log.error(f"Path: {path}, response: {preview}")
        return data

    def _eapi_header_cookie(self):
        csrf_token = self._get_cookie_value("__csrf")
        header = {
            "osver": EAPI_OS["osver"],
            "deviceId": self._device_id,
            "os": EAPI_OS["os"],
            "appver": EAPI_OS["appver"],
            "versioncode": "140",
            "mobilename": "",
            "buildver": str(int(time.time()))[:10],
            "resolution": "1920x1080",
            "__csrf": csrf_token,
            "channel": EAPI_OS["channel"],
            "requestId": f"{int(time.time() * 1000)}_{random.randint(0, 9999):04d}",
        }
        music_u = self._get_cookie_value("MUSIC_U")
        if music_u:
            header["MUSIC_U"] = music_u
        return header

    def eapi_request(
        self,
        path,
        params: dict[str, Any] | None = None,
        default: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST eapi 接口（interface.music.163.com）。"""
        if default is None:
            default = {"code": -1}
        if params is None:
            params = {}
        api_path = path if path.startswith("/api/") else f"/api{path}"
        endpoint = f"{EAPI_BASE_URL}/eapi/{api_path[5:]}"

        header = self._eapi_header_cookie()
        payload = {**params, "e_r": True, "header": header}
        body = eapi_encrypt(api_path, payload)

        eapi_headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip,deflate",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "interface.music.163.com",
            "User-Agent": "NeteaseMusic 9.0.90/5038 (iPhone; iOS 16.2; zh_CN)",
            "Cookie": "; ".join(f"{k}={v}" for k, v in header.items() if v is not None),
            "X-Real-IP": self.header.get("X-Real-IP", ""),
            "X-Forwarded-For": self.header.get("X-Forwarded-For", ""),
        }

        data = default
        resp = None
        try:
            resp = self.session.post(
                endpoint, data=body, headers=eapi_headers, timeout=DEFAULT_TIMEOUT
            )
            raw = resp.content
            if not raw:
                return data
            try:
                data = resp.json()
            except ValueError:
                # eapi 加密响应为二进制，需转 hex 再解密（同 api-enhanced request.js）
                data = eapi_response_decrypt(raw.hex().upper())
        except requests.exceptions.RequestException as e:
            log.error(e)
        except (ValueError, KeyError) as e:
            preview = resp.text[:200] if resp is not None else ""
            log.error("eapi path %s failed: %s, response: %s", api_path, e, preview)
        return data

    def _ensure_anon_cookies(self):
        """登录前注入匿名设备上下文，对照 api-enhanced processCookieObject。"""
        nuid = self._get_cookie_value("_ntes_nuid") or os.urandom(32).hex()
        rand6 = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(6))
        wnmcid = self._get_cookie_value("WNMCID") or (
            f"{rand6}.{int(time.time() * 1000)}.01.0"
        )
        defaults = {
            "deviceId": self._device_id,
            "os": "pc",
            "appver": "3.1.17.204416",
            "osver": "Microsoft-Windows-10-Professional-build-19045-64bit",
            "channel": "netease",
            "__remember_me": "true",
            "_ntes_nuid": nuid,
            "_ntes_nnid": f"{nuid},{int(time.time() * 1000)}",
            "WNMCID": wnmcid,
            "WEVNSM": "1.0.0",
        }
        for name, value in defaults.items():
            if not self._get_cookie_value(name):
                self._set_cookie(name, value)

    def register_anonimous(self):
        """注册匿名设备以获取 MUSIC_A，对照 api-enhanced register/anonimous。"""
        self._ensure_anon_cookies()
        username = anonymous_username(self._device_id)
        path = "/weapi/register/anonimous"
        data = self.request("POST", path, {"username": username})
        self.cookie_jar.save()
        return data

    def login_qr_key(self):
        """获取二维码 unikey。返回 unikey 字符串或 None。"""
        self.cookie_jar.load()
        self._ensure_anon_cookies()
        path = "/weapi/login/qrcode/unikey"
        data = self.request("POST", path, {"type": 3}) or {}
        nested = data.get("data")
        if not isinstance(nested, dict):
            nested = {}
        unikey = data.get("unikey") or nested.get("unikey")
        if unikey:
            return unikey
        log.error("login_qr_key failed: %s", data)
        return None

    @staticmethod
    def login_qr_url(unikey):
        """由 unikey 生成二维码内容 URL。"""
        return f"https://music.163.com/login?codekey={unikey}"

    def login_qr_check(self, unikey):
        """轮询扫码状态。code: 800 过期 / 801 待扫码 / 802 待确认 / 803 成功。"""
        path = "/weapi/login/qrcode/client/login"
        data = self.request("POST", path, {"type": 3, "key": unikey})
        if data.get("code") == 803:
            self._apply_cookie_string(data.get("cookie"))
            self.cookie_jar.save()
        return data

    def get_account_info(self):
        """获取当前登录账号信息（含 account.id 与 profile.nickname）。"""
        path = "/weapi/nuser/account/get"
        data = self.request("POST", path)
        if data.get("account") or data.get("profile"):
            return data
        return self.request("POST", "/weapi/w/nuser/account/get")

    # 用户歌单
    def user_playlist(self, uid, offset=0, limit=50):
        path = "/weapi/user/playlist"
        params = {"uid": uid, "offset": offset, "limit": limit}
        return self.request("POST", path, params).get("playlist", [])

    # 我的云盘
    def user_cloud(self, offset=0, limit=100):
        path = "/weapi/v1/cloud/get"
        params = {"offset": offset, "limit": limit}
        return self.request("POST", path, params).get("data", [])

    # 每日推荐歌单
    def recommend_resource(self):
        path = "/weapi/v1/discovery/recommend/resource"
        return self.request("POST", path).get("recommend", [])

    # 每日推荐歌曲
    def recommend_playlist(self, total=True, offset=0, limit=20):
        path = "/weapi/v3/discovery/recommend/songs"
        data = self.request("POST", path, {"afresh": False})
        songs = data.get("recommend")
        if songs is None:
            songs = data.get("data", {}).get("dailySongs", [])
        return songs[offset : offset + limit] if limit else songs[offset:]

    # 私人FM
    def personal_fm(self):
        path = "/weapi/v1/radio/get"
        return self.request("POST", path).get("data", [])

    # like
    def fm_like(self, songid, like=True, time=25, alg="itembased"):
        path = "/weapi/radio/like"
        params = {
            "alg": alg,
            "trackId": songid,
            "like": "true" if like else "false",
            "time": time,
        }
        return self.request("POST", path, params)["code"] == 200

    # FM trash
    def fm_trash(self, songid, time=25, alg="RT"):
        path = "/weapi/radio/trash/add"
        params = {"songId": songid, "alg": alg, "time": time}
        return self.request("POST", path, params)["code"] == 200

    # 搜索单曲(1)，歌手(100)，专辑(10)，歌单(1000)，用户(1002) *(type)*
    def search(self, keywords, stype=1, offset=0, total="true", limit=50):
        path = "/weapi/search/get"
        params = {
            "s": keywords,
            "type": stype,
            "offset": offset,
            "total": total,
            "limit": limit,
        }
        return self.request("POST", path, params).get("result", {})

    # 新碟上架
    def new_albums(self, offset=0, limit=50):
        path = "/weapi/album/new"
        params = {"area": "ALL", "offset": offset, "total": True, "limit": limit}
        return self.request("POST", path, params).get("albums", [])

    # 歌单（网友精选碟） hot||new http://music.163.com/#/discover/playlist/
    def top_playlists(self, category="全部", order="hot", offset=0, limit=50):
        path = "/weapi/playlist/list"
        params = {
            "cat": category,
            "order": order,
            "offset": offset,
            "total": "true",
            "limit": limit,
        }
        return self.request("POST", path, params).get("playlists", [])

    def playlist_catelogs(self):
        path = "/weapi/playlist/catalogue"
        return self.request("POST", path)

    # 歌单详情
    def playlist_songlist(self, playlist_id):
        path = "/api/v6/playlist/detail"
        params = {"id": playlist_id, "n": 100000, "s": 8}
        return (
            self.eapi_request(path, params)
            .get("playlist", {})
            .get("trackIds", [])
        )

    # 热门歌手 http://music.163.com/#/discover/artist/
    def top_artists(self, offset=0, limit=100):
        path = "/weapi/artist/top"
        params = {"offset": offset, "total": True, "limit": limit}
        return self.request("POST", path, params).get("artists", [])

    # 热门单曲 http://music.163.com/discover/toplist?id=
    def top_songlist(self, idx=0, offset=0, limit=100):
        if self._toplists_cache is None:
            self._toplists_cache = self.fetch_toplists()
        if idx < 0 or idx >= len(self._toplists_cache):
            log.error("top_songlist: invalid idx %s", idx)
            return []
        playlist_id = self._toplists_cache[idx][1]
        return self.playlist_songlist(playlist_id)

    # 歌手单曲
    def artists(self, artist_id):
        path = f"/weapi/v1/artist/{artist_id}"
        return self.request("POST", path).get("hotSongs", [])

    def get_artist_album(self, artist_id, offset=0, limit=50):
        path = f"/weapi/artist/albums/{artist_id}"
        params = {"offset": offset, "total": True, "limit": limit}
        return self.request("POST", path, params).get("hotAlbums", [])

    # album id --> song id set
    def album(self, album_id):
        path = f"/weapi/v1/album/{album_id}"
        return self.request("POST", path).get("songs", [])

    def song_comments(self, music_id, offset=0, total="false", limit=100):
        path = f"/weapi/v1/resource/comments/R_SO_4_{music_id}/"
        params = {"rid": music_id, "offset": offset, "total": total, "limit": limit}
        return self.request("POST", path, params)

    # song ids --> song urls ( details )
    def songs_detail(self, ids):
        path = "/weapi/v3/song/detail"
        params = {"c": json.dumps([{"id": _id} for _id in ids]), "ids": json.dumps(ids)}
        return self.request("POST", path, params).get("songs", [])

    def songs_url(self, ids):
        quality = Config().get("music_quality")
        level = music_quality_to_level(quality)
        if not isinstance(ids, list):
            ids = list(ids)
        params = {
            "ids": json.dumps(ids, separators=(",", ":")),
            "level": level,
            "encodeType": level_to_encode_type(level),
        }
        result = self.eapi_request("/api/song/enhance/player/url/v1", params).get(
            "data", []
        )
        if result:
            return result
        # 降级：旧 weapi 按码率取链
        rate_map = {
            "exhigh": 320000,
            "higher": 192000,
            "standard": 128000,
            "lossless": 999000,
            "hires": 999000,
            "jymaster": 999000,
        }
        path = "/weapi/song/enhance/player/url"
        fallback_params = {"ids": ids, "br": rate_map.get(level, 320000)}
        return self.request("POST", path, fallback_params).get("data", [])

    def _song_lyric_data(self, music_id):
        path = "/api/song/lyric/v1"
        params = {
            "id": music_id,
            "cp": False,
            "tv": 0,
            "lv": 0,
            "rv": 0,
            "kv": 0,
            "yv": 0,
            "ytv": 0,
            "yrv": 0,
        }
        return self.eapi_request(path, params)

    @staticmethod
    def _parse_lyric_lines(lyric):
        """拆分歌词文本，过滤逐字歌词的 JSON 元信息行（如 {"t":14000,"c":[...]}）。"""
        if not lyric:
            return []
        lines = []
        for line in lyric.split("\n"):
            if line.lstrip().startswith("{"):
                continue
            lines.append(line)
        return lines

    def song_lyric(self, music_id):
        lyric = self._song_lyric_data(music_id).get("lrc", {}).get("lyric", [])
        return self._parse_lyric_lines(lyric)

    def song_tlyric(self, music_id):
        lyric = self._song_lyric_data(music_id).get("tlyric", {}).get("lyric", [])
        return self._parse_lyric_lines(lyric)

    # 今日最热（0）, 本周最热（10），历史最热（20），最新节目（30）
    def djRadios(self, offset=0, limit=50):
        path = "/weapi/djradio/hot/v1"
        params = {"limit": limit, "offset": offset}
        return self.request("POST", path, params).get("djRadios", [])

    def djprograms(self, radio_id, asc=False, offset=0, limit=50):
        path = "/weapi/dj/program/byradio"
        params = {"asc": asc, "radioId": radio_id, "offset": offset, "limit": limit}
        programs = self.request("POST", path, params).get("programs", [])
        return [p["mainSong"] for p in programs]

    def alldjprograms(self, radio_id, asc=False, offset=0, limit=500):
        programs = []
        ps = self.djprograms(radio_id, asc=asc, offset=offset, limit=limit)
        while ps:
            programs.extend(ps)
            offset += limit
            ps = self.djprograms(radio_id, asc=asc, offset=offset, limit=limit)
        return programs

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
        if dig_type == "cloud_songs":
            return self.dig_info(Parse.cloud_songs(data), "songs")

        if dig_type == "songs" or dig_type == "fmsongs" or dig_type == "djprograms":
            sids = [x["id"] for x in data]
            # 可能因网络波动，返回空值，在Parse.songs中引发KeyError
            # 导致日志记录大量can't get song url的可能原因
            urls = []
            for i in range(0, len(sids), 350):
                urls.extend(self.songs_url(sids[i : i + 350]))
            # songs_detail api会返回空的电台歌名，故使用原数据
            sds = []
            if dig_type == "djprograms":
                sds.extend(data)
            # 支持超过1000首歌曲的歌单
            else:
                for i in range(0, len(sids), 500):
                    sds.extend(self.songs_detail(sids[i : i + 500]))
                detail_ids = {s.get("id") for s in sds}
                for song in data:
                    if (
                        isinstance(song, dict)
                        and song.get("id") not in detail_ids
                        and song.get("name")
                    ):
                        sds.append(song)
            # api 返回的 urls 的 id 顺序和 data 的 id 顺序不一致
            # 为了获取到对应 id 的 url，对返回的 urls 做一个 id2index 的缓存
            # 同时保证 data 的 id 顺序不变
            url_id_index = {}
            for index, url in enumerate(urls):
                url_id_index[url["id"]] = index

            timestamp = time.time()
            for s in sds:
                url_index = url_id_index.get(s["id"])
                if url_index is None:
                    log.error("can't get song url, id: %s", s["id"])
                    return []
                s["url"] = urls[url_index]["url"]
                s["br"] = urls[url_index].get("br", 0)
                s["type"] = urls[url_index].get("type", "")
                s["level"] = urls[url_index].get("level", "")
                s["expires"] = urls[url_index].get("expi", -1)
                s["get_time"] = timestamp
            return Parse.songs(sds)

        elif dig_type == "refresh_urls":
            urls_info = []
            for i in range(0, len(data), 350):
                urls_info.extend(self.songs_url(data[i : i + 350]))
            timestamp = time.time()

            songs = []
            for url_info in urls_info:
                song = {}
                song["song_id"] = url_info["id"]
                song["mp3_url"] = url_info["url"]
                song["type"] = url_info.get("type", "")
                song["level"] = url_info.get("level", "")
                song["expires"] = url_info.get("expi", -1)
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

        elif dig_type == "djRadios":
            return data
        else:
            raise ValueError("Invalid dig type")
