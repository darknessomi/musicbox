from NEMbox.api import Parse


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
