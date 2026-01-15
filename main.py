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
template = None
local_weather = None
refresh = True
enable_auto_template = True

m = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
m.username_pw_set(secrets.MQTT_USERNAME, secrets.MQTT_PASSWORD)
m.connect(secrets.MQTT_BROKER, secrets.MQTT_PORT, 60)

RESET_PIN = 18
GPIO.setmode(GPIO.BOARD)
GPIO.setup(RESET_PIN, GPIO.OUT)

def mqttLogger(message):
    global m
    m.publish(secrets.MQTT_LOGGING_TOPIC, payload=message).wait_for_publish()

def new_message(client, userdata, msg):
    global FGCOLOR, BGCOLOR, p10
    global board, template, refresh, local_weather, enable_auto_template
    topic = msg.topic
    message = msg.payload
    try:
        if topic == "marquee/pixels":
            return
        if topic != "esp32/test/raw":
            print("nm:",topic, message)
        if topic == "esp32/test/message" and len(message) > 2:
            x = int.from_bytes(bytearray(message[0:2]), "big")
            print("x", x, "y", message[2], "rawx", message[0:1])
            update_message(message[3:], (x, message[2]))  
        if "esp32/test/text" in topic and len(message) > 2:
            topic_split = topic.split("/")
            text_size = 16
            if len(topic_split) > 3:
                text_size = int(topic_split[3])
            x = int.from_bytes(bytearray(message[0:2]), "big")
            print("x", x, "y", message[2], "rawx", message[0:1])
            template.update_message_2( message[3:].decode(), font_size=text_size,
                fgcolor=FGCOLOR, bgcolor=BGCOLOR, anchor=(x, message[2]))
            #update_message(message[3:], (x, message[2]))  
        if topic == "esp32/test/1":
            update_message(message, (0,0))
        if topic == "esp32/test/2":
            update_message(message, (0,8))
        if topic == "esp32/test/3":
            update_message(message, (0,16))
        if topic == "esp32/test/fgcolor" and len(message) == 3:
            FGCOLOR = bytearray(message[0:3])
            print("fgcolor", FGCOLOR)
        if topic == "esp32/test/bgcolor" and len(message) == 3:
            BGCOLOR = bytearray(message[0:3])
        if topic == "esp32/test/raw":
            process_raw(message)
        if topic == "esp32/test/clear":
            if template:
                template.__del__()
            template = base(board)
        if topic == "esp32/test/bright":
            board.set_brightness(message[0])
        if topic == "esp32/test/reset":
            print("resetting...")
            GPIO.output(RESET_PIN, GPIO.HIGH)
            time.sleep(5)
            GPIO.output(RESET_PIN, GPIO.LOW)
            print("reset complete")

        if topic == "marquee/template":
            print("template:",topic, message)
            if message == bytearray(b"gmonster"):
                refresh = False
                check_template(gmonster)
                refresh = True
                print("gmonster template set")
            elif message == bytearray(b"clock"):
                refresh = False
                check_template(clock, weather=local_weather)
                refresh = True
                print("clock template set")
            elif message == bytearray(b"timer"):
                refresh = False
                check_template(timer, interval=5, clear=True)
                template.set_timer_duration("00:10")
                refresh = True
                print("timer template set")

        if "marquee/template/timer/duration" in topic:
            check_template(timer, clear=True)
            template.set_timer_duration(message.decode())

        if "marquee/template/gmonster/box/" in topic:
            check_template(gmonster)
            topic_split = topic.split("/")
            if len(topic_split) >= 7 and topic_split[4] == "inning":
                template.update_box(topic_split[4], topic_split[5], message.decode(), 
                    index=int(topic_split[6])-1)
            elif len(topic_split) >= 6:
                template.update_box(topic_split[4], topic_split[5], message.decode())

        if "marquee/template/gmonster/count/" in topic:
            check_template(gmonster)
            topic_split = topic.split("/")
            template.update_count(topic_split[4], message.decode())

        if "marquee/template/gmonster/inning/" in topic:
            check_template(gmonster)
            topic_split = topic.split("/")
            template.update_current_inning(topic_split[4], message.decode())

        if "marquee/template/gmonster/game" in topic:
            check_template(gmonster)
            topic_split = topic.split("/")
            if ( not template.disable_close and message.decode() in ("F", "FT", "UR") ):
                template.__del__()
                template = clock(board, weather=local_weather)
            else:
                template.update_game_status(message.decode())

        if "marquee/template/gmonster/disable-win" in topic:
            check_template(gmonster)
            topic_split = topic.split("/")
            if message.decode().lower() == "true":
                template.disable_win = True
            else:
                template.disable_win = False

        if "marquee/template/gmonster/disable-close" in topic:
            check_template(gmonster)
            topic_split = topic.split("/")
            if message.decode().lower() == "true":
                template.disable_close = True
            else:
                template.disable_close = False

        if "marquee/template/gmonster/batter" in topic:
            check_template(gmonster)
            print(f"batter {message}")
            topic_split = topic.split("/")
            if len(message.decode()) in range(1,3):
                template.update_batter(message.decode())

        if "marquee/template/gmonster/bases" in topic:
            check_template(gmonster)
            print(f"bases {message}")
            topic_split = topic.split("/")
            ocupied = message.decode().lower() in ("true")
            b = topic_split[4].lower()
            print(f"bases {ocupied} {b}")
            if b in ("first", "second", "third"):
                print(f"write: bases {ocupied} {b}")
                template.update_bases(**{b:ocupied})

        if "marquee/auto_template" in topic:
            if message.decode().lower() in ( "false", "0", "disable" ):
                enable_auto_template = False
            elif message.decode().lower() in ( "true", "1", "enable" ):
                enable_auto_template = True
    
        if "marquee/template/base/scrolltext" in topic:
            # Parse scroll parameters from topic: marquee/template/base/scrolltext/speed/direction/loop/y_offset
            topic_split = topic.split("/")
            text = message.decode()

            # Default parameters
            speed = 0.05
            direction = "left"
            loop = True
            y_offset = 0

            # Parse optional parameters from topic (parameters start at index 4)
            # Topic format: marquee/template/base/scrolltext/speed/direction/loop/y_offset
            if len(topic_split) > 4:
                try:
                    speed = float(topic_split[4])
                except (ValueError, IndexError):
                    pass
            if len(topic_split) > 5:
                if topic_split[5].lower() in ("left", "right"):
                    direction = topic_split[5].lower()
            if len(topic_split) > 6:
                loop = topic_split[6].lower() not in ("false", "0", "no")
            if len(topic_split) > 7:
                try:
                    y_offset = int(topic_split[7])
                except (ValueError, IndexError):
                    pass

            print(f"Scrolling text: '{text}' speed={speed} direction={direction} loop={loop} y_offset={y_offset}")
            template.scroll_text(text, speed=speed, direction=direction, loop=loop, y_offset=y_offset)

        if "marquee/get_pixels" in topic:
            send_pixels(board)

        if "hello/push/Backyard Garage/temperature/value" in topic:
            local_weather.temperature(message.decode())
    except Exception as exp:
        print(f"message exception: {exp}")
        print(traceback.format_exc())

def check_template(in_template, **kwargs):
    global board, template, enable_auto_template

    if enable_auto_template and not isinstance(template, in_template):
        if template is not None:
            template.__del__()
        template = in_template(board, **kwargs)
        print(f"Loaded template: {template}")

def process_bright(bright):
    global NP_PINS, MAX_PIXELS, matrices
    for i in range(len(matrices)):
        print("b",i,bright,bright/100)
        matrices[i].brightness = bright / 100

def send_pixels(board):
    global m
    pixels = board.get_pixels()
    for pixel in pixels:
        payload = json.dumps(pixel)
        m.publish(f"marquee/pixels", payload)



def process_raw(message):
    global matrices, board
    #print("m",message)
    if ( (len(message) % 6) == 0 ):
        for m in range(0,len(message),6):
            board.set_pixel(message[m:m+6])
    else:
        print("Message error:", message)
    print("Raw message processed")

def update_message(message, anchor=(0,0)):
    global matrices, board
    global FGCOLOR, BGCOLOR

    for x,y,b in font_5x8(message, fgcolor=FGCOLOR):
        board.set_pixel( (x+anchor[0]).to_bytes(2,"big") + (y+anchor[1]).to_bytes(1,"big") + b  )

def setup():
    global matrices
    global board, template, local_weather
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
    local_weather = weather(board, clear=False)
    template =  clock(board, weather=local_weather)
    #template = xmas(board)
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
    full_refresh = 10
    while True:
        # Existing display logic
        if refresh and full_refresh < 0:
            board.send(True, False)
            full_refresh = 10
        elif refresh:
            board.send(True)
        full_refresh -= 1
        time.sleep(PIXEL_TIME)

if __name__ == '__main__':
    setup()
    main()
