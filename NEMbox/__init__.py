#!/usr/bin/env python
# encoding: UTF-8

'''
网易云音乐 Entry
'''

from __future__ import absolute_import

import os.path
import sys
import curses, traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))
from NEMbox.menu import Menu


def start():
    nembox_menu = Menu()
    try:
        nembox_menu.start()
    except:
        # clean up terminal while failed
        nembox_menu.screen.keypad(1)
        curses.echo()
        curses.nocbreak()
        curses.endwin()
        traceback.print_exc()


if __name__ == '__main__':
    start()
