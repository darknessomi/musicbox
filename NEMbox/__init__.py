#!/usr/bin/env python
# encoding: UTF-8

'''
网易云音乐 Entry
'''

import curses
import traceback
from menu import Menu
import argparse
from osdlyrics import show_lyrics_new_process
import sys

version = "0.2.1.8"


def start():
    nembox_menu = Menu()
    try:
        show_lyrics_new_process()
        nembox_menu.start_fork(version)
    except:
        # clean up terminal while failed
        nembox_menu.screen.keypad(1)
        curses.echo()
        curses.nocbreak()
        curses.endwin()
        traceback.print_exc()


if __name__ == '__main__':
    start()

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--version", help="show this version and exit", action="store_true")
args = parser.parse_args()
if args.version:
    latest = Menu().check_version()
    curses.endwin()
    print 'NetEase-MusicBox installed version:' + version
    if latest != version:
        print 'NetEase-MusicBox latest version:' + str(latest)
    sys.exit()
