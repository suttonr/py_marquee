from .fonts.font import font_5x8
#from ..marquee.marquee import marquee
from PIL import ImageFont

class base:
    marquee = None

    def process_raw(self, message):
        if ( (len(message) % 6) == 0 ):
            for m in range(0,len(message),6):
                self.marquee.set_pixel(message[m:m+6])
        else:
            print("Message error:", message)
        print("Raw message processed")

    def update_message(self, message, anchor=(0,0)):
        for x,y,b in font_5x8(message, fgcolor=FGCOLOR):
            self.marquee.set_pixel( (x+anchor[0]).to_bytes(2,"big") + (y+anchor[1]).to_bytes(1,"big") + b  )
    
    def update_message_2(self, message, fgcolor=bytearray(b'\x00\x00\x00'), bgcolor=None, font_size=16, anchor=(0,0)):
        font = ImageFont.truetype("templates/fonts/BitPotion.ttf",font_size)
        message_bit = font.getmask(message)
        i=0
        if bgcolor == None:
            bgcolor = marquee.bgcolor
        for y in range(message_bit.size[1]):
            print(f"\n{y}: ",end="")
            for x in range(message_bit.size[0]):
                bit_color = fgcolor if message_bit[i] else bgcolor
                self.marquee.set_pixel( (x+anchor[0]).to_bytes(2,"big") + (y+anchor[1]).to_bytes(1,"big") + bit_color )
                i += 1

    def draw_box(self, cord, h, w, color):
        for x in range(cord[0], cord[0] + w):
            for y in range(cord[1], cord[1] + h):
                self.marquee.set_pixel( x.to_bytes(2,"big") +  y.to_bytes(1,"big") + color )
