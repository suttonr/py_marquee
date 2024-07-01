from  neomatrix.matrix import matrix
from  neomatrix.font import *
try:
    from machine import Pin
    from neopixel import NeoPixel
except:
    pass
import time
from PIL import ImageDraw
from PIL import ImageFont
from PIL import Image


MAX_PIXELS=512
PIXEL_TIME = 0.1

def test_spi():
    hspi = SPI(1, 10_000_000, sck=Pin(14), mosi=Pin(13), miso=Pin(12))
    cs = Pin(11, mode=Pin.OUT, value=1)  
    cs(0)
    hspi.write(b"\x00\x20\xff\x00\x00") 
    hspi.write(b"\x00\x21\xff\x00\x00") 
    hspi.write(b"\x00\x22\xff\x00\x00") 
    hspi.write(b"\x01\x23\xff\x00\x00") 
    hspi.write(b"\x01\x23\xff\x00\x00") 
    hspi.write(b"\x01\x23\xff\x00\x00") 
    hspi.write(b"\x02\x20\x00\xff\x00") 
    hspi.write(b"\x02\x21\x00\xff\x00") 
    hspi.write(b"\x02\x22\x00\xff\x00") 
    hspi.write(b"\x03\x23\x00\xff\x00") 
    hspi.write(b"\x03\x23\x00\xff\x00") 
    hspi.write(b"\x03\x23\x00\xff\x00") 
    hspi.write(b"\x04\x20\x00\x00\xff") 
    hspi.write(b"\x04\x21\x00\x00\xff") 
    hspi.write(b"\x04\x22\x00\x00\xff") 
    hspi.write(b"\x05\x23\x00\x00\xff") 
    hspi.write(b"\x05\x23\x00\x00\xff") 
    hspi.write(b"\x05\x23\x00\x00\xff") 
    cs(1)

def test():
    m=matrix(64,8)
    m.buffer.update(draw_message("HELLO WORLD"))
    print("Hello World Test")
    print(m)
    m.buffer={}
    print("Empty Test")
    print(m)

def test_np(r=128,b=0,g=0,clear=True):
    np=[]
    m=[]
    pin = Pin(14, Pin.OUT) 
    np.append(NeoPixel(pin, MAX_PIXELS))
    pin2 = Pin(0, Pin.OUT) 
    np.append(NeoPixel(pin2, MAX_PIXELS))
    pin3 = Pin(2, Pin.OUT) 
    np.append(NeoPixel(pin3, MAX_PIXELS))
    m.append(matrix(64,8,np[0]))
    m.append(matrix(64,8,np[1]))
    m.append(matrix(64,8,np[2]))
    for i in range(3):
        m[i].buffer.update(draw_message(bytearray("HELLO WORLD".encode('utf-8'))))
        m[i].send_np(r,g,b,False)
    for i in range(3):
        np[i].write()
    print("Hello World Test")
    print(m[0])
    if clear:
        time.sleep(10)
        for i in range(3):
            m[i].buffer={}
            m[i].send_np()
        print("Empty Test")
        print(m[0])

def test_font():
    
    img = Image.new("RGB", (100, 24))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("/Users/ryan/Downloads/BitPotion Full Extended/BitPotion.ttf",16)
    draw.text((0,-4), str("Aa!*?-:"), font=font, fill="#0000FF")
    font = ImageFont.truetype("/Users/ryan/Downloads/BitPotion Full Extended/BitPotion.ttf",16)
    draw.text((0,0), str("A!*?-:"), font=font, fill="#0000FF")
    img.save("out.png")
    i=font.getmask("AaBbCc")
    k=0
    for y in range(i.size[1]):
        print(f"\n{y}: ",end="")
        for x in range(i.size[0]):
            if i[k] > 0 :
                print("x",end="")
            else:
                print(" ",end="")
            k += 1



if __name__ == "__main__":
     test_font()