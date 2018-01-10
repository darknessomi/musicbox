#!/usr/bin/env python
# -*- coding: utf-8 -*-
# osdlyrics.py --- desktop lyrics for musicbox
# Copyright (c) 2015-2016 omi & Contributors

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import super
from future import standard_library
standard_library.install_aliases()
import sys
from multiprocessing import Process

from . import logger
from .config import Config

log = logger.getLogger(__name__)

config = Config()

try:
    from PyQt4 import QtGui, QtCore, QtDBus
    QWidget = QtGui.QWidget
    QApplication = QtGui.QApplication
    def delta(e):
        return e.delta()
    pyqt_activity = True
except ImportError:
    try:
        from PyQt5 import QtGui, QtCore, QtDBus, QtWidgets
        QWidget = QtWidgets.QWidget
        QApplication = QtWidgets.QApplication
        def delta(e):
            return e.angleDelta().y()
        pyqt_activity = True
    except ImportError:
        pyqt_activity = False
        log.warn("Either PyQt4 nor PyQt5 module installed.")
        log.warn("Osdlyrics Not Available.")

if pyqt_activity:

    class Lyrics(QWidget):

        def __init__(self):
            super(Lyrics, self).__init__()
            self.__dbusAdaptor = LyricsAdapter(self)
            self.initUI()

        def initUI(self):
            self.setStyleSheet("background:" + config.get_item(
                "osdlyrics_background"))
            if config.get_item("osdlyrics_transparent"):
                self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
            self.setAttribute(QtCore.Qt.WA_X11DoNotAcceptFocus)
            self.setFocusPolicy(QtCore.Qt.NoFocus)
            if config.get_item("osdlyrics_on_top"):
                self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                                    QtCore.Qt.WindowStaysOnTopHint |
                                    QtCore.Qt.X11BypassWindowManagerHint)
            else:
                self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
            self.setMinimumSize(600, 50)
            osdlyrics_size = config.get_item("osdlyrics_size")
            self.resize(osdlyrics_size[0], osdlyrics_size[1])
            scn = QApplication.desktop().screenNumber(
                QApplication.desktop().cursor().pos())
            bl = QApplication.desktop().screenGeometry(scn).bottomLeft()
            br = QApplication.desktop().screenGeometry(scn).bottomRight()
            bc = (bl+br)/2
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
            if (event.buttons() and QtCore.Qt.LeftButton):
                diff = event.pos() - self.mpos
                newpos = self.pos() + diff
                self.move(newpos)

        def wheelEvent(self, event):
            self.resize(self.width() + delta(event), self.height())

        def paintEvent(self, event):
            qp = QtGui.QPainter()
            qp.begin(self)
            self.drawText(event, qp)
            qp.end()

        def drawText(self, event, qp):
            osdlyrics_color = config.get_item("osdlyrics_color")
            osdlyrics_font = config.get_item("osdlyrics_font")
            font = QtGui.QFont(osdlyrics_font[0], osdlyrics_font[1])
            pen = QtGui.QColor(osdlyrics_color[0], osdlyrics_color[1],
                               osdlyrics_color[2])
            qp.setFont(font)
            qp.setPen(pen)
            qp.drawText(event.rect(), QtCore.Qt.AlignCenter |
                        QtCore.Qt.TextWordWrap, self.text)

    class LyricsAdapter(QtDBus.QDBusAbstractAdaptor):
        QtCore.Q_CLASSINFO("D-Bus Interface", "local.musicbox.Lyrics")
        QtCore.Q_CLASSINFO(
            "D-Bus Introspection",
            '  <interface name="local.musicbox.Lyrics">\n'
            '    <method name="refresh_lyrics">\n'
            '      <arg direction="in" type="s" name="lyric"/>\n'
            '    </method>\n'
            '  </interface>\n')

        def __init__(self, parent):
            super(LyricsAdapter, self).__init__(parent)

        @QtCore.pyqtSlot(str)
        def refresh_lyrics(self, text):
            self.parent().text = text.replace('||', '\n')
            self.parent().repaint()

    def show_lyrics():

        app = QApplication(sys.argv)
        lyrics = Lyrics()
        QtDBus.QDBusConnection.sessionBus().registerService('org.musicbox.Bus')
        QtDBus.QDBusConnection.sessionBus().registerObject('/', lyrics)
        sys.exit(app.exec_())


def show_lyrics_new_process():
    if pyqt_activity and config.get_item("osdlyrics"):
        p = Process(target=show_lyrics)
        p.daemon = True
        p.start()
