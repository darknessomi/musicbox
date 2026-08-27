from contextlib import contextmanager

import NEMbox.api as api_module
from NEMbox.api import PLAYLIST_CLASSES, NetEase


class _FakeSession:
    @contextmanager
    def cache_disabled(self):
        yield


def make_api():
    api = NetEase.__new__(NetEase)
    api._toplists_cache = None
    api._playlist_classes_cache = None
    api.session = _FakeSession()
    return api


class _JsonResponse:
    content = b"{}"

    def json(self):
        return {"code": 200}


def prepare_eapi(api, cookie_values):
    api._device_id = "device-id"
    api.header = {"X-Real-IP": "116.1.1.1", "X-Forwarded-For": "116.1.1.1"}
    api._get_cookie_value = lambda name: cookie_values.get(name, "")


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
        api,
        "cookie_jar",
        type("Jar", (), {"load": lambda self: None, "save": lambda self: None})(),
        raising=False,
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
    ensured = []

    monkeypatch.setattr(
        api,
        "cookie_jar",
        type(
            "Jar",
            (),
            {
                "load": lambda self: None,
                "save": lambda self: saved.append(True),
            },
        )(),
        raising=False,
    )
    monkeypatch.setattr(api, "_ensure_anon_cookies", lambda: ensured.append(True))
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
    assert ensured == [True]
    assert saved == [True, True]


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


def test_eapi_request_sends_music_u_and_nmtid_in_payload_and_cookie(monkeypatch):
    api = make_api()
    cookie_values = {
        "__csrf": "csrf-token",
        "MUSIC_U": "user-token",
        "MUSIC_A": "anonymous-token",
        "NMTID": "nmtid-token",
    }
    prepare_eapi(api, cookie_values)
    captured = {}

    class Session:
        def post(self, endpoint, data, headers, timeout):
            captured["endpoint"] = endpoint
            captured["headers"] = headers
            return _JsonResponse()

    def fake_eapi_encrypt(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"params": "encrypted"}

    api.session = Session()
    api.cookie_jar = type("Jar", (), {"save": lambda self: None})()
    monkeypatch.setattr(api_module, "eapi_encrypt", fake_eapi_encrypt)

    assert api.eapi_request("/api/test", {"id": 1}) == {"code": 200}
    header = captured["payload"]["header"]
    assert header["MUSIC_U"] == "user-token"
    assert header["NMTID"] == "nmtid-token"
    assert "MUSIC_A" not in header
    assert "MUSIC_U=user-token" in captured["headers"]["Cookie"]
    assert "NMTID=nmtid-token" in captured["headers"]["Cookie"]
    assert "MUSIC_A=" not in captured["headers"]["Cookie"]


def test_eapi_header_uses_music_a_without_logged_in_identity():
    api = make_api()
    prepare_eapi(
        api,
        {
            "MUSIC_A": "anonymous-token",
            "NMTID": "nmtid-token",
        },
    )

    header = api._eapi_header_cookie()

    assert header["MUSIC_A"] == "anonymous-token"
    assert header["NMTID"] == "nmtid-token"
    assert "MUSIC_U" not in header


def test_eapi_request_persists_first_nmtid(monkeypatch):
    api = make_api()
    cookie_values = {}
    prepare_eapi(api, cookie_values)
    saved = []

    class Session:
        def post(self, endpoint, data, headers, timeout):
            cookie_values["NMTID"] = "new-nmtid"
            return _JsonResponse()

    api.session = Session()
    api.cookie_jar = type("Jar", (), {"save": lambda self: saved.append(True)})()
    monkeypatch.setattr(api_module, "eapi_encrypt", lambda path, payload: {})

    assert api.eapi_request("/api/test") == {"code": 200}
    assert saved == [True]


def test_eapi_request_does_not_resave_existing_nmtid(monkeypatch):
    api = make_api()
    cookie_values = {"NMTID": "existing-nmtid"}
    prepare_eapi(api, cookie_values)
    saved = []
    api.session = type(
        "Session",
        (),
        {"post": lambda self, endpoint, data, headers, timeout: _JsonResponse()},
    )()
    api.cookie_jar = type("Jar", (), {"save": lambda self: saved.append(True)})()
    monkeypatch.setattr(api_module, "eapi_encrypt", lambda path, payload: {})

    assert api.eapi_request("/api/test") == {"code": 200}
    assert saved == []


def test_eapi_request_ignores_nmtid_save_failure(monkeypatch):
    api = make_api()
    cookie_values = {}
    prepare_eapi(api, cookie_values)
    warnings = []

    class Session:
        def post(self, endpoint, data, headers, timeout):
            cookie_values["NMTID"] = "new-nmtid"
            return _JsonResponse()

    class Jar:
        def save(self):
            raise RuntimeError("secret-new-nmtid")

    api.session = Session()
    api.cookie_jar = Jar()
    monkeypatch.setattr(api_module, "eapi_encrypt", lambda path, payload: {})
    monkeypatch.setattr(api_module.log, "warning", lambda *args: warnings.append(args))

    assert api.eapi_request("/api/test") == {"code": 200}
    assert warnings == [("failed to persist EAPI NMTID (%s)", "RuntimeError")]
    assert "secret-new-nmtid" not in repr(warnings)


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


def test_playlist_classes_are_dynamic_ordered_deduplicated_and_cached(monkeypatch):
    api = make_api()
    calls = []
    response = {
        "code": 200,
        "categories": {"4": "主题", "0": "语种", "1": "风格"},
        "sub": [
            {"name": "综艺", "category": 4},
            {"name": "华语", "category": 0},
            {"name": "流行", "category": 1},
            {"name": "综艺", "category": 4},
            {"name": "无效", "category": 9},
        ],
    }

    def fake_playlist_catelogs():
        calls.append(True)
        return response

    monkeypatch.setattr(api, "playlist_catelogs", fake_playlist_catelogs)

    assert api.dig_info([], "playlist_classes") == ["语种", "风格", "主题"]
    assert api.dig_info("主题", "playlist_class_detail") == ["综艺"]
    assert api.dig_info("语种", "playlist_class_detail") == ["华语"]
    assert calls == [True]


def test_playlist_classes_complete_two_level_tui_flow(monkeypatch):
    from NEMbox.menu import Menu

    api = make_api()
    monkeypatch.setattr(
        api,
        "playlist_catelogs",
        lambda: {
            "code": 200,
            "categories": {"0": "语种", "1": "风格"},
            "sub": [
                {"name": "华语", "category": 0},
                {"name": "流行", "category": 1},
            ],
        },
    )
    menu = Menu.__new__(Menu)
    menu.api = api
    menu.datatype = "recommend_lists"
    menu.title = "网易云音乐 > 精选歌单"
    menu.datalist = [
        {
            "title": "分类精选",
            "datatype": "playlist_classes",
            "callback": lambda: [],
        }
    ]
    menu.offset = 0
    menu.index = 0
    menu.stack = []

    menu.dispatch_enter(0)
    assert menu.datatype == "playlist_classes"
    assert menu.datalist == ["语种", "风格"]

    menu.dispatch_enter(1)
    assert menu.datatype == "playlist_class_detail"
    assert menu.datalist == ["流行"]


def test_playlist_classes_fall_back_on_invalid_response(monkeypatch):
    api = make_api()
    monkeypatch.setattr(api, "playlist_catelogs", lambda: {"code": 500})

    assert api.dig_info([], "playlist_classes") == list(PLAYLIST_CLASSES)
    assert api.dig_info("主题", "playlist_class_detail") == PLAYLIST_CLASSES["主题"]


def test_playlist_classes_fall_back_on_request_error(monkeypatch):
    api = make_api()

    def fail_playlist_catelogs():
        raise OSError("network unavailable")

    monkeypatch.setattr(api, "playlist_catelogs", fail_playlist_catelogs)

    assert api.dig_info([], "playlist_classes") == list(PLAYLIST_CLASSES)
