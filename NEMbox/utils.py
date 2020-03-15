#!/usr/bin/env python
# -*- coding: utf-8 -*-
# utils.py --- utils for musicbox
# Copyright (c) 2015-2016 omi & Contributors
# from __future__ import (
#print_function, unicode_literals, division, absolute_import
# )

import platform
import subprocess
import os
from collections import OrderedDict
from copy import deepcopy

#from future.builtins import str
"""
定义几个函数 写文件 通知 返回键 创建目录 创建文件
"""

__all__ = [
    'utf8_data_to_file', 'notify', 'uniq', 'create_dir', 'create_file', 'parse_keylist'
]


def parse_keylist(keylist):
    """
    '2' '3' '4' 'j'  ----> 234 j
    supoort keys  [  ]   j  k  <KEY_UP> <KEY_DOWN>
    """
    keylist = deepcopy(keylist)
    if keylist == []:
        return None
    tail_cmd = keylist.pop()
    if tail_cmd in (ord('['), ord(']'), ord('j'), ord('k'), 258, 259) and \
            max(keylist) <= 57 and min(keylist) >= 48:
        return (int(''.join([chr(i) for i in keylist])), tail_cmd)
    return None


def mkdir(path):
    try:
        os.mkdir(path)
        return True
    except OSError:
        return False


def create_dir(path):
    if not os.path.exists(path):
        return mkdir(path)

    if os.path.isdir(path):
        return True

    os.remove(path)
    return mkdir(path)


def create_file(path, default='\n'):
    if not os.path.exists(path):
        with open(path, 'w') as f:
            f.write(default)


def uniq(arr):
    return list(OrderedDict.fromkeys(arr).keys())


def utf8_data_to_file(f, data):
    if hasattr(data, 'decode'):
        f.write(data.decode('utf-8'))
    else:
        f.write(data)


def notify(msg, msg_type=0, t=None):
    msg = msg.replace('"', '\\"')
    command = ['/usr/bin/osascript', '-e']
    tpl = "display notification \"{}\" {} with title \"musicbox\""
    sound = 'sound name \"/System/Library/Sounds/Ping.aiff\"' if msg_type else ''
    command.append(tpl.format(msg, sound).encode('utf-8'))
    try:
        subprocess.call(command)
        return True
    except OSError as e:
        return False


if __name__ == "__main__":
    notify("I'm test \"\"quote", msg_type=1, t=1000)
    notify("I'm test 1", msg_type=1, t=1000)
    notify("I'm test 2", msg_type=0, t=1000)
    print(parse_keylist([48, 49, 55, 91]))
