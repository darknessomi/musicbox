#!/usr/bin/env python
# -*- coding: utf-8 -*-
# osdlyrics.py --- desktop lyrics for musicbox
# Copyright (c) 2015-2016 omi & Contributors

import sys
import os
import logger
from multiprocessing import Process

log = logger.getLogger(__name__)

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
            self.initUI()

        def initUI(self):
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.resize(900, 150)
            self.text = u"OSD Lyrics for Musicbox"
            self.setWindowTitle("Lyrics")
            self.show()

        @QtCore.pyqtSlot(str)
        def refresh_lyrics(self, text):
            self.text = text
            self.repaint()

        def paintEvent(self, event):
            qp = QtGui.QPainter()
            qp.begin(self)
            self.drawText(event, qp)
            qp.end()

        def drawText(self, event, qp):
            qp.setPen(QtGui.QColor(128, 0, 128))
            qp.setFont(QtGui.QFont('Decorative', 16))
            qp.drawText(event.rect(), QtCore.Qt.AlignCenter, self.text)

    def show_lyrics():
        app = QtGui.QApplication(sys.argv)
        # lyrics_receiver = LyricsReceiver()
        lyrics = Lyrics()
        QtDBus.QDBusConnection.sessionBus().registerService('org.musicbox.Bus')
        QtDBus.QDBusConnection.sessionBus().registerObject('/', lyrics, QtDBus.QDBusConnection.ExportAllSlots)
        sys.exit(app.exec_())

def show_lyrics_new_process():
    if  pyqt_activity:
        p = Process(target=show_lyrics)
        p.start()
        # p.join()
