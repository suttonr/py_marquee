from  neomatrix.matrix import matrix
from  neomatrix.font import *
try:
    from machine import Pin
    from neopixel import NeoPixel
except:
    pass
import time

MAX_PIXELS=128
PIXEL_TIME = 0.1

def test():
    m=matrix(64,8)
    m.buffer.update(draw_message("HELLO WORLD"))
    print("Hello World Test")
    print(m)
    m.buffer={}
    print("Empty Test")
    print(m)

def test_np():
    np=[]
    pin = Pin(14, Pin.OUT) 
    np.append(NeoPixel(pin, MAX_PIXELS))
    pin2 = Pin(0, Pin.OUT) 
    np.append(NeoPixel(pin2, MAX_PIXELS))
    pin3 = Pin(2, Pin.OUT) 
    np.append(NeoPixel(pin3, MAX_PIXELS))
    m=matrix(64,8,np[0])
    m.buffer.update(draw_message("HELLO WORLD"))
    print("Hello World Test")
    m.send_np()
    print(m)
    time.sleep(10)
    m.buffer={}
    m.send_np()
    print("Empty Test")
    print(m)
    time.sleep(10)

if __name__ == "__main__":
     test()