#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import curses
import sys
import traceback
from pathlib import Path

import toml

from .menu import Menu


def get_current_version():
    path = Path(".").parent.parent / "pyproject.toml"
    with path.open() as f:
        config = toml.load(f)
    return config["tool"]["poetry"]["version"]


def start():
    version = get_current_version()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--version", help="show this version and exit", action="store_true"
    )
    args = parser.parse_args()
    if args.version:
        latest = Menu().check_version()
        curses.endwin()
        print("NetEase-MusicBox installed version:" + version)
        if latest != version:
            print("NetEase-MusicBox latest version:" + str(latest))
        sys.exit()

    nembox_menu = Menu()
    try:
        nembox_menu.start_fork(version)
    except (OSError, TypeError, ValueError, KeyError, IndexError):
        # clean up terminal while failed
        curses.echo()
        curses.nocbreak()
        curses.endwin()
        traceback.print_exc()


if __name__ == "__main__":
    start()
