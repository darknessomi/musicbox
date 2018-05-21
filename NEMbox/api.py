#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57
'''
网易云音乐 Api
'''
from __future__ import (
    print_function, unicode_literals, division, absolute_import
)
import re
import os
import json
import time
import random
from collections import OrderedDict
from http.cookiejar import LWPCookieJar

from bs4 import BeautifulSoup
from future.builtins import (map, open, range, str)
import requests

from .config import Config
from .storage import Storage
from .encrypt import encrypted_id, encrypted_request
from .utils import uniq
from . import logger

log = logger.getLogger(__name__)

# 歌曲榜单地址
top_list_all = {
    0: ['云音乐新歌榜', '/discover/toplist?id=3779629'],
    1: ['云音乐热歌榜', '/discover/toplist?id=3778678'],
    2: ['网易原创歌曲榜', '/discover/toplist?id=2884035'],
    3: ['云音乐飙升榜', '/discover/toplist?id=19723756'],
    4: ['云音乐电音榜', '/discover/toplist?id=10520166'],
    5: ['UK排行榜周榜', '/discover/toplist?id=180106'],
    6: ['美国Billboard周榜', '/discover/toplist?id=60198'],
    7: ['KTV嗨榜', '/discover/toplist?id=21845217'],
    8: ['iTunes榜', '/discover/toplist?id=11641012'],
    9: ['Hit FM Top榜', '/discover/toplist?id=120001'],
    10: ['日本Oricon周榜', '/discover/toplist?id=60131'],
    11: ['韩国Melon排行榜周榜', '/discover/toplist?id=3733003'],
    12: ['韩国Mnet排行榜周榜', '/discover/toplist?id=60255'],
    13: ['韩国Melon原声周榜', '/discover/toplist?id=46772709'],
    14: ['中国TOP排行榜(港台榜)', '/discover/toplist?id=112504'],
    15: ['中国TOP排行榜(内地榜)', '/discover/toplist?id=64016'],
    16: ['香港电台中文歌曲龙虎榜', '/discover/toplist?id=10169002'],
    17: ['华语金曲榜', '/discover/toplist?id=4395559'],
    18: ['中国嘻哈榜', '/discover/toplist?id=1899724'],
    19: ['法国 NRJ EuroHot 30周榜', '/discover/toplist?id=27135204'],
    20: ['台湾Hito排行榜', '/discover/toplist?id=112463'],
    21: ['Beatport全球电子舞曲榜', '/discover/toplist?id=3812895']
}

default_timeout = 10


class Parse(object):

    @classmethod
    def _song_v1(cls, song):
        # 老的获取歌曲url方法
        quality = Config().get_item('music_quality')
        if song['hMusic'] and quality <= 0:
            music = song['hMusic']
            quality = 'HD'
        elif song['mMusic'] and quality <= 1:
            music = song['mMusic']
            quality = 'MD'
        elif song['lMusic'] and quality <= 2:
            music = song['lMusic']
            quality = 'LD'
        else:
            return song['mp3Url'], ''

        quality = quality + ' {0}k'.format(music['bitrate'] // 1000)
        song_id = str(music['dfsId'])
        enc_id = encrypted_id(song_id)
        url = 'http://m{}.music.126.net/{}/{}.mp3'.format(random.randrange(1, 3), enc_id, song_id)
        return url, quality

    @classmethod
    def _song_v3(cls, song):
        # 新的获取歌曲url方法
        quality = Config().get_item('music_quality')
        if song['h'] and quality <= 0:
            music = song['h']
            quality = 'HD'
        elif song['m'] and quality <= 1:
            music = song['m']
            quality = 'MD'
        elif song['l'] and quality <= 2:
            music = song['l']
            quality = 'LD'
        else:
            return song.get('mp3Url', ''), ''

        quality = quality + ' {0}k'.format(music['br'] // 1000)
        song_id = str(music['fid'])
        enc_id = encrypted_id(song_id)
        url = 'http://m{}.music.126.net/{}/{}.mp3'.format(random.randrange(1, 3), enc_id, song_id)
        return url, quality

    @classmethod
    def song_url(cls, song):
        # 获取高音质mp3 url
        try:
            return cls._song_v1(song)
        except KeyError as e:
            return cls._song_v3(song)

    @classmethod
    def song_album(cls, song):
        # 对新老接口进行处理
        if 'al' in song:
            if song['al'] is not None:
                album_name = song['al']['name']
                album_id = song['al']['id']
            else:
                album_name = '未知专辑'
                album_id = ''
        else:
            if song['album'] is not None:
                album_name = song['album']['name']
                album_id = song['album']['id']
            else:
                album_name = '未知专辑'
                album_id = ''
        return album_name, album_id

    @classmethod
    def song_artist(cls, song):
        artist = ''
        # 对新老接口进行处理
        if 'ar' in song:
            artist = ', '.join([a['name'] for a in song['ar']])
        elif 'artists' in song:
            artist = ', '.join([a['name'] for a in song['artists']])
        else:
            artist = '未知艺术家'

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
                'song_id': song['id'],
                'artist': Parse.song_artist(song),
                'song_name': song['name'],
                'album_name': album_name,
                'album_id': album_id,
                'mp3_url': url,
                'quality': quality
            }
            song_info_list.append(song_info)
        return song_info_list

    @classmethod
    def artists(cls, artists):
        return [{
            'artist_id': artist['id'],
            'artists_name': artist['name'],
            'alias': ''.join(artist['alias'])
        } for artist in artists]

    @classmethod
    def albums(cls, albums):
        return [{
            'album_id': album['id'],
            'albums_name': album['name'],
            'artists_name': album['artist']['name']
        } for album in albums]

    @classmethod
    def top_playlists(cls, playlists):
        return [{
            'playlist_id': pl['id'],
            'playlist_name': pl['name'],
            'creator_name': pl['creator']['nickname']
        } for pl in playlists]

    @classmethod
    def playlist_classes(cls, playlist_html):
        pass


class NetEase(object):

    def __init__(self):
        self.header = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip,deflate,sdch',
            'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'music.163.com',
            'Referer': 'http://music.163.com/search/',
            'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36'  # NOQA
        }
        self.cookies = {'appver': '1.5.2'}
        self.session = requests.Session()
        self.storage = Storage()
        self.session.cookies = LWPCookieJar(self.storage.cookie_path)
        try:
            self.session.cookies.load()
            cookie = ''
            if os.path.isfile(self.storage.cookie_path):
                self.file = open(self.storage.cookie_path, 'r')
                cookie = self.file.read()
                self.file.close()
            expire_time = re.compile(r'\d{4}-\d{2}-\d{2}').findall(cookie)
            if expire_time:
                if expire_time[0] < time.strftime('%Y-%m-%d', time.localtime(time.time())):
                    self.storage.database['user'] = {
                        'username': '',
                        'password': '',
                        'user_id': '',
                        'nickname': '',
                    }
                    self.storage.save()
                    os.remove(self.storage.cookie_path)
        except IOError as e:
            log.error(e)
            self.session.cookies.save()

    def return_toplists(self):
        return [l[0] for l in top_list_all.values()]

    def request(self, method, action, query=None, urlencoded=None, callback=None, timeout=None):
        connection = json.loads(
            self._raw_request(method, action, query, urlencoded, callback, timeout)
        )
        return connection

    def _raw_request(self,
                     method,
                     action,
                     query=None,
                     urlencoded=None,
                     callback=None,
                     timeout=None):
        if method == 'GET':
            url = action if query is None else action + '?' + query
            connection = self.session.get(
                url, headers=self.header, timeout=default_timeout
            )

        elif method == 'POST':
            connection = self.session.post(
                action, data=query, headers=self.header, timeout=default_timeout
            )

        elif method == 'Login_POST':
            connection = self.session.post(
                action, data=query, headers=self.header, timeout=default_timeout
            )
            self.session.cookies.save()

        connection.encoding = 'UTF-8'
        return connection.text

    # 登录
    def login(self, username, password):
        pattern = re.compile(r'^0\d{2,3}\d{7,8}$|^1[34578]\d{9}$')
        if pattern.match(username):
            return self.phone_login(username, password)

        action = 'https://music.163.com/weapi/login?csrf_token='
        self.session.cookies.load()
        text = {
            'username': username,
            'password': password,
            'rememberLogin': 'true'
        }
        data = encrypted_request(text)
        try:
            return self.request('Login_POST', action, data)
        except requests.exceptions.RequestException as e:
            log.error(e)
            return {'code': 501}

    # 手机登录
    def phone_login(self, username, password):
        action = 'https://music.163.com/weapi/login/cellphone'
        text = {
            'phone': username,
            'password': password,
            'rememberLogin': 'true'
        }
        data = encrypted_request(text)
        try:
            return self.request('Login_POST', action, data)
        except requests.exceptions.RequestException as e:
            log.error(e)
            return {'code': 501}

    # 每日签到
    def daily_signin(self, type):
        action = 'http://music.163.com/weapi/point/dailyTask'
        text = {'type': type}
        data = encrypted_request(text)
        try:
            return self.request('POST', action, data)
        except requests.exceptions.RequestException as e:
            log.error(e)
            return -1

    # 用户歌单
    def user_playlist(self, uid, offset=0, limit=100):
        action = 'http://music.163.com/api/user/playlist/?offset={}&limit={}&uid={}'.format(  # NOQA
            offset, limit, uid)
        try:
            data = self.request('GET', action)
            return data['playlist']
        except (requests.exceptions.RequestException, KeyError) as e:
            log.error(e)
            return -1

    # 每日推荐歌单
    def recommend_playlist(self):
        try:
            action = 'http://music.163.com/weapi/v1/discovery/recommend/songs?csrf_token='  # NOQA
            self.session.cookies.load()
            csrf = ''
            for cookie in self.session.cookies:
                if cookie.name == '__csrf':
                    csrf = cookie.value
            if csrf == '':
                return False
            action += csrf
            req = {'offset': 0, 'total': True, 'limit': 20, 'csrf_token': csrf}
            page = self.session.post(action,
                                     data=encrypted_request(req),
                                     headers=self.header,
                                     timeout=default_timeout)
            results = json.loads(page.text)['recommend']
            song_ids = []
            for result in results:
                song_ids.append(result['id'])
            data = map(self.song_detail, song_ids)
            return [d[0] for d in data]
        except (requests.exceptions.RequestException, ValueError) as e:
            log.error(e)
            return False

    # 私人FM
    def personal_fm(self):
        action = 'http://music.163.com/api/radio/get'
        try:
            data = self.request('GET', action)
            return data['data']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return -1

    # like
    def fm_like(self, songid, like=True, time=25, alg='itembased'):
        action = 'http://music.163.com/api/radio/like?alg={}&trackId={}&like={}&time={}'.format(
            alg, songid, 'true' if like else 'false', time
        )

        try:
            data = self.request('GET', action)
            if data['code'] == 200:
                return data
            else:
                return -1
        except requests.exceptions.RequestException as e:
            log.error(e)
            return -1

    # FM trash
    def fm_trash(self, songid, time=25, alg='RT'):
        action = 'http://music.163.com/api/radio/trash/add?alg={}&songId={}&time={}'.format(
            alg, songid, time
        )
        try:
            data = self.request('GET', action)
            if data['code'] == 200:
                return data
            else:
                return -1
        except requests.exceptions.RequestException as e:
            log.error(e)
            return -1

    # 搜索单曲(1)，歌手(100)，专辑(10)，歌单(1000)，用户(1002) *(type)*
    def search(self, s, stype=1, offset=0, total='true', limit=60):
        action = 'http://music.163.com/api/search/get'
        data = {
            's': s,
            'type': stype,
            'offset': offset,
            'total': total,
            'limit': limit
        }
        return self.request('POST', action, data)

    # 新碟上架 http://music.163.com/#/discover/album/
    def new_albums(self, offset=0, limit=50):
        action = 'http://music.163.com/api/album/new?area=ALL&offset={}&total=true&limit={}'.format(  # NOQA
            offset, limit)
        try:
            data = self.request('GET', action)
            return data['albums']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # 歌单（网友精选碟） hot||new http://music.163.com/#/discover/playlist/
    def top_playlists(self, category='全部', order='hot', offset=0, limit=50):
        action = 'http://music.163.com/api/playlist/list?cat={}&order={}&offset={}&total={}&limit={}'.format(  # NOQA
            category, order, offset, 'true' if offset else 'false',
            limit)  # NOQA
        try:
            data = self.request('GET', action)
            return data['playlists']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # 分类歌单
    def playlist_classes(self):
        action = 'http://music.163.com/discover/playlist/'
        try:
            data = self._raw_request('GET', action)
            soup = BeautifulSoup(data, 'html.parser')
            dls = soup.select('dl.f-cb')
            self.playlist_class_dict = OrderedDict()

            for dl in dls:
                title = dl.dt.text
                sub = [item.text for item in dl.select('a')]
                self.playlist_class_dict[title] = sub

            return self.playlist_class_dict

        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # 分类歌单中某一个分类的详情
    def playlist_class_detail(self):
        pass

    # 歌单详情， 使用新版本v3接口，借鉴自https://github.com/Binaryify/NeteaseCloudMusicApi/commit/a1239a838c97367e86e2ec3cdce5557f1aa47bc1
    def playlist_detail(self, playlist_id):
        action = 'http://music.163.com/weapi/v3/playlist/detail'
        self.session.cookies.load()
        csrf = ''
        for cookie in self.session.cookies:
            if cookie.name == '__csrf':
                csrf = cookie.value
        data = {'id': playlist_id, 'total': 'true',
                'csrf_token': csrf, 'limit': 1000, 'n': 1000, 'offset': 0}
        connection = self.session.post(action,
                                       data=encrypted_request(data),
                                       headers=self.header, )
        result = json.loads(connection.text)
        # log.debug(result['playlist']['tracks'])
        return result['playlist']['tracks']

    # 热门歌手 http://music.163.com/#/discover/artist/
    def top_artists(self, offset=0, limit=100):
        action = 'http://music.163.com/api/artist/top?offset={}&total=false&limit={}'.format(  # NOQA
            offset, limit)
        try:
            data = self.request('GET', action)
            return data['artists']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # 热门单曲 http://music.163.com/discover/toplist?id=
    def top_songlist(self, idx=0, offset=0, limit=100):
        action = 'http://music.163.com' + top_list_all[idx][1]
        try:
            connection = requests.get(action,
                                      headers=self.header,
                                      timeout=default_timeout)
            connection.encoding = 'UTF-8'
            songids = re.findall(r'/song\?id=(\d+)', connection.text)
            if songids == []:
                return []
            # 去重
            songids = uniq(songids)
            return self.songs_detail(songids)
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # 歌手单曲
    def artists(self, artist_id):
        action = 'http://music.163.com/api/artist/{}'.format(artist_id)
        try:
            data = self.request('GET', action)
            return data['hotSongs']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    def get_artist_album(self, artist_id, offset=0, limit=50):
        action = 'http://music.163.com/api/artist/albums/{}?offset={}&limit={}'.format(
            artist_id, offset, limit)
        try:
            data = self.request('GET', action)
            return data['hotAlbums']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # album id --> song id set
    def album(self, album_id):
        action = 'http://music.163.com/api/album/{}'.format(album_id)
        try:
            data = self.request('GET', action)
            return data['album']['songs']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    def song_comments(self, music_id, offset=0, total='false', limit=100):
        action = 'http://music.163.com/api/v1/resource/comments/R_SO_4_{}/?rid=R_SO_4_{}&\
            offset={}&total={}&limit={}'.format(music_id, music_id, offset, total, limit)
        try:
            comments = self.request('GET', action)
            return comments
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # song ids --> song urls ( details )
    def songs_detail(self, ids, offset=0):
        tmpids = ids[offset:]
        tmpids = tmpids[0:100]
        tmpids = list(map(str, tmpids))
        action = 'http://music.163.com/api/song/detail?ids=[{}]'.format(  # NOQA
            ','.join(tmpids))
        try:
            data = self.request('GET', action)

            # the order of data['songs'] is no longer the same as tmpids,
            # so just make the order back
            data['songs'].sort(key=lambda song: tmpids.index(str(song['id'])))

            return data['songs']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    def songs_detail_new_api(self, music_ids, bit_rate=320000):
        action = 'http://music.163.com/weapi/song/enhance/player/url?csrf_token='
        self.session.cookies.load()
        csrf = ''
        for cookie in self.session.cookies:
            if cookie.name == '__csrf':
                csrf = cookie.value

        action += csrf
        data = {'ids': music_ids, 'br': bit_rate, 'csrf_token': csrf}
        connection = self.session.post(action,
                                       data=encrypted_request(data),
                                       headers=self.header, )
        result = json.loads(connection.text)
        return result['data']

    # song id --> song url ( details )
    def song_detail(self, music_id):
        action = 'http://music.163.com/api/song/detail/?id={}&ids=[{}]'.format(
            music_id, music_id)
        try:
            data = self.request('GET', action)
            return data['songs']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # lyric http://music.163.com/api/song/lyric?os=osx&id= &lv=-1&kv=-1&tv=-1
    def song_lyric(self, music_id):
        action = 'http://music.163.com/api/song/lyric?os=osx&id={}&lv=-1&kv=-1&tv=-1'.format(
            music_id)
        try:
            data = self.request('GET', action)
            if 'lrc' in data and data['lrc']['lyric'] is not None:
                lyric_info = data['lrc']['lyric']
            else:
                lyric_info = '未找到歌词'
            return lyric_info
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    def song_tlyric(self, music_id):
        action = 'http://music.163.com/api/song/lyric?os=osx&id={}&lv=-1&kv=-1&tv=-1'.format(
            music_id)
        try:
            data = self.request('GET', action)
            if 'tlyric' in data and data['tlyric'].get('lyric') is not None:
                lyric_info = data['tlyric']['lyric'][1:]
            else:
                lyric_info = '未找到歌词翻译'
            return lyric_info
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # 今日最热（0）, 本周最热（10），历史最热（20），最新节目（30）
    def djchannels(self, stype=0, offset=0, limit=50):
        action = 'http://music.163.com/discover/djradio?type={}&offset={}&limit={}'.format(  # NOQA
            stype, offset, limit)
        try:
            connection = requests.get(action,
                                      headers=self.header,
                                      timeout=default_timeout)
            connection.encoding = 'UTF-8'
            channelids = re.findall(r'/program\?id=(\d+)', connection.text)
            channelids = uniq(channelids)
            return self.channel_detail(channelids)
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # DJchannel ( id, channel_name ) ids --> song urls ( details )
    # 将 channels 整理为 songs 类型
    def channel_detail(self, channelids, offset=0):
        channels = []
        for i in range(0, len(channelids)):
            action = 'http://music.163.com/api/dj/program/detail?id={}'.format(
                channelids[i])
            try:
                data = self.request('GET', action)
                channel = self.dig_info(
                    data['program']['mainSong'], 'channels')
                channels.append(channel)
            except requests.exceptions.RequestException as e:
                log.error(e)
                continue

        return channels

    # 获取版本
    def get_version(self):
        action = 'https://pypi.org/pypi/NetEase-MusicBox/json'  # JSON API
        try:
            return requests.get(action).json()
        except requests.exceptions.RequestException as e:
            log.error(e)
            return {}

    def dig_info(self, data, dig_type):
        if dig_type == 'songs' or dig_type == 'fmsongs':
            return Parse.songs(data)
        elif dig_type == 'artists':
            return Parse.artists(data)

        elif dig_type == 'albums':
            return Parse.albums(data)

        elif dig_type == 'top_playlists':
            return Parse.top_playlists(data)

        elif dig_type == 'channels':
            url, quality = Parse.song_url(data)
            return {
                'song_id': data['id'],
                'song_name': data['name'],
                'artist': data['artists'][0]['name'],
                'album_name': '主播电台',
                'mp3_url': url,
                'quality': quality
            }

        elif dig_type == 'playlist_classes':
            return list(self.playlist_class_dict.keys())

        elif dig_type == 'playlist_class_detail':
            return self.playlist_class_dict[data]
