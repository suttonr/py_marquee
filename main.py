import spidev as SPI
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import gc
import secrets
import time
import traceback
import json

from neomatrix.matrix import matrix
from neomatrix.font import *
from marquee.marquee import marquee
from templates.clock import clock
from templates.xmas import xmas
from templates.timer import timer
from templates.gmonster import gmonster
from templates.base import base
from templates.weather import weather
from animation_manager import start_animation_manager, stop_animation_manager
from mqtt_handlers import new_message, init_shared_state
from PIL import ImageDraw
from PIL import ImageFont
from PIL import Image

FGCOLOR=bytearray(b'\x32\x00\x00')
BGCOLOR=bytearray(b'\x00\x00\x00')

SETUP_RUN = False
MAX_PIXELS=512
NP_PINS = [14,0,2]
PIXEL_TIME = 0.05  # Increased from 1.0 to 0.05 for smoother scrolling (20 FPS)

matrices = []
board = marquee()
shared_state = {
    'template': None,
    'local_weather': None,
    'refresh': True,
    'enable_auto_template': True
}
# For backward compatibility
template = property(lambda self: shared_state['template'], lambda self, v: shared_state.update({'template': v}))
local_weather = property(lambda self: shared_state['local_weather'], lambda self, v: shared_state.update({'local_weather': v}))
refresh = property(lambda self: shared_state['refresh'], lambda self, v: shared_state.update({'refresh': v}))
enable_auto_template = property(lambda self: shared_state['enable_auto_template'], lambda self, v: shared_state.update({'enable_auto_template': v}))

# Debug: Track template changes
_last_template_type = None
def debug_template_change():
    global shared_state, _last_template_type
    current_template = shared_state['template'] if shared_state else None
    current_type = type(current_template).__name__ if current_template else None
    print(f"DEBUG: Checking template - current: {current_type}, last: {_last_template_type}, id: {id(current_template) if current_template else None}")
    if current_type != _last_template_type:
        print(f"DEBUG: Template changed from {_last_template_type} to {current_type}")
        _last_template_type = current_type

m = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
m.username_pw_set(secrets.MQTT_USERNAME, secrets.MQTT_PASSWORD)
m.connect(secrets.MQTT_BROKER, secrets.MQTT_PORT, 60)

RESET_PIN = 18
GPIO.setmode(GPIO.BOARD)
GPIO.setup(RESET_PIN, GPIO.OUT)



def process_bright(bright):
    global NP_PINS, MAX_PIXELS, matrices
    for i in range(len(matrices)):
        print("b",i,bright,bright/100)
        matrices[i].brightness = bright / 100

def update_message(message, anchor=(0,0)):
    global matrices, board
    global FGCOLOR, BGCOLOR

    for x,y,b in font_5x8(message, fgcolor=FGCOLOR):
        board.set_pixel( (x+anchor[0]).to_bytes(2,"big") + (y+anchor[1]).to_bytes(1,"big") + b  )

def setup():
    global matrices
    global board, template, local_weather, refresh
    global m
    global MAX_PIXELS

    # Reset fpga
    GPIO.output(RESET_PIN, GPIO.HIGH)
    time.sleep(5)
    GPIO.output(RESET_PIN, GPIO.LOW)
    # Setup Matrix
    hspi = SPI.SpiDev()
    hspi.open(0, 0)
    hspi.max_speed_hz = 48_000_000
    hspi.mode = 0
    for x in range(7):
        for y in range(3):
            print("setup matrix ",len(matrices)," loc ", x,y)
            matrices.append(
                matrix(64, 8, hspi, mode="PYSPI", xoffset=x, yoffset=y)
            )
    board.matrices = matrices
    update_message(bytearray(b"A"), (0,0))
    update_message(bytearray(b"B"), (0,8))
    update_message(bytearray(b"C"), (0,16))
    # Setup mqtt
    m.on_message = new_message
    m.subscribe("esp32/test/#")
    m.subscribe("marquee/#")
    m.subscribe("hello/push/Backyard Garage/temperature/value")
    # Set initial settings
    process_bright(5)
    shared_state['local_weather'] = weather(board, clear=False)
    shared_state['template'] = clock(board, weather=shared_state['local_weather'])
    #template = xmas(board)

    # Initialize globals in handlers module with shared state
    init_shared_state(shared_state, FGCOLOR, BGCOLOR, board, GPIO, RESET_PIN, m)

    time.sleep(2)
    # Start animation manager
    start_animation_manager()
    # Start listening for mqtt
    m.loop_start()

def main():
    print("Main function called, starting writer thread")
    writer_thread()

def writer_thread():
    global board
    board.send(True, False)
    full_refresh = 100
    while True:
        # Existing display logic
        start_ts = time.time()
        if refresh and full_refresh < 0:
            board.send(True, False)
            full_refresh = 100
        elif refresh:
            board.send(True)
        full_refresh -= 1
        end_ts = time.time()
        sleep_time = max(0, PIXEL_TIME - (start_ts-end_ts))
        time.sleep(sleep_time)

if __name__ == '__main__':
    setup()
    main()
