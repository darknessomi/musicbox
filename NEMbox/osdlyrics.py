from PyQt4 import QtGui, QtCore, QtDBus
import sys
import os
from multiprocessing import Process

class Lyrics(QtGui.QWidget):
    def __init__(self):
        super(Lyrics, self).__init__()
        self.initUI()

    def initUI(self):
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
        qp.setPen(QtGui.QColor(0, 0, 0))
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
    p = Process(target=show_lyrics)
    p.start()
    os.system("notify-send 123")
    # p.join()
