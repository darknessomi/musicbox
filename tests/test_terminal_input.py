from NEMbox.ui import _is_backspace_key, _is_enter_key
from NEMbox.utils import decode_terminal_input


def test_is_backspace_key_accepts_del_string():
    assert _is_backspace_key("\x7f")


def test_is_backspace_key_accepts_int_del():
    assert _is_backspace_key(127)


def test_is_backspace_key_rejects_printable():
    assert not _is_backspace_key("a")


def test_is_enter_key_accepts_newline_string():
    assert _is_enter_key("\n")


def test_decode_terminal_input_empty():
    assert decode_terminal_input(b"") == ""


def test_decode_terminal_input_valid_utf8():
    assert decode_terminal_input("你好".encode()) == "你好"


def test_decode_terminal_input_ignores_broken_utf8_after_backspace():
    # Simulates deleting the first byte of a 3-byte Chinese character.
    broken = b"ab" + b"\xbd\xa0"
    assert decode_terminal_input(broken) == "ab"


def test_decode_terminal_input_strips_whitespace():
    assert decode_terminal_input(b"  test  ") == "test"
