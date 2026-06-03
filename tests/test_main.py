import sys

import pytest

from NEMbox import __main__


class _FakeNetEase:
    def get_version(self):
        return {"info": {"version": __main__.__version__}}


def test_version_command_does_not_initialize_menu(monkeypatch, capsys):
    def fail_menu():
        raise AssertionError("version command should not initialize Menu")

    monkeypatch.setattr(sys, "argv", ["musicbox", "--version"])
    monkeypatch.setattr(__main__, "NetEase", _FakeNetEase)
    monkeypatch.setattr(__main__, "Menu", fail_menu)

    with pytest.raises(SystemExit):
        __main__.start()

    assert (
        "NetEase-MusicBox installed version:" + __main__.__version__
        in capsys.readouterr().out
    )


def test_version_command_ignores_failed_latest_check(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["musicbox", "--version"])
    monkeypatch.setattr(__main__, "_check_latest_version", lambda: 0)

    with pytest.raises(SystemExit):
        __main__.start()

    assert "latest version:0" not in capsys.readouterr().out
