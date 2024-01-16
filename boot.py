import network
import secrets

def do_connect():
    network.WLAN(network.AP_IF).active(False)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_KEY)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())

do_connect()