from  neomatrix.matrix import matrix
from  neomatrix.font import *
try:
    from machine import Pin
    from neopixel import NeoPixel
except:
    pass

import mqtt
import secrets
import time

MESSAGE=[
    bytearray(b"\x41"),
    bytearray(b"\x42"),
    bytearray(b"\x43"),
]
FGCOLOR=(32,0,0)
BGCOLOR=(0,0,0)

SETUP_RUN = False
MAX_PIXELS=512
PIXEL_TIME = 0.1

matrices = []
m = mqtt.mqtt_client()

def mqttLogger(message):
    global m
    m.pub(message, secrets.MQTT_LOGGING_TOPIC)

def new_message(topic, message, t=None):
    global MESSAGE, FGCOLOR, BGCOLOR
    print("nm:",topic, message)
    if topic == b"esp32/test/1":
        MESSAGE[0] = message
        update_message()
    if topic == b"esp32/test/2":
        MESSAGE[1] = message
        update_message()
    if topic == b"esp32/test/3":
        MESSAGE[2] = message
        update_message()
    if topic == b"esp32/test/fgcolor" and len(message) == 3:
        FGCOLOR = (message[0],message[1],message[2])
        print("fgcolor", FGCOLOR)
    if topic == b"esp32/test/bgcolor" and len(message) == 3:
        BGCOLOR = (message[0],message[1],message[2])
    if topic == b"esp32/test/raw":
        process_raw(message)

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


def update_message():
    global matrices
    global MESSAGE, FGCOLOR, BGCOLOR

    for i in range(len(matrices)):
        matrices[i].buffer={}
        matrices[i].buffer.update(draw_small(MESSAGE[i]))
        


def write():
    global matrices
    for i in range(len(matrices)):
        matrices.np.write()


def setup():
    global matrices
    global m
    global MAX_PIXELS

    # Setup Matrix
    matrices.append(
        matrix(64, 8, NeoPixel(Pin(14, Pin.OUT), MAX_PIXELS))
        )
    matrices.append(
        matrix(64, 8, NeoPixel(Pin(0, Pin.OUT), MAX_PIXELS))
        )
    matrices.append(
        matrix(64, 8, NeoPixel(Pin(2, Pin.OUT), MAX_PIXELS))
        )

    m.set_callback(new_message)
    m.sub("esp32/test/#")

def main():
    global SETUP_RUN
    global matrices
    global MESSAGE, FGCOLOR, BGCOLOR

    if not SETUP_RUN:
        setup()
        update_message()
        SETUP_RUN=True

    for i in range(len(matrices)):
        matrices[i].send_np(FGCOLOR, BGCOLOR, False)
    for i in range(len(matrices)):
        print(matrices[i])
        matrices[i].np.write()

while True:
    main()
    m.get_msg()
    time.sleep(PIXEL_TIME)