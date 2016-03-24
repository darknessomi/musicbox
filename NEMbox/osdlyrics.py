#!/usr/bin/env python
# -*- coding: utf-8 -*-
# osdlyrics.py --- desktop lyrics for musicbox
# Copyright (c) 2015-2016 omi & Contributors

from PyQt4 import QtGui, QtCore, QtDBus
import sys
import os
from multiprocessing import Process

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
        qp.setPen(QtGui.QColor(128, 0, 128))
        qp.setFont(QtGui.QFont('Decorative', 16))
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
    app = QtGui.QApplication(sys.argv)
    # lyrics_receiver = LyricsReceiver()
    lyrics = Lyrics()
    QtDBus.QDBusConnection.sessionBus().registerService('org.musicbox.Bus')
    QtDBus.QDBusConnection.sessionBus().registerObject('/', lyrics)
    sys.exit(app.exec_())

def show_lyrics_new_process():
    p = Process(target=show_lyrics)
    p.start()
    # p.join()
