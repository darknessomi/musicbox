#!/usr/bin/env python
import _curses
import curses
import sys
import traceback

from . import __version__
from .menu import Menu

# Keep the flock fd open for the TUI process lifetime (see daemon.acquire_lock).
_lock_fd: int | None = None


def start():
    argv = sys.argv[1:]
    if argv:
        from .cli import main

        sys.exit(main(argv))

    # TUI and daemon are mutually exclusive: both contend for the same flock.
    global _lock_fd
    from .daemon import acquire_lock, is_daemon_running

    if is_daemon_running():
        print(
            "musicbox daemon 正在运行，TUI 与 daemon 互斥。\n"
            "请先 `musicbox daemon stop`，或直接用 `musicbox status` 等命令控制播放。",
            file=sys.stderr,
        )
        sys.exit(4)
    _lock_fd = acquire_lock()
    if _lock_fd is None:
        print("无法获取 musicbox 运行锁，可能已有实例在运行。", file=sys.stderr)
        sys.exit(1)

    nembox_menu = Menu()
    try:
        nembox_menu.start_fork(__version__)
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
