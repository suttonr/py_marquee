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
    "BOOT1",
    "BOOT2",
    "BOOT3"
]
SETUP_RUN = False
MAX_PIXELS=512
PIXEL_TIME = 0.1

np = []
matrices = []
m = mqtt.mqtt_client()

def new_message(topic, message, t=None):
    global MESSAGE

    if topic == "esp32/test/1":
        MESSAGE[1] = message
    if topic == "esp32/test/2":
        MESSAGE[2] = message
    if topic == "esp32/test/3":
        MESSAGE[3] = message


def write():
    global np
    global m

    for i in range(len(np)):
        np[i].write()
    m.pub(secrets.MQTT_LOGGING_TOPIC,"write")

def setup():
    global np
    global matrices
    global m
    global MAX_PIXELS

    # Setup Matrix
    np.append(NeoPixel(Pin(14, Pin.OUT), MAX_PIXELS))
    np.append(NeoPixel(Pin(0, Pin.OUT), MAX_PIXELS))
    np.append(NeoPixel(Pin(2, Pin.OUT), MAX_PIXELS))
    matrices.append(matrix(64,8,np[0]))
    matrices.append(matrix(64,8,np[1]))
    matrices.append(matrix(64,8,np[2]))
    m.set_callback(new_message)
    m.sub("esp32/test/1")
    m.sub("esp32/test/2")
    m.sub("esp32/test/3")

def main():
    global SETUP_RUN
    global matrix
    global MESSAGE

    if not SETUP_RUN:
        setup()
        SETUP_RUN=True
    for i in range(3):
        matrices[i].buffer.update(draw_message(MESSAGE[i]))
        matrices[i].send_np(False)
    write()

while True:
    main()
    m.get_msg()
    time.sleep(1)