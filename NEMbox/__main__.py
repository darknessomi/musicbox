#!/usr/bin/env python
import _curses
import argparse
import contextlib
import curses
import sys
import traceback

from . import __version__
from .api import NetEase
from .menu import Menu


def _check_latest_version():
    try:
        return NetEase().get_version()["info"]["version"]
    except (KeyError, TypeError):
        return 0


def start():
    version = __version__

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--version", help="show this version and exit", action="store_true"
    )
    args = parser.parse_args()

    if args.version:
        latest = _check_latest_version()
        with contextlib.suppress(_curses.error):
            curses.endwin()
        print("NetEase-MusicBox installed version:" + version)
        if latest and latest != version:
            print("NetEase-MusicBox latest version:" + str(latest))
        sys.exit()

    nembox_menu = Menu()
    try:
        nembox_menu.start_fork(version)
    except (OSError, TypeError, ValueError, KeyError, IndexError):
        # clean up terminal while failed
        try:
            curses.echo()
            curses.nocbreak()
            curses.endwin()
        except _curses.error:
            pass
        traceback.print_exc()


if __name__ == "__main__":
    start()
