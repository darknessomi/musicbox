from NEMbox import ui
from NEMbox.ui import Ui


class FakeScreen:
    def __init__(self):
        self.writes = []

    def getmaxyx(self):
        return (40, 120)

    def move(self, *_args):
        pass

    def clrtobot(self):
        pass

    def refresh(self):
        pass

    def addstr(self, *args):
        text = next((arg for arg in args if isinstance(arg, str | bytes)), "")
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        self.writes.append(str(text))


def test_build_login_qr_does_not_render_url(monkeypatch):
    monkeypatch.setattr(ui.curses, "noecho", lambda: None)
    monkeypatch.setattr(ui.curses, "curs_set", lambda _visibility: None)
    monkeypatch.setattr(ui.curses, "color_pair", lambda _pair: 0)

    screen = FakeScreen()
    view = object.__new__(Ui)
    view.screen = screen
    view.startcol = 1

    url = "https://music.163.com/login?codekey=test-unikey"
    view.build_login_qr(url)

    rendered = "\n".join(screen.writes)
    assert "链接:" not in rendered
    assert "https://music.163.com/login" not in rendered
    assert "codekey=test-unikey" not in rendered
    assert "请使用网易云音乐 App 扫描二维码登录" in rendered
