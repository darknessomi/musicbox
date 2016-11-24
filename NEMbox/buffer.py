# -*- coding: utf-8 -*-
# @Author: Catofes
# @Date:   2015-08-15
'''
Class to cache songs into local storage.
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library

standard_library.install_aliases()

import threading
import os
import queue
import urllib.request
import argparse


class Buffer:
    def __init__(self):
        self.tmp_file = "/tmp/music_box.mp3"
        self.tmp_pipe = "/tmp/music_box.pipe"
        self.buffer_size = 128 * 1024
        self.queue = queue.Queue()
        self.music = None

    def buffer(self, url):
        def download():
            request = urllib.request.urlopen(url)
            with open(self.tmp_file, "wb") as f:
                try:
                    while True:
                        data = request.read(self.buffer_size)
                        if not data:
                            break
                        self.queue.put(data)
                        f.write(data)
                except:
                    pass

        def cache():
            try:
                os.unlink(self.tmp_pipe)
                os.unlink(self.tmp_file)
            except:
                pass
            os.mkfifo(self.tmp_pipe)
            pipe_file = open(self.tmp_pipe, "wb")
            while True:
                data = self.queue.get()
                pipe_file.write(data)

        download_thread = threading.Thread(target=download)
        download_thread.start()
        cache()
        download_thread.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url")
    args = parser.parse_args()
    Buffer().buffer(args.url)
