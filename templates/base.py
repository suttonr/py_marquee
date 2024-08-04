from .fonts.font import font_5x8
#from ..marquee.marquee import marquee
from PIL import ImageFont
from PIL import Image

class base:
    marquee = None
    
    def __init__(self, marquee):
        self.marquee = marquee

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
            bgcolor = marquee.bgcolor
        print(f"size {message_bit.size[1]} {message_bit.size[0]}")
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
