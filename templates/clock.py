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
        self.clock_xoffset = 0
        self.clock_yoffset = 0

        self.clock_tick()


    def clock_tick(self):
        x = self.clock_offset
        for tz in self.timezones:
            t = datetime.now(ZoneInfo(tz)).strftime("%H %M")

            for c in t:
                if c.isdigit():
                    self.draw_7seg_digit(c, x)
                else:
                    self.draw_box((x+4, self.clock_yoffset+3), 3, 2)
                    self.draw_box((x+9, self.clock_yoffset+3), 3, 2)
                x += 10
            x += 10
        threading.Timer(15, self.clock_tick).start()
