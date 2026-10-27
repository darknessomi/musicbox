import pytest

from NEMbox.api import NetEase, Parse, is_supported_music_quality


def test_parse_song_url_hides_lossless_bitrate():
    url, quality = Parse.song_url(
        {
            "id": 1,
            "url": "https://example.test/song",
            "br": 2163000,
        }
    )

    assert url == "https://example.test/song"
    assert quality == "LOSSLESS"


def test_parse_song_url_keeps_mp3_bitrate():
    assert Parse.song_url({"id": 1, "url": "u", "br": 320000}) == ("u", "HD 320k")


@pytest.mark.parametrize(
    "quality",
    [0, 1, 2, 3, 4, "0", "4", "standard", "exhigh", "lossless", "sky"],
)
def test_supported_music_quality_values(quality):
    assert is_supported_music_quality(quality) is True


@pytest.mark.parametrize("quality", ["", "vivid", "unknown", "5", -1, True, None])
def test_unsupported_music_quality_values(quality):
    assert is_supported_music_quality(quality) is False


def test_parse_songs_keeps_duration_for_mpv_progress():
    songs = Parse.songs(
        [
            {
                "id": 1,
                "name": "song",
                "ar": [{"name": "artist"}],
                "al": {"name": "album", "id": 2},
                "url": "https://example.test/song.flac",
                "br": 2163000,
                "dt": 243000,
                "expires": -1,
                "get_time": 1,
            }
        ]
    )

    assert songs[0]["duration"] == 243
    assert songs[0]["free_trial"] is False
    assert songs[0]["media_duration"] == 0


def test_dig_info_marks_free_trial_separately_from_catalog_duration():
    api = NetEase.__new__(NetEase)
    api.songs_url = lambda _ids: [
        {
            "id": 1,
            "url": "http://cdn.test/trial.mp3",
            "br": 128000,
            "type": "mp3",
            "level": "standard",
            "expi": 1200,
            "time": 45035,
            "freeTrialInfo": {"start": 0, "end": 45},
        }
    ]
    api.songs_detail = lambda _ids: [
        {
            "id": 1,
            "name": "song",
            "ar": [{"name": "artist"}],
            "al": {"name": "album", "id": 2},
            "dt": 240000,
        }
    ]

    songs = api.dig_info([{"id": 1}], "songs")
    refreshed = api.dig_info([1], "refresh_urls")

    assert songs[0]["duration"] == 240
    assert songs[0]["free_trial"] is True
    assert songs[0]["media_duration"] == 45
    assert refreshed[0]["free_trial"] is True
    assert refreshed[0]["media_duration"] == 45
    assert refreshed[0]["mp3_url"] == "http://cdn.test/trial.mp3"
