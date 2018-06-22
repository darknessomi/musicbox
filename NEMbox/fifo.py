import time
import select
import os
from multiprocessing import Queue, Process

from .config import Config

class FIFO(object):
    def __init__(self, path):
        self.path = path
        self.queue = Queue()
        self.process = Process(target=self.monitor)
        self.enable = Config().get('fifo_control')
        self.interval = Config().get('fifo_interval')

    def monitor(self):
        with open(self.path) as fifo:
            while True:
                select.select([fifo], [], [fifo])
                data = fifo.read()
                if len(data) == 0:
                    time.sleep(self.interval)
                    continue
                self.queue.put(data.strip())

    def start(self):
        if self.enable:
            if os.path.exists(self.path):
                os.unlink(self.path)
            os.mkfifo(self.path)
            self.process.daemon = True
            self.process.start()
        else:
            pass

    def retrieve(self):
        if self.queue.empty():
            return ""
        else:
            return self.queue.get()
