#!/usr/bin/env python
"""命令行扫码登录测试入口。

用法:
    uv run python tools/login_cli.py

流程：获取二维码 -> 终端打印二维码与链接 -> 轮询扫码状态 -> 成功后拉取账号信息。
"""

import io
import sys
import time

import qrcode

from NEMbox.api import NetEase


def render_qr(url):
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    buf = io.StringIO()
    qr.print_ascii(out=buf, invert=True)
    return buf.getvalue()


def main():
    api = NetEase()

    unikey = api.login_qr_key()
    if not unikey:
        print("获取二维码失败")
        return 1

    url = api.login_qr_url(unikey)
    print(render_qr(url))
    print(f"请用网易云音乐 App 扫描上方二维码，或打开链接：\n{url}\n")

    deadline = time.time() + 300
    last_code = None
    while time.time() < deadline:
        resp = api.login_qr_check(unikey)
        code = resp.get("code")
        if code != last_code:
            print(f"[{code}] {resp.get('message', '')}")
            last_code = code
        if code == 803:
            print("RESULT: SUCCESS 扫码登录成功")
            info = api.get_account_info()
            account = info.get("account") or {}
            profile = info.get("profile") or {}
            print(f"user_id: {account.get('id')}  nickname: {profile.get('nickname')}")
            return 0
        if code == 800:
            print("RESULT: FAILED 二维码已过期")
            return 1
        time.sleep(3)

    print("RESULT: TIMEOUT 超时未扫码")
    return 1


if __name__ == "__main__":
    sys.exit(main())
