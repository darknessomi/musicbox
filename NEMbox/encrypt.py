#!/usr/bin/env python
import base64
import binascii
import gzip
import hashlib
import json
import os
from typing import Any

from Cryptodome.Cipher import AES

__all__ = [
    "encrypted_id",
    "encrypted_request",
    "eapi_encrypt",
    "eapi_response_decrypt",
    "anonymous_username",
]

MODULUS = (
    "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7"
    "b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280"
    "104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932"
    "575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b"
    "3ece0462db0a22b8e7"
)
PUBKEY = "010001"
NONCE = b"0CoJUm6Qyw8W8jud"


# 歌曲加密算法, 基于https://github.com/yanunon/NeteaseCloudMusic
def encrypted_id(id):
    magic = bytearray("3go8&$8*3*3h0k(2)2", "u8")
    song_id = bytearray(id, "u8")
    magic_len = len(magic)
    for i, sid in enumerate(song_id):
        song_id[i] = sid ^ magic[i % magic_len]
    m = hashlib.md5(song_id)
    result = m.digest()
    result = base64.b64encode(result).replace(b"/", b"_").replace(b"+", b"-")
    return result.decode("utf-8")


# 登录加密算法, 基于https://github.com/stkevintan/nw_musicbox
def encrypted_request(text: Any) -> dict:
    data = json.dumps(text).encode("utf-8")
    secret = create_key(16)
    params = aes(aes(data, NONCE), secret)
    encseckey = rsa(secret, PUBKEY, MODULUS)
    return {"params": params, "encSecKey": encseckey}


def aes(text, key):
    pad = 16 - len(text) % 16
    text = text + bytearray([pad] * pad)
    encryptor = AES.new(key, 2, b"0102030405060708")
    ciphertext = encryptor.encrypt(text)
    return base64.b64encode(ciphertext)


def rsa(text, pubkey, modulus):
    text = text[::-1]
    rs = pow(int(binascii.hexlify(text), 16), int(pubkey, 16), int(modulus, 16))
    return format(rs, "x").zfill(256)


def create_key(size):
    return binascii.hexlify(os.urandom(size))[:16]


# 匿名设备注册用户名编码, 对照 api-enhanced module/register_anonimous.js
ANON_ID_XOR_KEY = b"3go8&$8*3*3h0k(2)2"


def _cloudmusic_dll_encode_id(some_id: str) -> str:
    raw = some_id.encode("utf-8")
    xored = bytes(
        b ^ ANON_ID_XOR_KEY[i % len(ANON_ID_XOR_KEY)] for i, b in enumerate(raw)
    )
    digest = hashlib.md5(xored).digest()
    return base64.b64encode(digest).decode("utf-8")


def anonymous_username(device_id: str) -> str:
    combined = f"{device_id} {_cloudmusic_dll_encode_id(device_id)}"
    return base64.b64encode(combined.encode("utf-8")).decode("utf-8")


EAPI_KEY = b"e82ckenh8dichen8"


def _pkcs7_pad(data: bytes) -> bytes:
    pad = 16 - len(data) % 16
    return data + bytes([pad] * pad)


def _pkcs7_unpad(data: bytes) -> bytes:
    pad = data[-1]
    if pad < 1 or pad > 16:
        raise ValueError("invalid PKCS7 padding")
    return data[:-pad]


def eapi_encrypt(uri: str, payload: dict) -> dict:
    """eapi 请求体加密，对照 api-enhanced util/crypto.js eapi()."""
    text = json.dumps(payload, separators=(",", ":"))
    message = f"nobody{uri}use{text}md5forencrypt"
    digest = hashlib.md5(message.encode("utf-8")).hexdigest()
    plain = f"{uri}-36cd479b6b5-{text}-36cd479b6b5-{digest}"
    cipher = AES.new(EAPI_KEY, AES.MODE_ECB)
    encrypted = cipher.encrypt(_pkcs7_pad(plain.encode("utf-8")))
    return {"params": encrypted.hex().upper()}


def eapi_response_decrypt(content) -> dict:
    """eapi 响应解密，对照 api-enhanced util/crypto.js eapiResDecrypt()."""
    if isinstance(content, str):
        raw = content.strip()
        if not raw:
            raise ValueError("empty eapi response")
        ciphertext = bytes.fromhex(raw)
    else:
        ciphertext = content

    cipher = AES.new(EAPI_KEY, AES.MODE_ECB)
    decrypted = _pkcs7_unpad(cipher.decrypt(ciphertext))
    if len(decrypted) >= 2 and decrypted[0] == 0x1F and decrypted[1] == 0x8B:
        decrypted = gzip.decompress(decrypted)
    return json.loads(decrypted.decode("utf-8"))
