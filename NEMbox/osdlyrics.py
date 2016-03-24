#!/usr/bin/env python
# -*- coding: utf-8 -*-
# osdlyrics.py --- desktop lyrics for musicbox
# Copyright (c) 2015-2016 omi & Contributors

import sys
import os
import logger
from config import Config
from multiprocessing import Process

log = logger.getLogger(__name__)

config = Config()

try:
    from PyQt4 import QtGui, QtCore, QtDBus
    pyqt_activity = True
except ImportError:
    pyqt_activity = False
    log.warn("PyQt4 module not installed.")
    log.warn("Osdlyrics Not Available.")

if  pyqt_activity:
    class Lyrics(QtGui.QWidget):
        def __init__(self):
            super(Lyrics, self).__init__()
            self.__dbusAdaptor = LyricsAdapter(self)
            self.initUI()

        def initUI(self):
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.resize(900, 150)
            self.text = u"OSD Lyrics for Musicbox"
            self.setWindowTitle("Lyrics")
            self.show()

        def paintEvent(self, event):
            qp = QtGui.QPainter()
            qp.begin(self)
            self.drawText(event, qp)
            qp.end()

        def drawText(self, event, qp):
            osdlyrics_color = config.get_item("osdlyrics_color")
            osdlyrics_font = config.get_item("osdlyrics_font")
            qp.setPen(QtGui.QColor(osdlyrics_color[0], osdlyrics_color[1], osdlyrics_color[2]))
            qp.setFont(QtGui.QFont(osdlyrics_font[0], osdlyrics_font[1]))
            qp.drawText(event.rect(), QtCore.Qt.AlignCenter, self.text)

    class LyricsAdapter(QtDBus.QDBusAbstractAdaptor):
        QtCore.Q_CLASSINFO("D-Bus Interface", "local.musicbox.Lyrics")
        QtCore.Q_CLASSINFO("D-Bus Introspection",
        '  <interface name="local.musicbox.Lyrics">\n'
        '    <method name="refresh_lyrics">\n'
        '      <arg direction="in" type="s" name="lyric"/>\n'
        '    </method>\n'
        '  </interface>\n')

        def __init__(self, parent):
            super(LyricsAdapter, self).__init__(parent)

        @QtCore.pyqtSlot(str)
        def refresh_lyrics(self, text):
            self.parent().text = text
            self.parent().repaint()


    def show_lyrics():
        try:
            app = QtGui.QApplication(sys.argv)
            # lyrics_receiver = LyricsReceiver()
            lyrics = Lyrics()
            QtDBus.QDBusConnection.sessionBus().registerService('org.musicbox.Bus')
            QtDBus.QDBusConnection.sessionBus().registerObject('/', lyrics)
            sys.exit(app.exec_())
        except:
            return 0

def show_lyrics_new_process():
    if  pyqt_activity and config.get_item("osdlyrics"):
        p = Process(target=show_lyrics)
        p.start()