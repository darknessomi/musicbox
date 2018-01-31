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
from . import logger
standard_library.install_aliases()
import platform
import subprocess

log = logger.getLogger(__name__)

def utf8_data_to_file(f, data):
    if hasattr(data, 'decode'):
        f.write(data.decode('utf-8'))
    else:
        f.write(data)


def notify_command_osx(msg, msg_type, t=None):
    command = ['/usr/bin/osascript', '-e']
    tpl = "display notification \"{}\" {} with title \"MusicBox\""
    sound = 'sound name \"/System/Library/Sounds/Ping.aiff\"' if msg_type else ''
    command.append(tpl.format(msg, sound).encode('UTF-8'))
    return command


def notify_command_linux(msg, t=None):
    command = ['/usr/bin/notify-send']
    command.append(msg.encode('UTF-8'))
    if t:
        command.extend(['-t', str(t)])
    command.extend(['-h', 'int:transient:1'])
    return command


def notify(msg, msg_type=0, t=None):
    "Show system notification with duration t (ms)"
    if platform.system() == 'Darwin':
        command = notify_command_osx(msg, msg_type, t)
    else:
        command = notify_command_linux(msg, t)
    try:
        subprocess.call(command)
    except OSError as e:
        log.warning('Sending notification error.')

if __name__ == "__main__":
    notify("I'm test 1", msg_type=1, t=1000)
    notify("I'm test 2", msg_type=0, t=1000)
