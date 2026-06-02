from NEMbox.menu import _item_search_text, _prepare_search_items


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
