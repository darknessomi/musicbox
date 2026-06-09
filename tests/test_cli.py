import json
import sys

import pytest

from NEMbox import cli


class FakeNetEase:
    def search(self, keywords, stype=1, offset=0, total="true", limit=50):
        return {
            "songs": [
                {
                    "id": 33894312,
                    "name": "邂逅",
                    "ar": [{"name": "周杰伦"}],
                    "al": {"name": "范特西", "id": 1},
                    "dt": 273000,
                }
            ]
        }

    def dig_info(self, data, dig_type):
        if dig_type == "songs":
            return [
                {
                    "song_id": 33894312,
                    "song_name": "邂逅",
                    "artist": "周杰伦",
                    "album_name": "范特西",
                }
            ]
        if dig_type == "artists":
            return [{"artist_id": 1, "artist_name": "周杰伦"}]
        if dig_type == "playlists":
            return [{"playlist_id": 1, "playlist_name": "测试歌单"}]
        return data

    def songs_detail(self, ids):
        return [{"id": ids[0], "name": "邂逅", "ar": [{"name": "周杰伦"}]}]

    def songs_url(self, ids):
        return [{"id": ids[0], "url": "http://example.com/song.mp3", "br": 320000}]

    def playlist_songlist(self, playlist_id):
        return [{"id": 33894312}]

    def fetch_toplists(self):
        return [("飙升榜", "19723756")]

    def top_songlist(self, idx=0, offset=0, limit=100):
        return [{"id": 33894312, "name": "邂逅", "ar": [{"name": "周杰伦"}]}]

    def get_account_info(self):
        return {}

    def recommend_playlist(self, total=True, offset=0, limit=20):
        return [{"id": 33894312, "name": "邂逅", "ar": [{"name": "周杰伦"}]}]

    def recommend_resource(self):
        return [{"id": 1, "name": "每日推荐歌单"}]

    def personal_fm(self):
        return [{"id": 33894312, "name": "邂逅", "ar": [{"name": "周杰伦"}]}]

    def song_comments(self, music_id, offset=0, total="false", limit=100):
        return {
            "comments": [{"user": {"nickname": "用户A"}, "content": "好听"}],
            "total": 1,
        }

    def fm_like(self, songid, like=True, time=25, alg="itembased"):
        return True

    def login_qr_key(self):
        return "test-unikey"

    @staticmethod
    def login_qr_url(unikey):
        return f"https://music.163.com/login?codekey={unikey}"

    def login_qr_check(self, unikey):
        return {"code": 801, "message": "waiting"}

    def logout(self):
        pass

    def get_version(self):
        return {"info": {"version": "9.9.9"}}


class LoggedInNetEase(FakeNetEase):
    def get_account_info(self):
        return {
            "account": {"id": 12345},
            "profile": {"nickname": "测试用户"},
        }

    def login_qr_check(self, unikey):
        return {"code": 803, "message": "success"}


def _run(monkeypatch, argv, api_cls=FakeNetEase):
    monkeypatch.setattr(cli, "NetEase", api_cls)
    return cli.main(argv)


def test_search_json_output(monkeypatch, capsys):
    code = _run(monkeypatch, ["search", "周杰伦", "--type", "song", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"][0]["song_id"] == 33894312
    assert "_notice" in payload


def test_search_quiet(monkeypatch, capsys):
    code = _run(monkeypatch, ["search", "周杰伦", "--quiet"])
    assert code == 0
    assert capsys.readouterr().out.strip() == "33894312"


def test_song_info_human(monkeypatch, capsys):
    code = _run(monkeypatch, ["song", "info", "33894312"])
    assert code == 0
    out = capsys.readouterr().out
    assert "33894312" in out
    assert "邂逅" in out


def test_song_url_quiet(monkeypatch, capsys):
    code = _run(monkeypatch, ["song", "url", "33894312", "--quiet"])
    assert code == 0
    assert capsys.readouterr().out.strip() == "http://example.com/song.mp3"


def test_recommend_not_logged_in(monkeypatch, capsys):
    code = _run(monkeypatch, ["recommend", "songs", "--json"])
    assert code == 3
    err = json.loads(capsys.readouterr().err)
    assert err["error"]["type"] == "not_logged_in"


def test_recommend_songs_logged_in(monkeypatch, capsys):
    code = _run(monkeypatch, ["recommend", "songs", "--json"], LoggedInNetEase)
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_auth_login_no_wait(monkeypatch, capsys):
    code = _run(monkeypatch, ["auth", "login", "--no-wait", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["unikey"] == "test-unikey"
    assert "qr_ascii" in payload["data"]
    assert "login_url" not in payload["data"]
    assert "codekey" not in payload["data"]["qr_ascii"]


def test_auth_login_without_no_wait_fails(monkeypatch, capsys):
    code = _run(monkeypatch, ["auth", "login", "--json"])
    assert code == 2
    err = json.loads(capsys.readouterr().err)
    assert err["error"]["type"] == "invalid_args"


def test_auth_login_check_success(monkeypatch, capsys):
    code = _run(
        monkeypatch,
        ["auth", "login", "--check", "test-unikey", "--json"],
        LoggedInNetEase,
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["status"] == "success"


def test_auth_logout_requires_confirmation(monkeypatch, capsys):
    code = _run(monkeypatch, ["auth", "logout", "--json"])
    assert code == 10
    err = json.loads(capsys.readouterr().err)
    assert err["error"]["type"] == "confirmation_required"


def test_auth_logout_with_yes(monkeypatch, capsys):
    code = _run(monkeypatch, ["auth", "logout", "--yes", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["logged_out"] is True


def test_toplist_list(monkeypatch, capsys):
    code = _run(monkeypatch, ["toplist", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"][0]["name"] == "飙升榜"


def test_config_get(monkeypatch, capsys):
    code = _run(monkeypatch, ["config", "get", "music_quality", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert "music_quality" in payload["data"]


def test_config_list_handles_bare_version(monkeypatch, capsys):
    code = _run(monkeypatch, ["config", "list", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert "version" in payload["data"]
    assert isinstance(payload["data"]["version"], int)


def test_config_get_version(monkeypatch, capsys):
    code = _run(monkeypatch, ["config", "get", "version", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload["data"]["version"], int)


def test_config_unknown_key(monkeypatch, capsys):
    code = _run(monkeypatch, ["config", "get", "nonexistent_key", "--json"])
    assert code == 2
    err = json.loads(capsys.readouterr().err)
    assert err["error"]["type"] == "invalid_args"


def test_root_help_banner(capsys):
    code = cli.main(["-h"])
    assert code == 0
    out = capsys.readouterr().out
    assert "USAGE:" in out
    assert "EXAMPLES:" in out
    assert "AI AGENT SKILLS:" in out
    assert "COMMUNITY:" in out
    assert "npx skills add darknessomi/musicbox" in out
    assert "Available Commands:" in out or "positional arguments:" in out


def test_version_via_cli(monkeypatch, capsys):
    monkeypatch.setattr(cli, "check_latest_version", lambda: 0)
    code = cli.main(["-v"])
    assert code == 0
    assert "NetEase-MusicBox installed version:" in capsys.readouterr().out


_STATUS_DATA = {
    "state": "playing",
    "song": {
        "id": 33894312,
        "name": "邂逅",
        "artist": "周杰伦",
        "album": "范特西",
        "duration": 273,
    },
    "position": 0,
    "length": 273,
    "volume": 60,
    "mode": "ordered",
    "backend": "mpv",
    "queue_index": 0,
    "queue_size": 1,
}


class FakeDaemon:
    """Records RPC calls and replays canned responses for control commands."""

    def __init__(self, running=True, responses=None):
        self.running = running
        self.responses = responses or {}
        self.calls = []
        self.spawned = False

    def is_running(self):
        return self.running

    def spawn(self):
        self.spawned = True
        self.running = True
        return True

    def send(self, method, params=None):
        self.calls.append((method, params or {}))
        if method in self.responses:
            return self.responses[method]
        return {"id": 1, "ok": True, "data": _STATUS_DATA}


def _patch_daemon(monkeypatch, fake):
    monkeypatch.setattr(cli, "is_daemon_running", fake.is_running)
    monkeypatch.setattr(cli, "spawn_daemon", fake.spawn)
    monkeypatch.setattr(cli, "send_request", fake.send)
    return fake


def test_status_json(monkeypatch, capsys):
    _patch_daemon(monkeypatch, FakeDaemon())
    code = cli.main(["status", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["state"] == "playing"


def test_play_dry_run_has_no_side_effect(monkeypatch, capsys):
    fake = _patch_daemon(monkeypatch, FakeDaemon(running=False))
    code = cli.main(["play", "--id", "33894312", "--dry-run", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["method"] == "player.play"
    assert payload["data"]["params"]["id"] == 33894312
    assert fake.calls == []
    assert fake.spawned is False


def test_control_autostarts_daemon(monkeypatch, capsys):
    fake = _patch_daemon(monkeypatch, FakeDaemon(running=False))
    code = cli.main(["pause", "--json"])
    capsys.readouterr()
    assert code == 0
    assert fake.spawned is True
    assert fake.calls[0][0] == "player.pause"


def test_daemon_not_running_no_autostart(monkeypatch, capsys):
    _patch_daemon(monkeypatch, FakeDaemon(running=False))
    code = cli.main(["status", "--no-daemon-autostart", "--json"])
    assert code == 4
    err = json.loads(capsys.readouterr().err)
    assert err["error"]["type"] == "daemon_not_running"


def test_volume_relative_params(monkeypatch, capsys):
    fake = _patch_daemon(monkeypatch, FakeDaemon())
    code = cli.main(["volume", "+10", "--json"])
    capsys.readouterr()
    assert code == 0
    assert fake.calls[0] == ("player.volume", {"delta": 10})


def test_volume_absolute_params(monkeypatch, capsys):
    fake = _patch_daemon(monkeypatch, FakeDaemon())
    code = cli.main(["volume", "50", "--json"])
    capsys.readouterr()
    assert code == 0
    assert fake.calls[0] == ("player.volume", {"value": 50})


def test_queue_clear_requires_confirmation(monkeypatch, capsys):
    fake = _patch_daemon(monkeypatch, FakeDaemon())
    code = cli.main(["queue", "clear", "--json"])
    assert code == 10
    err = json.loads(capsys.readouterr().err)
    assert err["error"]["type"] == "confirmation_required"
    assert fake.calls == []


def test_queue_clear_with_yes(monkeypatch, capsys):
    fake = _patch_daemon(
        monkeypatch,
        FakeDaemon(
            responses={
                "queue.clear": {
                    "id": 1,
                    "ok": True,
                    "data": {"items": [], "index": 0, "size": 0},
                }
            }
        ),
    )
    code = cli.main(["queue", "clear", "--yes", "--json"])
    capsys.readouterr()
    assert code == 0
    assert fake.calls[0][0] == "queue.clear"


def test_seek_not_supported_maps_to_exit_5(monkeypatch, capsys):
    _patch_daemon(
        monkeypatch,
        FakeDaemon(
            responses={
                "player.seek": {
                    "id": 1,
                    "ok": False,
                    "error": {
                        "type": "not_supported",
                        "message": "mpg123 后端不支持 seek",
                    },
                }
            }
        ),
    )
    code = cli.main(["seek", "90", "--json"])
    assert code == 5
    err = json.loads(capsys.readouterr().err)
    assert err["error"]["type"] == "not_supported"


def test_connection_error_returns_exit_4(monkeypatch, capsys):
    def boom(method, params=None):
        raise ConnectionError("no daemon")

    monkeypatch.setattr(cli, "is_daemon_running", lambda: True)
    monkeypatch.setattr(cli, "send_request", boom)
    code = cli.main(["status", "--json"])
    assert code == 4
    err = json.loads(capsys.readouterr().err)
    assert err["error"]["type"] == "daemon_not_running"


def test_daemon_status_command(monkeypatch, capsys):
    monkeypatch.setattr(cli, "is_daemon_running", lambda: False)
    code = cli.main(["daemon", "status", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["running"] is False


def test_cli_entry_dispatches_from_main(monkeypatch):
    import NEMbox.__main__ as main_mod

    called = {}

    def fake_main(argv):
        called["argv"] = argv
        return 0

    monkeypatch.setattr(sys, "argv", ["musicbox", "search", "test", "--json"])
    import NEMbox.cli as cli_mod

    monkeypatch.setattr(cli_mod, "main", fake_main)

    with pytest.raises(SystemExit) as exc:
        main_mod.start()
    assert exc.value.code == 0
    assert called["argv"] == ["search", "test", "--json"]
