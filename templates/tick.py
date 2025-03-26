import threading

from .base import base

class tick(base):
    def __init__(self, marquee, interval=15, clear=False):
        super().__init__(marquee, clear=clear)
        self.interval = interval
        self.timer = None
        self.clock_tick()

    def __del__(self):
        if self.timer:
            print("tick timer cancel")
            self.timer.cancel()

    def clock_tick(self):
        self.timer = threading.Timer(self.interval, self.clock_tick)
        self.timer.start()
