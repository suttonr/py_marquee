#!/usr/bin/env python3
import os
import click
import time
import secrets
from base64 import b64encode
from PIL import Image
import paho.mqtt.client as mqtt

class ctx_obj(object):
    def on_connect(self, client, userdata, flags, rc):
        if self.debug:
            print("on_connect", client, userdata, flags)
        if rc == 0:
            self.mqtt_connected = True
        else:
            self.mqtt_connected = False
    def on_publish(self, client, userdata, mid):
        print("Data sent:", mid)

    def __init__(self, mqtt_topic='', debug=False):
        self.mqttc = mqtt.Client()
        self.mqttc.on_connect = self.on_connect
        self.mqttc.on_publish = self.on_publish
        self.mqtt_connected = False
        self.debug = debug
        self.mqtt_topic = mqtt_topic
pass_appctx = click.make_pass_decorator(ctx_obj, ensure=True)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

@click.group()
@click.option('--mqtt-broker', default=secrets.MQTT_BROKER, help='mqtt broker address')
@click.option('--mqtt-port', default=secrets.MQTT_PORT, help='mqtt broker port')
@click.option('--mqtt-user', default=secrets.MQTT_USERNAME, help='mqtt user')
@click.option('--mqtt-pass', default=secrets.MQTT_PASSWORD, help='mqtt user')
@click.option('--mqtt-topic', default=secrets.MQTT_TOPIC, help='Base topic name')
@click.option('-d', '--debug', default=False, is_flag=True)
@click.pass_context
def cli(ctx, mqtt_broker, mqtt_port, mqtt_user, mqtt_pass, mqtt_topic, debug):
    ctx.obj = ctx_obj(mqtt_topic, debug)
    ctx.obj.mqttc.username_pw_set(mqtt_user, mqtt_pass)
    ctx.obj.mqttc.connect(mqtt_broker, mqtt_port, 60)
    ctx.obj.mqttc.loop_start()
    while not ctx.obj.mqtt_connected:
        print(f"mqtt connecting to {mqtt_user}@{mqtt_broker}")
        time.sleep(.5)

@cli.command()
@click.option('--file-name', default=None, help='File to send')
@click.option('-x', 'x_offset', default=0, type=int, help='x-cord')
@click.option('-y', 'y_offset', default=0, type=int, help='y-cord')
@click.option('--clear', default=False, is_flag=True,
              help='Clear display before sending')
@pass_appctx
def send(appctx, clear, file_name, x_offset=0, y_offset=0):
    """Sends a file to mqtt topic"""
    raw_topic = appctx.mqtt_topic + "/raw"

    click.echo(f"File: {file_name}")
    click.echo(f"Topic: {raw_topic}")

    im = Image.open(file_name)

    data = bytearray()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            if appctx.debug:
                print(y)
            if sum(im.getpixel((x,y))) > 0:
                data += bytearray([x+x_offset,y+y_offset] + list(im.getpixel((x,y))))
                if appctx.debug:
                    print(bytearray([x+x_offset,y+y_offset] + list(im.getpixel((x,y)))) )   
    if appctx.debug:
        print(data)
        print(b64encode(data))
    if clear:
        appctx.mqttc.publish(appctx.mqtt_topic + "/clear").wait_for_publish()
    appctx.mqttc.publish(raw_topic, payload=data).wait_for_publish()

@cli.command()
@pass_appctx
def clear(appctx):
    """Clears the display"""
    appctx.mqttc.publish(appctx.mqtt_topic + "/clear", payload="a").wait_for_publish()

@cli.command()
@click.argument('brightness', type=int)
@pass_appctx
def brightness(appctx, brightness):
    """Sets the global brightness of the display"""
    appctx.mqttc.publish(
            appctx.mqtt_topic + "/bright", payload=brightness.to_bytes(1)
        ).wait_for_publish()

@cli.command()
@click.option('--line', default=1, type=int, help='Line to send to')
@click.argument('message')
@pass_appctx
def text_line(appctx, message, line):
    """Sends a text message to the display"""
    appctx.mqttc.publish(
            f"{appctx.mqtt_topic}/{line}", payload=message
        ).wait_for_publish()

@cli.command()
@click.option('-x', default=0, type=int, help='x-cord')
@click.option('-y', default=0, type=int, help='y-cord')
@click.argument('message')
@pass_appctx
def text(appctx, message, x, y):
    """Sends a text message to the display"""
    payload = bytearray([x, y])
    payload += bytearray(message.encode("utf-8"))
    appctx.mqttc.publish(
            f"{appctx.mqtt_topic}/message", payload=payload
        ).wait_for_publish()


if __name__ == '__main__':
    cli()
