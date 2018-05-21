#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
网易云音乐 Entry
'''
from __future__ import (
    print_function, unicode_literals, division, absolute_import
)
import curses
import traceback
import argparse
import sys

from future.builtins import str

from .menu import Menu

version = '0.2.4.3'


def start():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v",
                        "--version",
                        help="show this version and exit",
                        action="store_true")
    args = parser.parse_args()
    if args.version:
        latest = Menu().check_version()
        curses.endwin()
        print('NetEase-MusicBox installed version:' + version)
        if latest != version:
            print('NetEase-MusicBox latest version:' + str(latest))
        sys.exit()

    nembox_menu = Menu()
    try:
        nembox_menu.start_fork(version)
    except (OSError, TypeError, ValueError, KeyError):
        # clean up terminal while failed
        nembox_menu.screen.keypad(1)
        curses.echo()
        curses.nocbreak()
        curses.endwin()
        traceback.print_exc()


if __name__ == '__main__':
    start()
