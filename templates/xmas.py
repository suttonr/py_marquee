from .base import base


class xmas(base):
    def __init__(self, marquee, xoffset=3, yoffset=0, show_label=True, 
        fgcolor=bytearray(b'\xba\x99\x10'), bgcolor=bytearray(b'\x00\x00\x00'),
        label_color=bytearray(b'\xff\x00\x00'), tz_list=None, weather=None, clear=True):
        super().__init__(marquee, clear=clear)
        self.timer = None
        self.draw_bmp("templates/img/xmas-1.bmp")
    def __del__(self):
        if self.timer:
            print("clock timer cancel")
            self.timer.cancel()


