#!/usr/bin/env python
# -*- coding: utf-8 -*-
# utils.py --- utils for musicbox
# Copyright (c) 2015-2016 omi & Contributors
from __future__ import print_function, unicode_literals, division, absolute_import

import platform
import subprocess
import os
from collections import OrderedDict

from future.builtins import str


__all__ = ["utf8_data_to_file", "notify", "uniq", "create_dir", "create_file"]


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


def create_file(path, default="\n"):
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(default)


def uniq(arr):
    return list(OrderedDict.fromkeys(arr).keys())


def utf8_data_to_file(f, data):
    if hasattr(data, "decode"):
        f.write(data.decode("utf-8"))
    else:
        f.write(data)


def notify_command_osx(msg, msg_type, t=None):
    command = ["/usr/bin/osascript", "-e"]
    tpl = 'display notification "{}" {} with title "musicbox"'
    sound = 'sound name "/System/Library/Sounds/Ping.aiff"' if msg_type else ""
    command.append(tpl.format(msg, sound).encode("utf-8"))
    return command


def notify_command_linux(msg, t=None):
    command = ["/usr/bin/notify-send"]
    command.append(msg.encode("utf-8"))
    if t:
        command.extend(["-t", str(t)])
    command.extend(["-h", "int:transient:1"])
    return command


def notify(msg, msg_type=0, t=None):
    msg = msg.replace('"', '\\"')
    "Show system notification with duration t (ms)"
    if platform.system() == "Darwin":
        command = notify_command_osx(msg, msg_type, t)
    else:
        command = notify_command_linux(msg, t)

    try:
        subprocess.call(command)
        return True
    except OSError as e:
        return False


if __name__ == "__main__":
    notify('I\'m test ""quote', msg_type=1, t=1000)
    notify("I'm test 1", msg_type=1, t=1000)
    notify("I'm test 2", msg_type=0, t=1000)
