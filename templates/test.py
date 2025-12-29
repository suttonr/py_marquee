import threading
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from .base import base, box


class test(base):
    def __init__(self, marquee, xoffset=3, yoffset=0, show_label=True, 
        fgcolor=bytearray(b'\xba\x99\x10'), bgcolor=bytearray(b'\x00\x00\x00'),
        label_color=bytearray(b'\xff\x00\x00'), clear=True):
        super().__init__(marquee, clear=clear)
       
        self.show_label = show_label
        self.clock_xoffset = xoffset
        self.clock_yoffset = yoffset
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor
        self.label_color = label_color
        self.offset = 0
        self.timer = None

        self.clock_tick()

    def __del__(self):
        if self.timer:
            print("clock timer cancel")
            self.timer.cancel()

    def clock_tick(self):
        for x in range(self.marquee.panel_width):
            for y in range( self.marquee.panel_height * 17):
                color = self.fgcolor if x == self.offset else self.bgcolor
                self.marquee.set_pixel( (x).to_bytes(2,"big") + (y).to_bytes(1,"big") + color )
        
        if (self.offset > self.marquee.panel_width):
            self.offset = 0
                           
        self.marquee.send()
        self.timer = threading.Timer(1, self.clock_tick)
        self.timer.start()
