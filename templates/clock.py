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

        t = datetime.now(ZoneInfo("America/New_York")).strftime("%H %M")
        
        x = 0
        for c in t:
            if c.isdigit():
                self.draw_7seg_digit(c, x)
            x += 10
