#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-07-15 15:48:27
# @Last Modified by:   omi
# @Last Modified time: 2015-01-30 18:05:08


'''
网易云音乐 Player
'''
# Let's make some noise

import subprocess
import threading
import time
import os
import signal
import random
import re
from ui import Ui


# carousel x in [left, right]
carousel = lambda left, right, x: left if (x > right) else (right if x < left else x)


class Player:
    def __init__(self):
        self.ui = Ui()
        self.datatype = 'songs'
        self.popen_handler = None
        # flag stop, prevent thread start
        self.playing_flag = False
        self.pause_flag = False
        self.songs = []
        self.idx = 0
        self.volume = 60
        self.process_length = 0
        self.process_location = 0
        self.process_first = False
        self.playing_mode = 0
    def popen_recall(self, onExit, popenArgs):
        """
        Runs the given args in a subprocess.Popen, and then calls the function
        onExit when the subprocess completes.
        onExit is a callable object, and popenArgs is a lists/tuple of args that
        would give to subprocess.Popen.
        """

        def runInThread(onExit, popenArgs):
            self.popen_handler = subprocess.Popen(['mpg123', '-R', ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            #self.popen_handler.stdin.write("SILENCE\n")
            self.popen_handler.stdin.write("V " + str(self.volume) + "\n")
            self.popen_handler.stdin.write("L " + popenArgs + "\n")
            self.process_first = True
            # self.popen_handler.wait()
            while (True):
                if self.playing_flag == False:
                    break
                try:
                    strout = self.popen_handler.stdout.readline()
                except IOError:
                    break
                if re.match("^\@F.*$", strout):
                    process_data = strout.split(" ")
                    process_location = float(process_data[4])
                    if self.process_first:
                        self.process_length = process_location
                        self.process_first = False
                        self.process_location = 0
                    else:
                        self.process_location = self.process_length - process_location
                    continue
                if strout == "@P 0\n":
                    self.popen_handler.stdin.write("Q\n")
                    self.popen_handler.kill()
                    break

            if self.playing_flag:
                if self.idx < 0 or self.idx >= len(self.songs):
                    return
                # Playing mode. 0 is ordered. 1 is orderde loop. 2 is single song loop. 3 is random.
                if self.playing_mode == 0:
                    self.idx = carousel(0, len(self.songs) - 1, self.idx + 1)
                elif self.playing_mode == 1:
                    self.idx = (self.idx + 1) % len(self.songs)
                elif self.playing_mode == 2:
                    self.idx = self.idx
                elif self.playing_mode == 3:
                    self.idx = random.randint(0, len(self.songs))
                else:
                    self.idx = carousel(0, len(self.songs) - 1, self.idx + 1)
                onExit()
            return

        thread = threading.Thread(target=runInThread, args=(onExit, popenArgs))
        thread.start()
        # returns immediately after the thread starts
        return thread

    def recall(self):
        if self.idx < 0 or self.idx >= len(self.songs):
            return
        self.playing_flag = True
        item = self.songs[self.idx]
        self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], item['quality'], time.time())
        self.popen_recall(self.recall, item['mp3_url'])

    def play(self, datatype, songs, idx):
        # if same playlists && idx --> same song :: pause/resume it
        self.datatype = datatype

        if datatype == 'songs' or datatype == 'djchannels':
            if idx == self.idx and songs == self.songs:
                if self.pause_flag:
                    self.resume()
                else:
                    self.pause()

            else:
                if datatype == 'songs' or datatype == 'djchannels':
                    self.songs = songs
                    self.idx = idx

                # if it's playing
                if self.playing_flag:
                    self.switch()

                # start new play
                else:
                    self.recall()
        # if current menu is not song, pause/resume
        else:
            if self.playing_flag:
                if self.pause_flag:
                    self.resume()
                else:
                    self.pause()
            else:
                pass

    # play another
    def switch(self):
        self.stop()
        # wait process be killed
        time.sleep(0.01)
        self.recall()

    def stop(self):
        if self.playing_flag and self.popen_handler:
            self.playing_flag = False
            self.popen_handler.stdin.write("Q\n")
            self.popen_handler.kill()

    def pause(self):
        self.pause_flag = True
        os.kill(self.popen_handler.pid, signal.SIGSTOP)
        item = self.songs[self.idx]
        self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], item['quality'], time.time(), pause=True)

    def resume(self):
        self.pause_flag = False
        os.kill(self.popen_handler.pid, signal.SIGCONT)
        item = self.songs[self.idx]
        self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], item['quality'], time.time())

    def next(self):
        self.stop()
        time.sleep(0.01)
        self.idx = carousel(0, len(self.songs) - 1, self.idx + 1)
        self.recall()

    def prev(self):
        self.stop()
        time.sleep(0.01)
        self.idx = carousel(0, len(self.songs) - 1, self.idx - 1)
        self.recall()

    def shuffle(self):
        self.stop()
        time.sleep(0.01)
        num = random.randint(0, 12)
        self.idx = carousel(0, len(self.songs) - 1, self.idx + num)
        self.recall()

    def volume_up(self):
        self.volume = self.volume + 7
        if (self.volume > 100):
            self.volume = 100
        self.popen_handler.stdin.write("V " + str(self.volume) + "\n")

    def volume_down(self):
        self.volume = self.volume - 7
        if (self.volume < 0):
            self.volume = 0
        self.popen_handler.stdin.write("V " + str(self.volume) + "\n")

    def update_size(self):
        try:
            self.ui.update_size()
            item = self.songs[self.idx]
            if self.playing_flag:
                self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], item['quality'], time.time())
            if self.pause_flag:
                self.ui.build_playinfo(item['song_name'], item['artist'], item['album_name'], item['quality'], time.time(), pause=True)
        except IndexError:
            pass
