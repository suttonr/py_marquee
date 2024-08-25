from .fonts.font import font_5x8
#from ..marquee.marquee import marquee
from PIL import ImageFont
from PIL import Image

class box:
    def __init__(self, cord=(0,0), value="", h=8, w=8, fgcolor=bytearray(b'\xff\xff\xff'), bgcolor=bytearray(b'\x00\x20\x00')):
        self.x = cord[0]
        self.y = cord[1]
        self.h = h
        self.w = w
        self.value = value
        self.bgcolor = bgcolor
        self.fgcolor = fgcolor
    
    def set_values(self, cord=(0,0), value="", fgcolor=None, bgcolor=None):
        self.x = cord[0]
        self.y = cord[1]
        self.value = value
        self.bgcolor = bgcolor if bgcolor else self.bgcolor
        self.fgcolor = fgcolor if fgcolor else self.fgcolor

    def __eq__(self, other):
        return ( 
            self.value == other.value and 
            self.fgcolor == other.fgcolor and 
            self.bgcolor == other.bgcolor 
        )

    def get_cord(self, xoffset=0, yoffset=0):
        return (self.x + xoffset, self.y + yoffset) 

class base:
    marquee = None
    
    def __init__(self, marquee, brightness=1):
        self.marquee = marquee
        self.marquee.set_brightness(brightness)
        self.marquee.clear()

    def process_raw(self, message):
        if ( (len(message) % 6) == 0 ):
            for m in range(0,len(message),6):
                self.marquee.set_pixel(message[m:m+6])
        else:
            print("Message error:", message)

    def update_message(self, message, anchor=(0,0), fgcolor=bytearray(b'\x00\x00\x00'), bgcolor=None):
        for x,y,b in font_5x8(message, fgcolor=fgcolor):
            self.marquee.set_pixel( (x+anchor[0]).to_bytes(2,"big") + (y+anchor[1]).to_bytes(1,"big") + b  )
    
    def update_message_2(self, message, fgcolor=bytearray(b'\x00\x00\x00'), bgcolor=None, font_size=16, anchor=(0,0)):
        font = ImageFont.truetype("templates/fonts/BitPotion.ttf",font_size)
        message_bit = font.getmask(message)
        i=0
        if bgcolor == None:
            bgcolor = self.marquee.bgcolor

        for y in range(message_bit.size[1]):
            for x in range(message_bit.size[0]):
                bit_color = fgcolor if message_bit[i] else bgcolor
                self.marquee.set_pixel( (x+anchor[0]).to_bytes(2,"big") + (y+anchor[1]).to_bytes(1,"big") + bit_color )
                i += 1

    def draw_box(self, cord, h, w, color):
        for x in range(cord[0], cord[0] + w):
            for y in range(cord[1], cord[1] + h):
                self.marquee.set_pixel( x.to_bytes(2,"big") +  y.to_bytes(1,"big") + color )

    def draw_bmp(self, file_name="", x_offset=0, y_offset=0, x_start=0, y_start=0, x_end=0, y_end=0):
        im = Image.open(file_name)
        range_x_end = x_end if x_end else im.size[0]
        range_y_end = y_end if y_end else im.size[1]

        for y in range(y_start, range_y_end):
            for x in range(x_start, range_x_end):
                if sum(im.getpixel((x,y))) > 0:
                    data = bytearray()
                    data += (x+x_offset).to_bytes(2,"big") + (y+y_offset).to_bytes(1,"big") 
                    data += bytearray(list(im.getpixel((x,y))))
                    self.process_raw(data)
    
    def draw_7seg_digit(self, number, x_offset=0, y_offset=0, 
            fgcolor=bytearray(b'\xba\x99\x10'), bgcolor=bytearray(b'\x00\x00\x00')):
        seven_seg = {
            "a" : { "cord" : (x_offset, y_offset), "h" : 1, "w" : 5 },
            "b" : { "cord" : (5+x_offset, y_offset), "h" : 6, "w" : 1 },
            "c" : { "cord" : (5+x_offset, 6+y_offset), "h" : 7, "w" : 1 },
            "d" : { "cord" : (x_offset, 12+y_offset), "h" : 1, "w" : 5 },
            "e" : { "cord" : (x_offset, 6+y_offset), "h" : 7, "w" : 1 },
            "f" : { "cord" : (x_offset, y_offset), "h" : 6, "w" : 1 },
            "g" : { "cord" : (x_offset, 6+y_offset), "h" : 1, "w" : 5 },
        }
        digit = {
            "1" : ["b", "c"],
            "2" : ["a", "b", "g", "e", "d"],
            "3" : ["a", "b", "c", "d", "g"],
            "4" : ["b", "c", "f", "g"],
            "5" : ["a", "c", "d", "f", "g"],
            "6" : ["a", "c", "d", "e", "f", "g"],
            "7" : ["a", "b", "c"],
            "8" : ["a", "b", "c", "d", "e", "f", "g"],
            "9" : ["a", "b", "c", "d", "f", "g"],
            "0" : ["a", "b", "c", "d", "e", "f"],
        }
        for seg,params in seven_seg.items():
            c = bgcolor
            if seg in digit[str(number)[0]]:
                c = fgcolor
            self.draw_box(**seven_seg[seg], color=c)

