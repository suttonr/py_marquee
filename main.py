from  neomatrix.matrix import matrix
from  neomatrix.font import *
try:
    from machine import Pin
    from neopixel import NeoPixel
except:
    pass
import gc
import mqtt
import secrets
import time

FGCOLOR=(32,0,0)
BGCOLOR=(0,0,0)

SETUP_RUN = False
MAX_PIXELS=512
NP_PINS = [14,0,2]
PIXEL_TIME = 0.1

matrices = []
m = mqtt.mqtt_client()

def free(full=False):
  gc.collect()
  F = gc.mem_free()
  A = gc.mem_alloc()
  T = F+A
  P = '{0:.2f}%'.format(F/T*100)
  if not full: return P
  else : return ('Total:{0} Free:{1} ({2})'.format(T,F,P))

def mqttLogger(message):
    global m
    m.pub(message, secrets.MQTT_LOGGING_TOPIC)

def new_message(topic, message, t=None):
    global FGCOLOR, BGCOLOR
    print("nm:",topic, message)
    if topic == b"esp32/test/message" and len(message) > 2:
        update_message(message[2:], (message[0], message[1]))  
    if topic == b"esp32/test/1":
        update_message(message, (0,0))
    if topic == b"esp32/test/2":
        update_message(message, (0,8))
    if topic == b"esp32/test/3":
        update_message(message, (0,16))
    if topic == b"esp32/test/fgcolor" and len(message) == 3:
        FGCOLOR = (message[0],message[1],message[2])
        print("fgcolor", FGCOLOR)
    if topic == b"esp32/test/bgcolor" and len(message) == 3:
        BGCOLOR = (message[0],message[1],message[2])
        send(fill_background=True)
    if topic == b"esp32/test/raw":
        process_raw(message)
    if topic == b"esp32/test/clear":
        clear()
    if topic == b"esp32/test/bright":
        process_bright(message[0])

def process_bright(bright):
    global NP_PINS, MAX_PIXELS, matrices
    for i in range(len(matrices)):
        print("b",i,bright,bright/100)
        matrices[i].brightness = bright / 100

def process_raw(message):
    global matrices
    print("m",message)
    if ( (len(message) % 5) == 0 ):
        for m in range(0,len(message),5):
            process_pixel(message[m:m+5])
    else:
        print("Message error:", message)

def process_pixel(message):
    global matrices
    if ( len(message) == 5 ):
        print(f"{message[0]:03d}{message[1]:03d} : {message[2]} {message[3]} {message[4]}")
        i = int( message[1] >> 3 )
        print("matrix:",i)
        if ( i < len(matrices) ):
            matrices[i].buffer.update({f"{message[0]:03d}{(message[1]-(i*8)):03d}" : (message[2],message[3],message[4])})
        else:
            print("Invalid Matric Index:", i)

def clear(index=None):
    global matrices
    print("clearing")
    if index == None:
        for i in range(len(matrices)):
            matrices[i].buffer={}
    else:
        matrices[index].buffer={}
    send(fill_background=True)

def update_message(message, anchor=(0,0)):
    global matrices
    global FGCOLOR, BGCOLOR

    for x,y,b in font_4x4(message):
        process_pixel( bytearray( [x+anchor[0], y+anchor[1]] ) + b  )

def send(fill_background=False):
    global matrices
    global FGCOLOR, BGCOLOR

    for i in range(len(matrices)):
        matrices[i].send_np(FGCOLOR, BGCOLOR, fill_background, False)
        print(matrices[i])

def write():
    global matrices
    for i in range(len(matrices)):
        matrices[i].np.write()


def setup():
    global matrices
    global m
    global MAX_PIXELS

    # Setup Matrix
    matrices.append(
        matrix(64, 8, NeoPixel(Pin(45, Pin.OUT), MAX_PIXELS, timing=1))
        )
    matrices.append(
        matrix(64, 8, NeoPixel(Pin(48, Pin.OUT), MAX_PIXELS, timing=1))
        )
    matrices.append(
        matrix(64, 8, NeoPixel(Pin(47, Pin.OUT), MAX_PIXELS, timing=1))
        )

    m.set_callback(new_message)
    m.sub("esp32/test/#")

def main():
    global SETUP_RUN
    global matrices
    global FGCOLOR, BGCOLOR

    if not SETUP_RUN:
        setup()
        update_message(bytearray(b"A"), (0,0))
        update_message(bytearray(b"B"), (0,8))
        update_message(bytearray(b"C"), (0,16))
        SETUP_RUN=True

    send()
    write()

while True:
    main()
    m.get_msg()
    #print(free(True))
    time.sleep(PIXEL_TIME)