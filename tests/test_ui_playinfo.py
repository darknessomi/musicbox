from NEMbox.scrollstring import truelen
from NEMbox.ui import playinfo_song_start


def test_playinfo_song_start_accounts_for_long_quality_label():
    prefix = "♫  ♪ ♫  ♪ "
    quality = "LOSSLESS"

    start = playinfo_song_start(0, prefix, quality)

    assert start == truelen(prefix + quality) + 2
    assert start > 18
