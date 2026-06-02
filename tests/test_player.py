from unittest.mock import PropertyMock, patch

from NEMbox.player import Player


def test_playing_id_is_none_without_current_song():
    with patch.object(Player, "current_song", new_callable=PropertyMock, return_value={}):
        player = Player.__new__(Player)
        assert player.playing_id is None
