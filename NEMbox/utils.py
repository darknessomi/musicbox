#!/usr/bin/env python
# -*- coding: utf-8 -*-
# utils.py --- utils for musicbox
# Copyright (c) 2015-2016 omi & Contributors

import platform
import os


def notify_command_osx(msg, msg_type, t=None):
    command = '/usr/bin/osascript -e \'display notification "' + msg
    if msg_type == 1:
        command += '"sound name "/System/Library/Sounds/Ping.aiff'
    command += '"\''
    return command


def notify_command_linux(msg, t=None):
    command = '/usr/bin/notify-send "' + msg + '"'
    if t:
        command += ' -t ' + str(t)
    command += ' -h int:transient:1'
    return command


def notify(msg, msg_type=0, t=None):
    "Show system notification with duration t (ms)"
    if platform.system() == 'Darwin':
        command = notify_command_osx(msg, msg_type, t)
    else:
        command = notify_command_linux(msg, t)
    os.system(command)


if __name__ == "__main__":
    notify("test", t=1000)
