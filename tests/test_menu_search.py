import signal

from NEMbox.menu import Menu, _item_search_text, _prepare_search_items


def test_prepare_search_items_handles_string_entries():
    datalist = ["UK排行榜周榜", "韩国Melon排行榜周榜"]
    items = _prepare_search_items(datalist)

    assert len(items) == 2
    assert items[0]["_search_label"] == "UK排行榜周榜"
    assert items[0]["origin_index"] == 0
    assert items[1]["origin_index"] == 1


def test_prepare_search_items_sets_origin_index_on_dict_entries():
    song = {"song_id": 1, "song_name": "挪威的森林", "artist": "伍佰"}
    items = _prepare_search_items([song])

    assert items[0] is song
    assert song["origin_index"] == 0


def test_item_search_text_includes_song_fields():
    song = {"song_name": "挪威的森林", "artist": "伍佰", "album_name": "爱情万岁"}
    text = _item_search_text(song)

    assert "挪威的森林" in text
    assert "伍佰" in text
    assert "爱情万岁" in text


def test_item_search_text_falls_back_to_string():
    assert _item_search_text("华语榜") == "华语榜"


def test_resize_signal_only_sets_a_flag():
    menu = Menu.__new__(Menu)
    menu._winch_pending = False
    touched: list[str] = []

    class Screen:
        def clear(self):
            touched.append("clear")

        def refresh(self):
            touched.append("refresh")

    class Ui:
        def __init__(self):
            self.screen = Screen()

    menu.ui = Ui()

    menu.change_term(signal.SIGWINCH, None)

    assert menu._winch_pending is True
    assert touched == []


def test_restore_terminal_runs_on_the_main_loop(monkeypatch):
    menu = Menu.__new__(Menu)
    menu._winch_pending = True
    calls: list[object] = []

    class Screen:
        def keypad(self, enabled):
            calls.append(("keypad", enabled))

        def refresh(self):
            calls.append("refresh")

    class Ui:
        def update_size(self):
            calls.append("update_size")

    menu.screen = Screen()
    menu.ui = Ui()
    monkeypatch.setattr("NEMbox.menu.C.endwin", lambda: calls.append("endwin"))

    menu._restore_terminal_after_signal()
    menu._restore_terminal_after_signal()

    assert calls == ["endwin", ("keypad", True), "refresh", "update_size"]
    assert menu._winch_pending is False
