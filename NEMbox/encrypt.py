#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (
    print_function, unicode_literals, division, absolute_import
)
import base64
import binascii
import hashlib
import json
import os

from Crypto.Cipher import AES
from future.builtins import (chr, int, pow)

__all__ = ['encrypted_id', 'encrypted_request']

MODULUS = ('00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7'
           'b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280'
           '104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932'
           '575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b'
           '3ece0462db0a22b8e7')
NONCE = '0CoJUm6Qyw8W8jud'
PUBKEY = '010001'


# 歌曲加密算法, 基于https://github.com/yanunon/NeteaseCloudMusic
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
    return result.decode('utf-8')


# 登录加密算法, 基于https://github.com/stkevintan/nw_musicbox
def encrypted_request(text):
    text = json.dumps(text)
    secKey = create_key(16)
    encText = aes(aes(text, NONCE), secKey)
    encSecKey = rsa(secKey, PUBKEY, MODULUS)
    data = {'params': encText, 'encSecKey': encSecKey}
    return data


def aes(text, key):
    pad = 16 - len(text) % 16
    text = text + chr(pad) * pad
    encryptor = AES.new(key, 2, '0102030405060708')
    ciphertext = encryptor.encrypt(text)
    ciphertext = base64.b64encode(ciphertext).decode('utf-8')
    return ciphertext


def rsa(text, pubkey, modulus):
    text = text[::-1]
    rs = pow(int(binascii.hexlify(text), 16),
             int(pubkey, 16), int(modulus, 16))
    return format(rs, 'x').zfill(256)


def create_key(size):
    return binascii.hexlify(os.urandom(size))[:16]
