from  neomatrix.matrix import matrix
from  neomatrix.font import *
try:
    from machine import SPI, Pin, SoftSPI, Timer
    from neopixel import NeoPixel
    import mqtt
    import _thread
except:
    pass
try:
    import spidev as SPI
    import paho.mqtt.client as mqtt
    import RPi.GPIO as GPIO
except:
    pass
import gc
import secrets
import time


FGCOLOR=bytearray(b'\x32\x00\x00')
BGCOLOR=bytearray(b'\x00\x00\x00')

SETUP_RUN = False
MAX_PIXELS=512
NP_PINS = [14,0,2]
PIXEL_TIME = 0.01

matrices = []
#m = mqtt.mqtt_client()
m = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
m.username_pw_set(secrets.MQTT_USERNAME, secrets.MQTT_PASSWORD)
m.connect(secrets.MQTT_BROKER, secrets.MQTT_PORT, 60)
#p10 = Pin(3, mode=Pin.OUT, value=0)
RESET_PIN = 18
GPIO.setmode(GPIO.BOARD)
GPIO.setup(RESET_PIN, GPIO.OUT)

#def free(full=False):
#  gc.collect()
#  F = gc.mem_free()
#  A = gc.mem_alloc()
#  t = gc.threshold()
#  T = F+A
#  P = '{0:.2f}%'.format(F/T*100)
#  if not full: return P
#  else : return ('Total:{0} Free:{1} ({2}) Thresh: {3}'.format(T,F,P,t))

def mqttLogger(message):
    global m
    #m.pub(message, secrets.MQTT_LOGGING_TOPIC)
    m.publish(secrets.MQTT_LOGGING_TOPIC, payload=message).wait_for_publish()

#def new_message(topic, message, t=None):
def new_message(client, userdata, msg):
    global FGCOLOR, BGCOLOR, p10
    topic = msg.topic
    message = msg.payload
    if topic != "esp32/test/raw":
        print("nm:",topic, message)
    if topic == "esp32/test/message" and len(message) > 2:
        x = int.from_bytes(bytearray(message[0:2]), "big")
        print("x",x, "y", message[2], "rawx",message[0:1])
        update_message(message[3:], (x, message[2]))  
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
        #send(fill_background=True)
    if topic == "esp32/test/raw":
        process_raw(message)
    if topic == "esp32/test/clear":
        clear()
    if topic == "esp32/test/bright":
        process_bright(message[0])
    if topic == "esp32/test/reset":
        print("resetting...")
        GPIO.output(RESET_PIN, GPIO.HIGH)
        time.sleep(5)
        GPIO.output(RESET_PIN, GPIO.LOW)
        print("reset complete")

def process_bright(bright):
    global NP_PINS, MAX_PIXELS, matrices
    for i in range(len(matrices)):
        print("b",i,bright,bright/100)
        matrices[i].brightness = bright / 100

def process_raw(message):
    global matrices
    #print("m",message)
    if ( (len(message) % 6) == 0 ):
        for m in range(0,len(message),6):
            process_pixel(message[m:m+6])
    else:
        print("Message error:", message)
    print("Raw message processed")

def process_pixel(message):
    global matrices
    if ( len(message) == 6 ):
        # print(f"{message[0]:03d}{message[1]:03d} : {message[2]} {message[3]} {message[4]}")
        x = int.from_bytes(bytearray(message[0:2]), "big")
        y = int.from_bytes(bytearray(message[2:3]), "big")
        i = int( y / 8 )
        j = int( x / 64 )
        port = i + (j * 3)
        #print("matrix:", i, j, port, len(matrices), x, y)
        if ( port < len(matrices) ):
            matrices[port].buffer.update({f"{(x-int(j*64)):03d}{(y-(i*8)):03d}" : (message[3],message[4],message[5])})
        else:
            print("Invalid Matric Index:", i, j, port, len(matrices) )

def clear(index=None):
    global matrices
    print("clearing")
    if index == None:
        for i in range(len(matrices)):
            print("clearing",i)
            matrices[i].buffer={}
    else:
        matrices[index].buffer={}
    print("done",len(matrices))
    #send(fill_background=True)

def update_message(message, anchor=(0,0)):
    global matrices
    global FGCOLOR, BGCOLOR

    for x,y,b in font_5x8(message, fgcolor=FGCOLOR):
        process_pixel( (x+anchor[0]).to_bytes(2,"big") + (y+anchor[1]).to_bytes(1,"big") + b  )

def send(fill_background=False):
    global matrices
    global FGCOLOR, BGCOLOR

    for i in range(len(matrices)):
        matrices[i].send_np(FGCOLOR, BGCOLOR, fill_background, False)

def write():
    global matrices
    for i in range(len(matrices)):
        if matrices[i].mode == "NP":
            matrices[i].np.write()


def setup():
    global matrices
    global m
    global MAX_PIXELS
    #global p10
    #p10(1)
    #time.sleep(5)
    #p10(0)
    GPIO.output(RESET_PIN, GPIO.HIGH)
    time.sleep(5)
    GPIO.output(RESET_PIN, GPIO.LOW)
    # Setup Matrix
    #hspi = SPI(1, 18_000_000, sck=Pin(14), mosi=Pin(13), miso=Pin(12))
    #hspi = SPI(1, 18_000_000, bits=48, sck=Pin(11), mosi=Pin(10), miso=Pin(9))
    #hspi = SoftSPI( baudrate=20_000_000, sck=Pin(14), mosi=Pin(13), miso=Pin(12))
    hspi = SPI.SpiDev()
    hspi.open(0, 0)
    hspi.max_speed_hz = 1_000_000
    hspi.mode = 0
    #cs = Pin(46, mode=Pin.OUT, value=1)
    #p15 = Pin(15, mode=Pin.OUT, value=0)
    #p16 = Pin(16, mode=Pin.OUT, value=0)
    #p17 = Pin(17, mode=Pin.OUT, value=0)
    for x in range(7):
        for y in range(3):
            print("setup matrix ",len(matrices)," loc ", x,y)
            matrices.append(
                matrix(64, 8, hspi, mode="PYSPI", xoffset=x, yoffset=y)
            )
    #m.set_callback(new_message)
    #m.sub("esp32/test/#")
    m.on_message = new_message
    m.subscribe("esp32/test/#")
    
    process_bright(5)
    m.loop_start()
    #tim1 = Timer(1)
    #tim1.init(period=2000, mode=Timer.PERIODIC, callback=lambda t:m.get_msg())
    #time.sleep(1)
    #tim2 = Timer(2)
    #tim2.init(period=20000, mode=Timer.PERIODIC, callback=lambda t:send(True))

def main():
    global SETUP_RUN
    global matrices
    global FGCOLOR, BGCOLOR, m

    if not SETUP_RUN:
        setup()
        update_message(bytearray(b"A"), (0,0))
        update_message(bytearray(b"B"), (0,8))
        update_message(bytearray(b"C"), (0,16))
        SETUP_RUN=True
    writer_thread()
    #send(True)
    #write()



def writer_thread():
    while True:
        send(True)
        time.sleep(PIXEL_TIME)

def mqtt_thread():
    while True:
        #m.get_msg()
        m.loop_read()
        #print(free(True))
        time.sleep(.1)

#_thread.start_new_thread(mqtt_thread, ())
main()
#gc.threshold(5_000_000)
#writer_thread()
