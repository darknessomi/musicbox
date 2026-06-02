from unittest.mock import MagicMock, patch

from NEMbox import osdlyrics


def test_stop_lyrics_process_skips_when_osdlyrics_disabled():
    with patch.object(osdlyrics.config, "get", return_value=False):
        osdlyrics.stop_lyrics_process()


def test_stop_lyrics_process_survives_dbus_failure():
    mock_dbus = MagicMock()
    mock_dbus.SessionBus.side_effect = RuntimeError("dbus no enough memory")

    with (
        patch.object(osdlyrics, "pyqt_activity", True),
        patch.object(osdlyrics.config, "get", return_value=True),
        patch.object(osdlyrics, "dbus", mock_dbus),
        patch.object(osdlyrics, "_lyrics_process", None),
    ):
        osdlyrics.stop_lyrics_process()
