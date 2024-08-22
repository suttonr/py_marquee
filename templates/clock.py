import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from .base import base, box

class clock(base):
    def __init__(self, marquee):
        super().__init__(marquee)
        self.timezones = [
            "Asia/Kolkata",
            "UTC",
            "America/New_York",
            "America/Chicago",
            "America/Los_Angeles",
        ]
        self.label = " KOLKATA     UTC      BOSTON     AUSTIN     SEATTLE   "
        self.clock_xoffset = 0
        self.clock_yoffset = 0
        self.fgcolor = bytearray(b'\xba\x99\x10')
        self.label_color = bytearray(b'\xff\x00\x00')
        self.timer = None

        self.update_message_2(self.label, self.label_color, anchor=(1,15))
        self.clock_tick()

    def __del__(self):
        if self.timer:
            self.timer.cancel()


    def clock_tick(self):
        x = self.clock_xoffset
        for tz in self.timezones:
            t = datetime.now(ZoneInfo(tz)).strftime("%H %M")

            for c in t:
                if c.isdigit():
                    self.draw_7seg_digit(c, x)
                else:
                    self.draw_box((x+2, self.clock_yoffset+2), 3, 2, self.fgcolor)
                    self.draw_box((x+2, self.clock_yoffset+10), 3, 2, self.fgcolor)
                    x -= 3
                x += 9
            x += 10
        self.timer = threading.Timer(15, self.clock_tick)
        self.timer.start()
