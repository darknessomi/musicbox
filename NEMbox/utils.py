#!/usr/bin/env python
# -*- coding: utf-8 -*-
# utils.py --- utils for musicbox
# Copyright (c) 2015-2016 omi & Contributors

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import str
from future import standard_library
standard_library.install_aliases()
import platform
import os


def utf8_data_to_file(f, data):
    if hasattr(data, 'decode'):
        f.write(data.decode('utf-8'))
    else:
        f.write(data)


def notify_command_osx(msg, msg_type, t=None):
    command = '/usr/bin/osascript -e "display notification \\\"{}\\\" {} with title \\\"musicbox\\\""'
    sound = 'sound name \\\"/System/Library/Sounds/Ping.aiff\\\"' if msg_type else ''
    return command.format(msg, sound)


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
    os.system(command.encode('utf-8'))


if __name__ == "__main__":
    notify("I'm test 1", msg_type=1, t=1000)
    notify("I'm test 2", msg_type=0, t=1000)
