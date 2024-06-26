#!/usr/bin/env python3
import os
import click
import time
import secrets
from base64 import b64encode
from PIL import Image
import paho.mqtt.client as mqtt

import mlb, nhl

class ctx_obj(object):
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if self.debug:
            print("on_connect", client, userdata, flags)
        if reason_code == 0:
            self.mqtt_connected = True
        else:
            self.mqtt_connected = False
    def on_publish(self, client, userdata, mid, reason_codes, properties):
        if self.debug:
            print("Data sent:", mid)

    def __init__(self, mqtt_topic='', debug=False):
        self.mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
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
@click.option('-xs', 'x_start', default=0, type=int, help='bmp x-cord start')
@click.option('-ys', 'y_start', default=0, type=int, help='bmp y-cord start')
@click.option('-xe', 'x_end', default=None, type=int, help='bmp x-cord end')
@click.option('-ye', 'y_end', default=None, type=int, help='bmp y-cord end')
@click.option('--clear', default=False, is_flag=True,
              help='Clear display before sending')
@pass_appctx
def send(appctx, clear=False, file_name="", x_offset=0, y_offset=0, x_start=0, y_start=0, x_end=0, y_end=0):
    """Sends a file to mqtt topic"""
    raw_topic = appctx.mqtt_topic + "/raw"

    if appctx.debug:
        click.echo(f"File: {file_name}")
        click.echo(f"Topic: {raw_topic}")

    im = Image.open(file_name)
    range_x_end = x_end if x_end else im.size[0]
    range_y_end = y_end if y_end else im.size[1]

    data = bytearray()
    for y in range(y_start, range_y_end):
        for x in range(x_start, range_x_end):
            if appctx.debug:
                print(y)
            if sum(im.getpixel((x,y))) > 0:
                data += (x+x_offset).to_bytes(2,"big") + (y+y_offset).to_bytes(1,"big") 
                data += bytearray(list(im.getpixel((x,y))))
            if appctx.debug:
                print(x,y)
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
            appctx.mqtt_topic + "/bright", payload=brightness.to_bytes(1,"big")
        ).wait_for_publish()

@cli.command()
@click.option('-r', '--red', type=int, default=0)
@click.option('-g', '--green', type=int, default=0)
@click.option('-b', '--blue', type=int, default=0)
@pass_appctx
def bgcolor(appctx, red, green, blue):
    """Sets the global bgcolor of the display"""
    appctx.mqttc.publish(
            appctx.mqtt_topic + "/bgcolor", 
            payload=red.to_bytes(1,"big")+green.to_bytes(1,"big")+blue.to_bytes(1,"big")
        ).wait_for_publish()

@cli.command()
@click.option('-r', '--red', type=int, default=0)
@click.option('-g', '--green', type=int, default=0)
@click.option('-b', '--blue', type=int, default=0)
@pass_appctx
def fgcolor(appctx, red, green, blue):
    """Sets the global bgcolor of the display"""
    appctx.mqttc.publish(
            appctx.mqtt_topic + "/fgcolor", 
            payload=red.to_bytes(1,"big")+green.to_bytes(1,"big")+blue.to_bytes(1,"big")
        ).wait_for_publish()

@cli.command()
@pass_appctx
def reset(appctx):
    """Sets the global bgcolor of the display"""
    appctx.mqttc.publish(
            appctx.mqtt_topic + "/reset", payload = "a"
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
@click.option('-b', default=None, type=int, help='box')
@click.option('-r', default=0, type=int, help='row')
@click.option('-o', '--offset', default=0, type=int, help='offset')
@click.argument('message')
@pass_appctx
def text(appctx, message="", x=0, y=0, b=None, r=0, offset=0, clear_box=False):
    """Sends a text message to the display"""
    if b is not None:
        (x,y) = lookup_box(b,r, offset=offset)
    payload = x.to_bytes(2,"big") + y.to_bytes(1,"big")
    payload += bytearray(message.encode("utf-8"))
    appctx.mqttc.publish(
            f"{appctx.mqtt_topic}/message", payload=payload
        ).wait_for_publish()

#####
# Hockey Commands
#####
@cli.command()
@click.option('-g','--game-pk', default=None, help='game pk')
@click.option('--dry-run', default=False, is_flag=True, help='dry run')
@click.pass_context
def display_nhl_game(ctx, game_pk, dry_run):
    """Sends a nhl game to display"""
    g = nhl.game(game_pk, secrets.NHL_GAME_URL)

    cur_period = min(g.get_current_inning(),3)
    for period in range(1,cur_period+1):
        period_data = g.get_inning_score(period)
        box = period + 100
        for row,team in enumerate(("away", "home")):
            ctx.invoke(update_box, b=box, r=row, num=period_data[team] )
    cur_score = g.get_score()
    for row,team in enumerate(("away", "home")):
        box = 104
        ctx.invoke(update_box, b=box, r=row, num=cur_score[team]["score"] )
        box = 105
        ctx.invoke(update_box, b=box, r=row, num=cur_score[team]["shots"] )
        

@cli.command()
@click.option('-b', default=None, type=int, help='box')
@click.option('-r', default=0, type=int, help='row')
@click.argument('num')
@click.pass_context
def update_box(ctx, b, r, num):
    offset = 4
    if int(num) < 10:
        offset = 8
    (x,y) = lookup_box(b, r, offset=offset)
    if r == 0:
        y -= 1

    ctx.invoke(send, file_name=f"/Users/ryan/Downloads/b_shadow.bmp", x_offset=(x-offset), y_offset=y)
    for digit in str(num):
        ctx.invoke(send, file_name=f"/Users/ryan/Downloads/gold_{digit}.bmp", x_offset=x, y_offset=y)
        x += 8 

#####
# Baseball Commands
#####
@cli.command()
@click.option('-g','--game-pk', default=None, help='game pk')
@click.option('--dry-run', default=False, is_flag=True, help='dry run')
@click.pass_context
def display_mlb_game(ctx, game_pk, dry_run):
    """Sends a mlb game to display"""
    g = mlb.game(game_pk, secrets.MLB_GAME_URL)
    appctx = ctx.obj

    game_status = g.get_game_status()
    ctx.invoke(fgcolor, red=255, green=255, blue=255)
    if game_status == "P" or game_status == "S":
        # Pregame
        dt = g.get_game_date()
        t = dt.strftime("%b %e")
        y = dt.strftime("%Y")
        padding = int((11-len(t))/2) if len(t) <= 10 else 1
        for inning in range(padding, min(len(t)+padding,10)):
            print(t[inning-padding], inning, 0)
            ctx.invoke(text, message=str(t[inning-padding]), b=inning, r=0)
            if inning >= 4 and inning <= 7:
                print(str(y[inning-4]), inning, 1)
                ctx.invoke(text, message=str(y[inning-4]), b=inning, r=1)
        return

    # Write Teams Playing
    teams = g.get_teams(short=True)
    for row,team in enumerate(("away", "home")):
        ctx.invoke(text, message=teams.get(team,""), x=19, y=4+(row*10))

    # Write Pitchers
    pitchers = g.get_pitchers()
    for row,team in enumerate(("away", "home")):
        player = mlb.player(pitchers[team].get("id", None), secrets.MLB_PLAYER_URL)
        clear_box(ctx, b=0, r=1)
        ctx.invoke(text, message=player.get_player_number(), b=0, r=row)

    # Write score by inning
    (cur_inning, is_top_inning) = g.get_current_inning()
    for inning in range(1,cur_inning+1):
        inning_data = g.get_inning_score(inning)
        for row,team in enumerate(("away", "home")):
            s = inning_data.get(team,{}).get("runs",0)
            offset = 0
            if ((inning == cur_inning and is_top_inning and team == "away" ) or 
                (inning == cur_inning and not is_top_inning and team == "home" )):
                ctx.invoke(fgcolor, red=255, green=255)
            if len(str(s)) > 1:
                offset = -2
            if not dry_run and not (inning == cur_inning and is_top_inning and team == "home" ):
                clear_box(ctx, inning, row)
                ctx.invoke(text, message=str(s), b=inning, r=row, offset=offset)
            print(inning, team, s)
    
    # Write current score
    score = g.get_score()
    ctx.invoke(fgcolor, red=255, green=255, blue=255)
    for row,team in enumerate(("away", "home")):
        for index,stat in enumerate(("runs", "hits", "errors")):
            s = score.get(team, {}).get(stat, 0)
            offset = 0
            if len(str(s)) > 1:
                offset = -2
            if not dry_run:
                clear_box(ctx, (11+index), row)
                ctx.invoke(text, message=str(s), b=(11+index), r=row, offset=offset)   
            print(team,stat,s)
    
    # Write batter
    ctx.invoke(fgcolor, red=255, green=255)
    ctx.invoke(send, file_name="/Users/ryan/Downloads/batter_shadow.bmp", x_offset=200, y_offset=10)  
    batter = g.get_batter()
    batter_num = mlb.player(batter.get("id",None), secrets.MLB_PLAYER_URL).get_player_number()
    if len(batter_num) == 2:
        ctx.invoke(text, message=batter_num[0], x=201, y=12)
        ctx.invoke(text, message=batter_num[1], x=211, y=12)  
    elif len(batter_num) == 1:
        ctx.invoke(text, message=batter_num[0], x=211, y=12)  
    ctx.invoke(fgcolor, red=255, green=255, blue=255)

    # Write pitch count
    clear_count(ctx, all=True)
    for k,v in g.get_count().items():
        color = "green" if k=="balls" else "red"
        print(k, v)
        for i in range(v):
            light(ctx, k, i, color)


#####
# Utility Functions
#####
def clear_box(ctx, b, r):
    (x,y) = lookup_box(b,r, offset=-1)
    ctx.invoke(send, file_name="/Users/ryan/Downloads/shadow_box.bmp", x_offset=x, y_offset=(y-1))   

def clear_count(ctx, all=False ):
    sections = ("balls", "strikes")
    if all:
        sections += ("outs",)
    for section in sections:
        num_lights = 3 if section == "balls" else 2
        for index in range(num_lights):
            light(ctx, section, index, "off")

def light(ctx, section, index, color):
    x = lookup_light(section,index)
    y = 14
    ctx.invoke(send, file_name=f"/Users/ryan/Downloads/{color}_light.bmp", x_offset=x, y_offset=y)    

def lookup_light(section, index):
    lights = {
        "balls" : [231, 239, 247, 247],
        "strikes" : [271, 279, 279],
        "outs" : [304, 312, 312]
    }
    return lights[section][index]

def lookup_box(b,r,offset=0):
    x = 0
    y = 0
    if b == 0:
        x =  4
    elif b >= 1 and b <= 10:
        x = 42 + 10 * (b - 1)
    elif b >= 11 and b <= 13:
        x = 146 + 15 * (b - 11)
    elif b >=101 and b <=104:
        x = 112 + 37 * (b - 101)
    elif b == 105:
        x = 310

    if r == 0:
        y = 4
    elif r == 1:
        y = 14
    return ((x+offset) , y)

if __name__ == '__main__':
    cli()
