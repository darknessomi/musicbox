#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57
'''
网易云音乐 Api
'''
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from builtins import chr
from builtins import int
from builtins import map
from builtins import open
from builtins import range
from builtins import str
from future import standard_library
standard_library.install_aliases()

import re
import os
import json
import time
import hashlib
import random
import base64
import binascii

from Crypto.Cipher import AES
from http.cookiejar import LWPCookieJar
from bs4 import BeautifulSoup
import requests

from .config import Config
from .storage import Storage
from .utils import notify
from . import logger

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

log = logger.getLogger(__name__)

modulus = ('00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7'
           'b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280'
           '104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932'
           '575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b'
           '3ece0462db0a22b8e7')
nonce = '0CoJUm6Qyw8W8jud'
pubKey = '010001'


# 歌曲加密算法, 基于https://github.com/yanunon/NeteaseCloudMusic脚本实现
def encrypted_id(id):
    magic = bytearray('3go8&$8*3*3h0k(2)2', 'u8')
    song_id = bytearray(id, 'u8')
    magic_len = len(magic)
    for i, sid in enumerate(song_id):
        song_id[i] = sid ^ magic[i % magic_len]
    m = hashlib.md5(song_id)
    result = m.digest()
    result = base64.b64encode(result)
    result = result.replace(b'/', b'_')
    result = result.replace(b'+', b'-')
    return result.decode('u8')


# 登录加密算法, 基于https://github.com/stkevintan/nw_musicbox脚本实现
def encrypted_request(text):
    text = json.dumps(text)
    secKey = createSecretKey(16)
    encText = aesEncrypt(aesEncrypt(text, nonce), secKey)
    encSecKey = rsaEncrypt(secKey, pubKey, modulus)
    data = {'params': encText, 'encSecKey': encSecKey}
    return data


def aesEncrypt(text, secKey):
    pad = 16 - len(text) % 16
    text = text + chr(pad) * pad
    encryptor = AES.new(secKey, 2, '0102030405060708')
    ciphertext = encryptor.encrypt(text)
    ciphertext = base64.b64encode(ciphertext).decode('u8')
    return ciphertext


def rsaEncrypt(text, pubKey, modulus):
    text = text[::-1]
    rs = pow(int(binascii.hexlify(text), 16), int(pubKey, 16)) % int(modulus, 16)
    return format(rs, 'x').zfill(256)


def createSecretKey(size):
    return binascii.hexlify(os.urandom(size))[:16]


# list去重
def uniq(arr):
    arr2 = list(set(arr))
    arr2.sort(key=arr.index)
    return arr2


# 获取高音质mp3 url
def geturl(song):
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
    url = 'http://m%s.music.126.net/%s/%s.mp3' % (random.randrange(1, 3),
                                                  enc_id, song_id)
    return url, quality


def geturl_new_api(song):
    br_to_quality = {128000: 'MD 128k', 320000: 'HD 320k'}
    alter = NetEase().songs_detail_new_api([song['id']])[0]
    url = alter['url']
    quality = br_to_quality.get(alter['br'], '')
    return url, quality


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
        self.playlist_class_dict = {}
        self.session = requests.Session()
        self.storage = Storage()
        self.session.cookies = LWPCookieJar(self.storage.cookie_path)
        try:
            self.session.cookies.load()
            self.file = open(self.storage.cookie_path, 'r')
            cookie = self.file.read()
            self.file.close()
            pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
            str = pattern.findall(cookie)
            if str:
                if str[0] < time.strftime('%Y-%m-%d',
                                          time.localtime(time.time())):
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

    def httpRequest(self,
                    method,
                    action,
                    query=None,
                    urlencoded=None,
                    callback=None,
                    timeout=None):
        connection = json.loads(self.rawHttpRequest(
            method, action, query, urlencoded, callback, timeout))
        return connection

    def rawHttpRequest(self,
                       method,
                       action,
                       query=None,
                       urlencoded=None,
                       callback=None,
                       timeout=None):
        if method == 'GET':
            url = action if query is None else action + '?' + query
            connection = self.session.get(url,
                                          headers=self.header,
                                          timeout=default_timeout)

        elif method == 'POST':
            connection = self.session.post(action,
                                           data=query,
                                           headers=self.header,
                                           timeout=default_timeout)

        elif method == 'Login_POST':
            connection = self.session.post(action,
                                           data=query,
                                           headers=self.header,
                                           timeout=default_timeout)
            self.session.cookies.save()

        connection.encoding = 'UTF-8'
        return connection.text

    # 登录
    def login(self, username, password):
        pattern = re.compile(r'^0\d{2,3}\d{7,8}$|^1[34578]\d{9}$')
        if pattern.match(username):
            return self.phone_login(username, password)
        action = 'https://music.163.com/weapi/login/'
        text = {
            'username': username,
            'password': password,
            'rememberLogin': 'true'
        }
        data = encrypted_request(text)
        try:
            return self.httpRequest('Login_POST', action, data)
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
            return self.httpRequest('Login_POST', action, data)
        except requests.exceptions.RequestException as e:
            log.error(e)
            return {'code': 501}

    # 每日签到
    def daily_signin(self, type):
        action = 'http://music.163.com/weapi/point/dailyTask'
        text = {'type': type}
        data = encrypted_request(text)
        try:
            return self.httpRequest('POST', action, data)
        except requests.exceptions.RequestException as e:
            log.error(e)
            return -1

    # 用户歌单
    def user_playlist(self, uid, offset=0, limit=100):
        action = 'http://music.163.com/api/user/playlist/?offset={}&limit={}&uid={}'.format(  # NOQA
            offset, limit, uid)
        try:
            data = self.httpRequest('GET', action)
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
            data = self.httpRequest('GET', action)
            return data['data']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return -1

    # like
    def fm_like(self, songid, like=True, time=25, alg='itembased'):
        action = 'http://music.163.com/api/radio/like?alg={}&trackId={}&like={}&time={}'.format(  # NOQA
            alg, songid, 'true' if like else 'false', time)

        try:
            data = self.httpRequest('GET', action)
            if data['code'] == 200:
                return data
            else:
                return -1
        except requests.exceptions.RequestException as e:
            log.error(e)
            return -1

    # FM trash
    def fm_trash(self, songid, time=25, alg='RT'):
        action = 'http://music.163.com/api/radio/trash/add?alg={}&songId={}&time={}'.format(  # NOQA
            alg, songid, time)
        try:
            data = self.httpRequest('GET', action)
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
        return self.httpRequest('POST', action, data)

    # 新碟上架 http://music.163.com/#/discover/album/
    def new_albums(self, offset=0, limit=50):
        action = 'http://music.163.com/api/album/new?area=ALL&offset={}&total=true&limit={}'.format(  # NOQA
            offset, limit)
        try:
            data = self.httpRequest('GET', action)
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
            data = self.httpRequest('GET', action)
            return data['playlists']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # 分类歌单
    def playlist_classes(self):
        action = 'http://music.163.com/discover/playlist/'
        try:
            data = self.rawHttpRequest('GET', action)
            return data
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # 分类歌单中某一个分类的详情
    def playlist_class_detail(self):
        pass

    # 歌单详情
    def playlist_detail(self, playlist_id):
        action = 'http://music.163.com/api/playlist/detail?id={}'.format(
            playlist_id)
        try:
            data = self.httpRequest('GET', action)
            return data['result']['tracks']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # 热门歌手 http://music.163.com/#/discover/artist/
    def top_artists(self, offset=0, limit=100):
        action = 'http://music.163.com/api/artist/top?offset={}&total=false&limit={}'.format(  # NOQA
            offset, limit)
        try:
            data = self.httpRequest('GET', action)
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
            data = self.httpRequest('GET', action)
            return data['hotSongs']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # album id --> song id set
    def album(self, album_id):
        action = 'http://music.163.com/api/album/{}'.format(album_id)
        try:
            data = self.httpRequest('GET', action)
            return data['album']['songs']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    def song_comments(self, music_id, offset=0, total='fasle', limit=100):
        action = 'http://music.163.com/api/v1/resource/comments/R_SO_4_{}/?rid=R_SO_4_{}&\
            offset={}&total={}&limit={}'.format(music_id, music_id, offset, total, limit)
        try:
            comments = self.httpRequest('GET', action)
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
            data = self.httpRequest('GET', action)

            # the order of data['songs'] is no longer the same as tmpids,
            # so just make the order back
            data['songs'].sort(key=lambda song: tmpids.index(str(song['id'])))

            return data['songs']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    def songs_detail_new_api(self, music_ids, bit_rate=320000):
        action = 'http://music.163.com/weapi/song/enhance/player/url?csrf_token='  # NOQA
        self.session.cookies.load()
        csrf = ''
        for cookie in self.session.cookies:
            if cookie.name == '__csrf':
                csrf = cookie.value
        if csrf == '':
            notify('You Need Login', 1)
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
            music_id, music_id)  # NOQA
        try:
            data = self.httpRequest('GET', action)
            return data['songs']
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    # lyric http://music.163.com/api/song/lyric?os=osx&id= &lv=-1&kv=-1&tv=-1
    def song_lyric(self, music_id):
        action = 'http://music.163.com/api/song/lyric?os=osx&id={}&lv=-1&kv=-1&tv=-1'.format(  # NOQA
            music_id)
        try:
            data = self.httpRequest('GET', action)
            if 'lrc' in data and data['lrc']['lyric'] is not None:
                lyric_info = data['lrc']['lyric']
            else:
                lyric_info = '未找到歌词'
            return lyric_info
        except requests.exceptions.RequestException as e:
            log.error(e)
            return []

    def song_tlyric(self, music_id):
        action = 'http://music.163.com/api/song/lyric?os=osx&id={}&lv=-1&kv=-1&tv=-1'.format(  # NOQA
            music_id)
        try:
            data = self.httpRequest('GET', action)
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
                data = self.httpRequest('GET', action)
                channel = self.dig_info(data['program']['mainSong'],
                                        'channels')
                channels.append(channel)
            except requests.exceptions.RequestException as e:
                log.error(e)
                continue

        return channels

    # 获取版本
    def get_version(self):
        action = 'https://pypi.python.org/pypi?:action=doap&name=NetEase-MusicBox'  # NOQA
        try:
            data = requests.get(action)
            return data.content
        except requests.exceptions.RequestException as e:
            log.error(e)
            return ""

    def dig_info(self, data, dig_type):
        temp = []
        if dig_type == 'songs' or dig_type == 'fmsongs':
            for i in range(0, len(data)):
                url, quality = geturl(data[i])

                if data[i]['album'] is not None:
                    album_name = data[i]['album']['name']
                    album_id = data[i]['album']['id']
                else:
                    album_name = '未知专辑'
                    album_id = ''

                song_info = {
                    'song_id': data[i]['id'],
                    'artist': [],
                    'song_name': data[i]['name'],
                    'album_name': album_name,
                    'album_id': album_id,
                    'mp3_url': url,
                    'quality': quality
                }
                if 'artist' in data[i]:
                    song_info['artist'] = data[i]['artist']
                elif 'artists' in data[i]:
                    for j in range(0, len(data[i]['artists'])):
                        song_info['artist'].append(data[i]['artists'][j][
                            'name'])
                    song_info['artist'] = ', '.join(song_info['artist'])
                else:
                    song_info['artist'] = '未知艺术家'

                temp.append(song_info)

        elif dig_type == 'artists':
            artists = []
            for i in range(0, len(data)):
                artists_info = {
                    'artist_id': data[i]['id'],
                    'artists_name': data[i]['name'],
                    'alias': ''.join(data[i]['alias'])
                }
                artists.append(artists_info)

            return artists

        elif dig_type == 'albums':
            for i in range(0, len(data)):
                albums_info = {
                    'album_id': data[i]['id'],
                    'albums_name': data[i]['name'],
                    'artists_name': data[i]['artist']['name']
                }
                temp.append(albums_info)

        elif dig_type == 'top_playlists':
            for i in range(0, len(data)):
                playlists_info = {
                    'playlist_id': data[i]['id'],
                    'playlists_name': data[i]['name'],
                    'creator_name': data[i]['creator']['nickname']
                }
                temp.append(playlists_info)

        elif dig_type == 'channels':
            url, quality = geturl(data)
            channel_info = {
                'song_id': data['id'],
                'song_name': data['name'],
                'artist': data['artists'][0]['name'],
                'album_name': '主播电台',
                'mp3_url': url,
                'quality': quality
            }
            temp = channel_info

        elif dig_type == 'playlist_classes':
            soup = BeautifulSoup(data, 'lxml')
            dls = soup.select('dl.f-cb')
            for dl in dls:
                title = dl.dt.text
                sub = [item.text for item in dl.select('a')]
                temp.append(title)
                self.playlist_class_dict[title] = sub

        elif dig_type == 'playlist_class_detail':
            log.debug(data)
            temp = self.playlist_class_dict[data]

        return temp


if __name__ == '__main__':
    ne = NetEase()
    print(geturl_new_api(ne.songs_detail([27902910])[0]))  # MD 128k, fallback
    print(ne.songs_detail_new_api([27902910])[0]['url'])
    print(ne.songs_detail([405079776])[0]['mp3Url'])  # old api
    print(requests.get(ne.songs_detail([405079776])[0][
        'mp3Url']).status_code)  # 404
