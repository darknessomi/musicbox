#!/usr/bin/env python
# -*- coding: utf-8 -*-
# osdlyrics.py --- desktop lyrics for musicbox
# Copyright (c) 2015-2016 omi & Contributors
import sys
from multiprocessing import Process
from multiprocessing import set_start_method

from . import logger
from .config import Config

log = logger.getLogger(__name__)

config = Config()

try:
    from qtpy import QtGui, QtCore, QtWidgets
    import dbus
    import dbus.service
    import dbus.mainloop.glib

    pyqt_activity = True
except ImportError:
    pyqt_activity = False
    log.warn("qtpy module not installed.")
    log.warn("Osdlyrics Not Available.")

if pyqt_activity:
    QWidget = QtWidgets.QWidget
    QApplication = QtWidgets.QApplication

    class Lyrics(QWidget):
        def __init__(self):
            super(Lyrics, self).__init__()
            self.text = ""
            self.initUI()

        def initUI(self):
            self.setStyleSheet("background:" + config.get("osdlyrics_background"))
            if config.get("osdlyrics_transparent"):
                self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
            self.setAttribute(QtCore.Qt.WA_X11DoNotAcceptFocus)
            self.setFocusPolicy(QtCore.Qt.NoFocus)
            if config.get("osdlyrics_on_top"):
                self.setWindowFlags(
                    QtCore.Qt.FramelessWindowHint
                    | QtCore.Qt.WindowStaysOnTopHint
                    | QtCore.Qt.X11BypassWindowManagerHint
                )
            else:
                self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
            self.setMinimumSize(600, 50)
            osdlyrics_size = config.get("osdlyrics_size")
            self.resize(osdlyrics_size[0], osdlyrics_size[1])
            scn = QApplication.desktop().screenNumber(
                QApplication.desktop().cursor().pos()
            )
            bl = QApplication.desktop().screenGeometry(scn).bottomLeft()
            br = QApplication.desktop().screenGeometry(scn).bottomRight()
            bc = (bl + br) / 2
            frameGeo = self.frameGeometry()
            frameGeo.moveCenter(bc)
            frameGeo.moveBottom(bc.y())
            self.move(frameGeo.topLeft())
            self.text = "OSD Lyrics for Musicbox"
            self.setWindowTitle("Lyrics")
            self.show()

        def mousePressEvent(self, event):
            self.mpos = event.pos()

        def mouseMoveEvent(self, event):
            if event.buttons() and QtCore.Qt.LeftButton:
                diff = event.pos() - self.mpos
                newpos = self.pos() + diff
                self.move(newpos)

        def wheelEvent(self, event):
            self.resize(self.width() + event.delta(), self.height())

        def paintEvent(self, event):
            qp = QtGui.QPainter()
            qp.begin(self)
            self.drawText(event, qp)
            qp.end()

        def drawText(self, event, qp):
            osdlyrics_color = config.get("osdlyrics_color")
            osdlyrics_font = config.get("osdlyrics_font")
            font = QtGui.QFont(osdlyrics_font[0], osdlyrics_font[1])
            pen = QtGui.QColor(
                osdlyrics_color[0], osdlyrics_color[1], osdlyrics_color[2]
            )
            qp.setFont(font)
            qp.setPen(pen)
            qp.drawText(
                event.rect(), QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, self.text
            )

        def setText(self, text):
            self.text = text
            self.repaint()

    class LyricsAdapter(dbus.service.Object):
        def __init__(self, name, session):
            dbus.service.Object.__init__(self, name, session)
            self.widget = Lyrics()

        @dbus.service.method(
            "local.musicbox.Lyrics", in_signature="s", out_signature=""
        )
        def refresh_lyrics(self, text):
            self.widget.setText(text.replace("||", "\n"))

        @dbus.service.method("local.musicbox.Lyrics", in_signature="", out_signature="")
        def exit(self):
            QApplication.quit()

    def show_lyrics():
        app = QApplication(sys.argv)
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        session_bus = dbus.SessionBus()
        name = dbus.service.BusName("org.musicbox.Bus", session_bus)
        lyrics = LyricsAdapter(session_bus, "/")
        app.exec_()


def stop_lyrics_process():
    if pyqt_activity:
        bus = dbus.SessionBus().get_object("org.musicbox.Bus", "/")
        bus.exit(dbus_interface="local.musicbox.Lyrics")


def show_lyrics_new_process():
    if pyqt_activity and config.get("osdlyrics"):
        set_start_method("spawn")
        p = Process(target=show_lyrics)
        p.daemon = True
        p.start()
