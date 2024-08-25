import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from .base import base, box

tz_label_map = {
    "Asia/Kolkata" : "Kolkata",
    "America/New_York" : "Boston",
    "America/Chicago" : "Austin",
    "America/Los_Angeles" : "Seattle",
}

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
        #self.label = " KOLKATA     UTC      BOSTON     AUSTIN     SEATTLE   "
        self.show_label = True
        self.clock_xoffset = 3
        self.clock_yoffset = 0
        self.fgcolor = bytearray(b'\xba\x99\x10')
        self.label_color = bytearray(b'\xff\x00\x00')
        self.timer = None

        #self.update_message_2(self.label, self.label_color, anchor=(1+self.clock_xoffset,15))
        self.clock_tick()

    def __del__(self):
        print(f"destructor {self.timer}")
        if self.timer:
            print("timer cancel")
            self.timer.cancel()


    def clock_tick(self):
        x = self.clock_xoffset
        for tz in self.timezones:
            t = datetime.now(ZoneInfo(tz)).strftime("%H %M")
            label = tz_label_map.get(tz, tz)
            label_offset = int((42-(len(label)*6))/2)
            label_offset = label_offset if label_offset > 0 else 0
            self.update_message(label.upper(), (x+label_offset, 15), fgcolor=self.label_color)
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
