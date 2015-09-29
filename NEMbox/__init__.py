#!/usr/bin/env python
# encoding: UTF-8

'''
网易云音乐 Entry
'''

import curses, traceback
from menu import Menu
import argparse
import sys

version = "0.1.9.4"

def start():
    nembox_menu = Menu()
    try:
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
        print 'NetEase-MusicBox latest version:' + latest
    sys.exit()
