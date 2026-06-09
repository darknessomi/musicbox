from unittest.mock import PropertyMock, patch

from NEMbox.player import Player


def test_playing_id_is_none_without_current_song():
    with patch.object(
        Player, "current_song", new_callable=PropertyMock, return_value={}
    ):
        player = Player.__new__(Player)
        assert player.playing_id is None


class FakePopen:
    def poll(self):
        return None


def test_mpv_switch_uses_ipc_pause_command():
    player = Player.__new__(Player)
    player.popen_handler = FakePopen()
    player.current_backend = "mpv"
    player.playing_flag = True
    player.build_playinfo = lambda: None
    commands = []
    player._send_mpv_command = commands.append

    player.switch()
    player.switch()

    assert commands == [
        ["set_property", "pause", True],
        ["set_property", "pause", False],
    ]


def test_stale_playback_token_is_not_current():
    player = Player.__new__(Player)
    process = FakePopen()
    player.popen_handler = process
    player.playback_token = 2

    assert player._is_current_playback(2, process)
    assert not player._is_current_playback(1, process)
    assert not player._is_current_playback(2, FakePopen())


def test_format_audio_params():
    assert (
        Player._format_audio_params({"samplerate": 44100, "format": "s16"})
        == "44.1kHz 16bit"
    )
    assert (
        Player._format_audio_params({"samplerate": 96000, "format": "s24"})
        == "96kHz 24bit"
    )
    assert (
        Player._format_audio_params({"samplerate": 48000, "format": "float"})
        == "48kHz 32bit"
    )


def test_refresh_mpv_audio_info_stores_audio_quality_separately():
    player = Player.__new__(Player)
    process = FakePopen()
    song = {"quality": "LOSSLESS"}
    player.popen_handler = process
    player.playback_token = 1
    player._request_mpv_property = lambda name, path: {
        "samplerate": 44100,
        "format": "s16",
    }

    with patch.object(
        Player, "current_song", new_callable=PropertyMock
    ) as current_song:
        current_song.return_value = song
        assert player._refresh_mpv_audio_info("sock", 1, process)
        assert player._refresh_mpv_audio_info("sock", 1, process)

    assert song["quality"] == "LOSSLESS"
    assert song["audio_quality"] == "44.1kHz 16bit"


def _player_with_queue(song_ids, *, mode=4, idx=0):
    player = Player.__new__(Player)
    player.storage = type(
        "FakeStorage",
        (),
        {
            "database": {
                "songs": {
                    str(sid): {"song_id": sid, "song_name": f"song-{sid}"}
                    for sid in song_ids
                },
                "player_info": {
                    "player_list": [str(sid) for sid in song_ids],
                    "player_list_type": "songs",
                    "player_list_title": "test",
                    "playing_order": list(range(len(song_ids))),
                    "playing_mode": mode,
                    "idx": idx,
                    "random_index": 0,
                    "playing_volume": 60,
                },
            }
        },
    )()
    player.playing_flag = True
    player.popen_handler = None
    return player


def test_advance_on_playback_failure_stops_for_single_song_queue():
    player = _player_with_queue([186016], mode=Player.MODE_RANDOM_LOOP)
    player.stop = lambda: setattr(player, "playing_flag", False)
    player.next_idx = lambda: None
    player.replay = lambda: (_ for _ in ()).throw(
        AssertionError("replay should not run")
    )

    player._advance_on_playback_failure()

    assert player.playing_flag is False


def test_advance_on_playback_failure_stops_when_loop_wraps_to_same_song():
    player = _player_with_queue(
        [186016, 33894312], mode=Player.MODE_ORDERED_LOOP, idx=0
    )

    def fake_next_idx():
        player.info["idx"] = 0

    player.stop = lambda: setattr(player, "playing_flag", False)
    player.next_idx = fake_next_idx
    player.replay = lambda: (_ for _ in ()).throw(
        AssertionError("replay should not run")
    )

    player._advance_on_playback_failure()

    assert player.playing_flag is False


def test_advance_on_playback_failure_replays_when_next_song_differs():
    player = _player_with_queue(
        [186016, 33894312], mode=Player.MODE_ORDERED_LOOP, idx=0
    )
    replayed = []

    def fake_next_idx():
        player.info["idx"] = 1

    player.stop = lambda: setattr(player, "playing_flag", False)
    player.next_idx = fake_next_idx
    player.replay = lambda: replayed.append(player.playing_id)

    player._advance_on_playback_failure()

    assert replayed == [33894312]


def test_build_playinfo_rotates_quality_label(monkeypatch):
    player = Player.__new__(Player)
    player.playinfo_starts = 100
    player.playing_flag = True
    song = {
        "song_name": "song",
        "artist": "artist",
        "album_name": "album",
        "quality": "LOSSLESS",
        "audio_quality": "44.1kHz 16bit",
    }
    calls = []
    player.ui = type(
        "FakeUi",
        (),
        {"build_playinfo": lambda self, *args, **kwargs: calls.append((args, kwargs))},
    )()

    with patch.object(
        Player, "current_song", new_callable=PropertyMock
    ) as current_song:
        current_song.return_value = song
        monkeypatch.setattr("NEMbox.player.time.time", lambda: 101)
        player.build_playinfo()
        monkeypatch.setattr("NEMbox.player.time.time", lambda: 104)
        player.build_playinfo()

    assert calls[0][0][3] == "LOSSLESS"
    assert calls[1][0][3] == "44.1kHz 16bit"
