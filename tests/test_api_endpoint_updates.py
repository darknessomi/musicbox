from contextlib import contextmanager

from NEMbox.api import NetEase


class _FakeSession:
    @contextmanager
    def cache_disabled(self):
        yield


def make_api():
    api = NetEase.__new__(NetEase)
    api._toplists_cache = None
    api.session = _FakeSession()
    return api


def test_get_account_info_uses_current_account_endpoint(monkeypatch):
    api = make_api()
    calls = []

    def fake_request(method, path, params=None):
        calls.append((method, path, params))
        return {"code": 200, "account": {"id": 1}, "profile": {"nickname": "u"}}

    monkeypatch.setattr(api, "request", fake_request)

    assert api.get_account_info() == {
        "code": 200,
        "account": {"id": 1},
        "profile": {"nickname": "u"},
    }
    assert calls == [("POST", "/weapi/nuser/account/get", None)]


def test_get_account_info_falls_back_to_legacy_w_endpoint(monkeypatch):
    api = make_api()
    calls = []

    def fake_request(method, path, params=None):
        calls.append((method, path, params))
        if path == "/weapi/nuser/account/get":
            return {"code": -1}
        return {"code": 200, "account": {"id": 1}}

    monkeypatch.setattr(api, "request", fake_request)

    assert api.get_account_info() == {"code": 200, "account": {"id": 1}}
    assert calls == [
        ("POST", "/weapi/nuser/account/get", None),
        ("POST", "/weapi/w/nuser/account/get", None),
    ]


def test_login_qr_key_uses_type_3_and_reads_nested_unikey(monkeypatch):
    api = make_api()
    calls = []

    monkeypatch.setattr(
        api, "cookie_jar", type("Jar", (), {"load": lambda self: None})(), raising=False
    )
    monkeypatch.setattr(api, "_ensure_anon_cookies", lambda: None)

    def fake_request(method, path, params=None):
        calls.append((method, path, params))
        return {"code": 200, "data": {"code": 200, "unikey": "abc"}}

    monkeypatch.setattr(api, "request", fake_request)

    assert api.login_qr_key() == "abc"
    assert calls == [("POST", "/weapi/login/qrcode/unikey", {"type": 3})]


def test_login_qr_check_uses_type_3_and_applies_cookie(monkeypatch):
    api = make_api()
    calls = []
    applied = []
    saved = []

    monkeypatch.setattr(
        api,
        "cookie_jar",
        type("Jar", (), {"save": lambda self: saved.append(True)})(),
        raising=False,
    )
    monkeypatch.setattr(api, "_apply_cookie_string", applied.append)

    def fake_request(method, path, params=None):
        calls.append((method, path, params))
        return {"code": 803, "cookie": "MUSIC_U=token; __csrf=csrf"}

    monkeypatch.setattr(api, "request", fake_request)

    assert api.login_qr_check("abc") == {
        "code": 803,
        "cookie": "MUSIC_U=token; __csrf=csrf",
    }
    assert calls == [
        ("POST", "/weapi/login/qrcode/client/login", {"type": 3, "key": "abc"})
    ]
    assert applied == ["MUSIC_U=token; __csrf=csrf"]
    assert saved == [True]


def test_recommend_playlist_reads_v3_daily_songs(monkeypatch):
    api = make_api()
    calls = []
    songs = [{"id": 1}, {"id": 2}, {"id": 3}]

    def fake_request(method, path, params=None):
        calls.append((method, path, params))
        return {"data": {"dailySongs": songs}}

    monkeypatch.setattr(api, "request", fake_request)

    assert api.recommend_playlist(offset=1, limit=1) == [{"id": 2}]
    assert calls == [("POST", "/weapi/v3/discovery/recommend/songs", {"afresh": False})]


def test_playlist_songlist_uses_v6_detail_eapi(monkeypatch):
    api = make_api()
    calls = []
    track_ids = [{"id": 1}, {"id": 2}]

    def fake_eapi_request(path, params=None):
        calls.append((path, params))
        return {"playlist": {"trackIds": track_ids}}

    monkeypatch.setattr(api, "eapi_request", fake_eapi_request)

    assert api.playlist_songlist(123) == track_ids
    assert calls == [("/api/v6/playlist/detail", {"id": 123, "n": 100000, "s": 8})]


def test_song_lyrics_use_v1_lyric_eapi(monkeypatch):
    api = make_api()
    calls = []

    def fake_eapi_request(path, params=None):
        calls.append((path, params))
        return {
            "lrc": {"lyric": "[00:00.00]hello\n[00:01.00]world"},
            "tlyric": {"lyric": "[00:00.00]nihao"},
        }

    monkeypatch.setattr(api, "eapi_request", fake_eapi_request)

    assert api.song_lyric(456) == ["[00:00.00]hello", "[00:01.00]world"]
    assert api.song_tlyric(456) == ["[00:00.00]nihao"]
    assert calls[0][0] == "/api/song/lyric/v1"
    assert calls[0][1]["id"] == 456
    assert calls[0][1]["lv"] == 0


def test_dj_radios_uses_current_hot_endpoint(monkeypatch):
    api = make_api()
    calls = []
    radios = [{"id": 1}]

    def fake_request(method, path, params=None):
        calls.append((method, path, params))
        return {"djRadios": radios}

    monkeypatch.setattr(api, "request", fake_request)

    assert api.djRadios(offset=10, limit=5) == radios
    assert calls == [("POST", "/weapi/djradio/hot/v1", {"limit": 5, "offset": 10})]


def _fake_toplist_response():
    return type(
        "Resp",
        (),
        {
            "json": lambda self: {
                "code": 200,
                "list": [
                    {"id": 3779629, "name": "新歌榜"},
                    {"id": 3778678, "name": "热歌榜"},
                ],
            }
        },
    )()


def test_logout_calls_eapi_logout_before_clearing_local(monkeypatch):
    api = make_api()
    eapi_calls = []
    cleared = []
    saved = []

    def fake_eapi_request(path, params=None):
        eapi_calls.append((path, params or {}))
        return {"code": 200}

    class FakeCookies:
        def clear(self):
            cleared.append(True)

    api.session.cookies = FakeCookies()
    api.cookie_jar = type("Jar", (), {"save": lambda self: saved.append(True)})()
    api.storage = type(
        "Storage",
        (),
        {
            "database": {
                "user": {
                    "username": "u",
                    "password": "",
                    "user_id": "1",
                    "nickname": "n",
                }
            },
            "save": lambda self: None,
        },
    )()

    monkeypatch.setattr(api, "eapi_request", fake_eapi_request)

    api.logout()

    assert eapi_calls == [("/api/logout", {})]
    assert cleared == [True]
    assert saved == [True]
    assert api.storage.database["user"]["nickname"] == ""


def test_fetch_toplists_uses_api_toplist(monkeypatch):
    api = make_api()
    calls = []

    def fake_raw_request(method, endpoint, data=None):
        calls.append((method, endpoint, data))
        return _fake_toplist_response()

    monkeypatch.setattr(api, "_raw_request", fake_raw_request)

    assert api.fetch_toplists() == [("新歌榜", "3779629"), ("热歌榜", "3778678")]
    assert calls == [("GET", "https://music.163.com/api/toplist", None)]


def test_toplists_property_caches_result(monkeypatch):
    api = make_api()
    calls = []

    def fake_raw_request(method, endpoint, data=None):
        calls.append((method, endpoint, data))
        return _fake_toplist_response()

    monkeypatch.setattr(api, "_raw_request", fake_raw_request)

    assert api.toplists == ["新歌榜", "热歌榜"]
    assert api.toplists == ["新歌榜", "热歌榜"]
    assert len(calls) == 1


def test_top_songlist_uses_dynamic_id(monkeypatch):
    api = make_api()
    playlist_calls = []

    monkeypatch.setattr(
        api,
        "fetch_toplists",
        lambda: [("新歌榜", "3779629"), ("热歌榜", "3778678")],
    )

    def fake_playlist_songlist(playlist_id):
        playlist_calls.append(playlist_id)
        return [{"id": playlist_id}]

    monkeypatch.setattr(api, "playlist_songlist", fake_playlist_songlist)

    assert api.top_songlist(1) == [{"id": "3778678"}]
    assert playlist_calls == ["3778678"]
