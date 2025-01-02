import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .base import box
from .tick import tick


class timer(tick):
    def __init__(self, marquee, xoffset=3, yoffset=0, show_label=True, 
        fgcolor=bytearray(b'\xba\x99\x10'), bgcolor=bytearray(b'\x00\x00\x00'),
        label_color=bytearray(b'\xff\x00\x00'), interval=15, clear=True, tz="UTC", 
        fmt="{day:02}d {hour:02}h {min:02}m {sec:02}s",timer_end=None):
        print("timer init")
        self.show_label = show_label
        self.clock_xoffset = xoffset
        self.clock_yoffset = yoffset
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor
        self.label_color = label_color
        self.tz = tz
        self.fmt = fmt
        self.timer_end = timer_end
        super().__init__(marquee, interval=interval, clear=clear)
    
    def set_timer_end(self, timer_end):
        self.timer_end = timer_end
        print("timer set", self.timer_end)

    def set_timer_duration(self, duration):
        print("timer set duration", duration)
        t = datetime.strptime(duration,"%H:%M")
        self.timer_end = datetime.now(ZoneInfo("UTC")) + timedelta(hours=t.hour, minutes=t.minute)
        print("timer set", self.timer_end)
        

    def clock_tick(self):
        x = self.clock_xoffset
        t_now = datetime.now(ZoneInfo(self.tz))
        if isinstance(self.timer_end, datetime):
            if t_now < self.timer_end:
                t_delta = self.timer_end - t_now
                neg = True
            else:
                t_delta = t_now - self.timer_end
                neg = False
            sec = t_delta.seconds
            sec = abs(sec)
            days = int(sec / 86400)
            sec -= int(sec / 86400) * 86400
            hours = int(sec/3600)
            sec -= int(sec / 3600) * 3600
            minutes = int(sec / 60)
            sec -= int(sec / 60) * 60
            t = self.fmt.format(day=days, hour=hours, min=minutes, sec=sec )
            print("tick:",t, neg)

            for c in t:
                if c.isdigit():
                    self.draw_7seg_digit(c, x, y_offset=self.clock_yoffset, fgcolor=self.fgcolor, bgcolor=self.bgcolor)
                else:
                    self.update_message(c, (x, 10), fgcolor=self.label_color, bgcolor=self.bgcolor)
                    x -= 3
                x += 9
            x += 10
        super().clock_tick()
