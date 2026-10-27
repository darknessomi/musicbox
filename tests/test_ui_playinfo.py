from NEMbox.scrollstring import truelen
from NEMbox.ui import (
    HELP_FOOTER_LINES,
    HELP_ITEM_FIRST_ROW,
    help_footer_row,
    help_item_row,
    playinfo_song_start,
)


def test_playinfo_song_start_accounts_for_long_quality_label():
    prefix = "♫  ♪ ♫  ♪ "
    quality = "LOSSLESS"

    start = playinfo_song_start(0, prefix, quality)

    assert start == truelen(prefix + quality) + 2
    assert start > 18


def test_help_footer_stays_below_auto_page_items():
    # page_length=0 时 menu 用这个步长。旧页脚写死在 20–22 行，终端一高就会盖住中间条目。
    for screen_rows in (24, 30, 40, 50, 80):
        step = max(int(screen_rows * 4 / 5) - 10, 1)
        last_item_row = help_item_row(step - 1, 0)
        footer = help_footer_row(screen_rows)
        assert last_item_row == HELP_ITEM_FIRST_ROW + step - 1
        assert last_item_row < footer
        assert footer + len(HELP_FOOTER_LINES) <= screen_rows


def test_help_footer_is_not_pinned_to_row_20_on_a_tall_terminal():
    assert help_footer_row(40) == 37
    assert help_footer_row(40) != 20
