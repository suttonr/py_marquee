"""
MQTT Message Handlers

This module contains handlers for processing MQTT messages received by the marquee system.
Handlers are organized by topic patterns for better maintainability and extensibility.
"""

import time
import traceback
from templates.clock import clock
from templates.timer import timer
from templates.gmonster import gmonster
from templates.base import base

# Shared state from main.py
shared_state = None

# Other global variables
FGCOLOR = None
BGCOLOR = None
board = None
GPIO = None
RESET_PIN = None
m = None

def init_shared_state(state_dict, fgcolor, bgcolor, board_obj, gpio_obj, reset_pin, mqtt_client):
    """Initialize shared state and globals from main.py"""
    global shared_state, FGCOLOR, BGCOLOR, board, GPIO, RESET_PIN, m
    global template, local_weather, refresh, enable_auto_template
    shared_state = state_dict
    FGCOLOR = fgcolor
    BGCOLOR = bgcolor
    board = board_obj
    GPIO = gpio_obj
    RESET_PIN = reset_pin
    m = mqtt_client

    # Set module-level variables to reference shared state
    template = shared_state['template']
    local_weather = shared_state['local_weather']
    refresh = shared_state['refresh']
    enable_auto_template = shared_state['enable_auto_template']

def update_template(new_template):
    """Central function to update template in both module and shared state"""
    global template, shared_state
    from main import debug_template_change
    debug_template_change()
    template = new_template
    debug_template_change()
    if shared_state is not None:
        shared_state['template'] = new_template

# For backward compatibility - these will be updated by init_shared_state
template = None
local_weather = None
refresh = True
enable_auto_template = True

def mqttLogger(message):
    """Log message via MQTT"""
    global m
    if m:
        m.publish("marquee/logging", payload=message).wait_for_publish()

def new_message(client, userdata, msg):
    """Main MQTT message handler with dynamic topic routing"""
    global FGCOLOR, BGCOLOR, board, template, refresh, local_weather, enable_auto_template

    topic = msg.topic
    message = msg.payload

    try:
        if topic == "marquee/pixels":
            return

        if topic != "esp32/test/raw":
            print("nm:", topic, message)

        # Handler mapping for dynamic topic processing
        handlers = {
            "esp32/test/message": handle_esp32_message,
            "esp32/test/text": handle_esp32_text,
            "esp32/test/1": lambda m: update_message(m.payload, (0, 0)),
            "esp32/test/2": lambda m: update_message(m.payload, (0, 8)),
            "esp32/test/3": lambda m: update_message(m.payload, (0, 16)),
            "esp32/test/fgcolor": handle_fgcolor,
            "esp32/test/bgcolor": handle_bgcolor,
            "esp32/test/raw": handle_raw,
            "esp32/test/clear": handle_clear,
            "esp32/test/bright": handle_bright,
            "esp32/test/reset": handle_reset,
            "marquee/template": handle_template,
            "marquee/template/timer/duration": handle_timer_duration,
            "marquee/template/gmonster/box/": handle_gmonster_box,
            "marquee/template/gmonster/count/": handle_gmonster_count,
            "marquee/template/gmonster/inning/": handle_gmonster_inning,
            "marquee/template/gmonster/game": handle_gmonster_game,
            "marquee/template/gmonster/disable-win": handle_gmonster_disable_win,
            "marquee/template/gmonster/disable-close": handle_gmonster_disable_close,
            "marquee/template/gmonster/batter": handle_gmonster_batter,
            "marquee/template/gmonster/bases": handle_gmonster_bases,
            "marquee/auto_template": handle_auto_template,
            "marquee/template/base/scrolltext": handle_scrolltext,
            "marquee/get_pixels": handle_get_pixels,
            "hello/push/Backyard Garage/temperature/value": handle_temperature,
        }

        # Find and execute matching handler
        handled = False
        matched_pattern = ""
        for pattern, handler in handlers.items():
            if topic.startswith(pattern):
                if len(pattern) > matched_pattern:
                    matched_pattern = pattern

        if matched_pattern in handlers:
            print(f"Handler Execute: {pattern} {handler}")
            handlers[matched_pattern](msg)
        else:
            mqttLogger(f"Unrecognized topic: {topic}")

    except Exception as exp:
        print(f"Message exception: {exp}")
        print(traceback.format_exc())
        mqttLogger(f"Error processing message on topic {topic}: {exp}")

# Handler functions

def handle_esp32_message(msg):
    if len(msg.payload) > 2:
        x = int.from_bytes(bytearray(msg.payload[0:2]), "big")
        print("x", x, "y", msg.payload[2], "rawx", msg.payload[0:1])
        update_message(msg.payload[3:], (x, msg.payload[2]))

def handle_esp32_text(msg):
    topic_split = msg.topic.split("/")
    text_size = 16
    if len(topic_split) > 3:
        text_size = int(topic_split[3])
    x = int.from_bytes(bytearray(msg.payload[0:2]), "big")
    print("x", x, "y", msg.payload[2], "rawx", msg.payload[0:1])
    global template, FGCOLOR, BGCOLOR
    template.update_message_2(msg.payload[3:].decode(), font_size=text_size,
        fgcolor=FGCOLOR, bgcolor=BGCOLOR, anchor=(x, msg.payload[2]))

def handle_fgcolor(msg):
    if len(msg.payload) == 3:
        global FGCOLOR
        FGCOLOR = bytearray(msg.payload[0:3])
        print("fgcolor", FGCOLOR)

def handle_bgcolor(msg):
    if len(msg.payload) == 3:
        global BGCOLOR
        BGCOLOR = bytearray(msg.payload[0:3])

def handle_raw(msg):
    process_raw(msg.payload)

def handle_clear(msg):
    global template, board
    if template:
        template.__del__()
    update_template(base(board))

def handle_bright(msg):
    global board
    board.set_brightness(msg.payload[0])

def handle_reset(msg):
    print("resetting...")
    global GPIO, RESET_PIN
    GPIO.output(RESET_PIN, GPIO.HIGH)
    time.sleep(5)
    GPIO.output(RESET_PIN, GPIO.LOW)
    print("reset complete")

def handle_template(msg):
    global refresh, local_weather, template, board
    message = msg.payload
    print("template:", msg.topic, message)
    if message == bytearray(b"gmonster"):
        refresh = False
        check_template(gmonster, force=True)
        refresh = True
        print("gmonster template set")
    elif message == bytearray(b"clock"):
        refresh = False
        check_template(clock, weather=local_weather, force=True)
        refresh = True
        print("clock template set")
    elif message == bytearray(b"timer"):
        refresh = False
        check_template(timer, interval=5, clear=True, force=True)
        template.set_timer_duration("00:10")
        refresh = True
        print("timer template set")

def handle_timer_duration(msg):
    check_template(timer, clear=True)
    global template
    template.set_timer_duration(msg.payload.decode())

def handle_gmonster_box(msg):
    check_template(gmonster)
    topic_split = msg.topic.split("/")
    global template
    if len(topic_split) >= 7 and topic_split[4] == "inning":
        template.update_box(topic_split[4], topic_split[5], msg.payload.decode(),
            index=int(topic_split[6])-1)
    elif len(topic_split) >= 6:
        template.update_box(topic_split[4], topic_split[5], msg.payload.decode())

def handle_gmonster_count(msg):
    check_template(gmonster)
    topic_split = msg.topic.split("/")
    global template
    template.update_count(topic_split[4], msg.payload.decode())

def handle_gmonster_inning(msg):
    check_template(gmonster)
    topic_split = msg.topic.split("/")
    global template
    template.update_current_inning(topic_split[4], msg.payload.decode())

def handle_gmonster_game(msg):
    check_template(gmonster)
    topic_split = msg.topic.split("/")
    global template, local_weather, board
    game_status = msg.payload.decode()
    # Only auto-switch to clock if we're currently showing gmonster template AND game ends
    if (isinstance(template, gmonster) and not template.disable_close and game_status in ("F", "FT", "UR")):
        template.__del__()
        update_template(clock(board, weather=local_weather))
        print("Game ended, automatically switched to clock template")
    else:
        template.update_game_status(game_status)

def handle_gmonster_disable_win(msg):
    check_template(gmonster)
    global template
    if msg.payload.decode().lower() == "true":
        template.disable_win = True
    else:
        template.disable_win = False

def handle_gmonster_disable_close(msg):
    check_template(gmonster)
    global template
    if msg.payload.decode().lower() == "true":
        template.disable_close = True
    else:
        template.disable_close = False

def handle_gmonster_batter(msg):
    check_template(gmonster)
    print(f"batter {msg.payload}")
    global template
    if len(msg.payload.decode()) in range(1, 3):
        template.update_batter(msg.payload.decode())

def handle_gmonster_bases(msg):
    check_template(gmonster)
    print(f"bases {msg.payload}")
    topic_split = msg.topic.split("/")
    occupied = msg.payload.decode().lower() in ("true")
    b = topic_split[4].lower()
    print(f"bases {occupied} {b}")
    global template
    if b in ("first", "second", "third"):
        print(f"write: bases {occupied} {b}")
        template.update_bases(**{b: occupied})

def handle_auto_template(msg):
    global enable_auto_template
    if msg.payload.decode().lower() in ("false", "0", "disable"):
        enable_auto_template = False
    elif msg.payload.decode().lower() in ("true", "1", "enable"):
        enable_auto_template = True

def handle_scrolltext(msg):
    topic_split = msg.topic.split("/")
    text = msg.payload.decode()

    # Default parameters
    speed = 0.05
    direction = "left"
    loop = True
    y_offset = 0

    # Parse optional parameters from topic
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
    global template, FGCOLOR, BGCOLOR
    template.scroll_text(
        text, speed=speed, direction=direction, loop=loop, y_offset=y_offset,
        fgcolor=FGCOLOR, bgcolor=BGCOLOR
    )

def handle_get_pixels(msg):
    global board
    send_pixels(board)

def handle_temperature(msg):
    global local_weather
    local_weather.temperature(msg.payload.decode())

# Utility functions (imported from original main.py)

def check_template(in_template, force=False, **kwargs):
    global board, template, enable_auto_template, shared_state

    old_type = type(template).__name__ if template else None
    old_id = id(template) if template else None

    if force or (enable_auto_template and not isinstance(template, in_template)):
        if template is not None:
            template.__del__()
        template = in_template(board, **kwargs)
        # Update shared state
        if shared_state is not None:
            shared_state['template'] = template
        print(f"DEBUG: check_template changed template from {old_type} (id:{old_id}) to {type(template).__name__ if template else None} (id:{id(template) if template else None})")
        print(f"Loaded template: {template}")

def send_pixels(board):
    global m
    pixels = board.get_pixels()
    for pixel in pixels:
        import json
        payload = json.dumps(pixel)
        m.publish("marquee/pixels", payload)

def process_raw(message):
    global board
    #print("m",message)
    if ( (len(message) % 6) == 0 ):
        for m in range(0,len(message),6):
            board.set_pixel(message[m:m+6])
    else:
        print("Message error:", message)
    print("Raw message processed")

def update_message(message, anchor=(0,0)):
    from neomatrix.font import font_5x8
    global board, FGCOLOR, BGCOLOR

    for x,y,b in font_5x8(message, fgcolor=FGCOLOR):
        board.set_pixel( (x+anchor[0]).to_bytes(2,"big") + (y+anchor[1]).to_bytes(1,"big") + b )
