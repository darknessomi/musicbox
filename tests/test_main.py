import sys

import pytest

from NEMbox import __main__, cli


class _FakeNetEase:
    def get_version(self):
        return {"info": {"version": __main__.__version__}}


def test_version_command_does_not_initialize_menu(monkeypatch, capsys):
    def fail_menu():
        raise AssertionError("version command should not initialize Menu")

    monkeypatch.setattr(sys, "argv", ["musicbox", "--version"])
    monkeypatch.setattr(cli, "NetEase", _FakeNetEase)
    monkeypatch.setattr(__main__, "Menu", fail_menu)

    with pytest.raises(SystemExit) as exc:
        __main__.start()

    assert exc.value.code == 0
    assert (
        "NetEase-MusicBox installed version:" + __main__.__version__
        in capsys.readouterr().out
    )


def test_version_command_ignores_failed_latest_check(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["musicbox", "--version"])
    monkeypatch.setattr(cli, "check_latest_version", lambda: 0)

    with pytest.raises(SystemExit) as exc:
        __main__.start()

    assert exc.value.code == 0
    assert "latest version:0" not in capsys.readouterr().out


def test_tui_exits_4_when_daemon_running(monkeypatch, capsys):
    from NEMbox import daemon as daemon_mod

    monkeypatch.setattr(sys, "argv", ["musicbox"])
    monkeypatch.setattr(daemon_mod, "is_daemon_running", lambda: True)

    with pytest.raises(SystemExit) as exc:
        __main__.start()

    assert exc.value.code == 4
    assert "daemon" in capsys.readouterr().err


def test_tui_exits_1_when_lock_unavailable(monkeypatch, capsys):
    from NEMbox import daemon as daemon_mod

    monkeypatch.setattr(sys, "argv", ["musicbox"])
    monkeypatch.setattr(daemon_mod, "is_daemon_running", lambda: False)
    monkeypatch.setattr(daemon_mod, "acquire_lock", lambda: None)

    with pytest.raises(SystemExit) as exc:
        __main__.start()

    assert exc.value.code == 1
    assert "运行锁" in capsys.readouterr().err
