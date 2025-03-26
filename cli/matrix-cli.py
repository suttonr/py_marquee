#!/usr/bin/env python3
import os
import click
import time
import secrets
from base64 import b64encode
from PIL import Image
import paho.mqtt.client as mqtt

import mlb, nhl, election

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
@click.argument('arg', type=int)
@pass_appctx
def auto_template(appctx, arg):
    """Sets auto switching of template"""
    appctx.mqttc.publish(appctx.mqtt_topic + "/clear", payload=arg).wait_for_publish()

@cli.command()
@click.argument('brightness', type=int)
@pass_appctx
def brightness(appctx, brightness):
    """Sets the global brightness of the display"""
    appctx.mqttc.publish(
            appctx.mqtt_topic + "/bright", payload=brightness.to_bytes(1,"big")
        ).wait_for_publish()

@cli.command()
@click.argument('template')
@pass_appctx
def set_template(appctx, template):
    """Sets the active template of the display"""
    appctx.mqttc.publish(
            "marquee/template", payload=template
        ).wait_for_publish()

@cli.command()
@click.option('-b', '--box')
@click.option('-s', '--side')
@click.option('-i', '--inning', default=None)
@click.option('-t', '--team', default=None)
@click.option('-g', '--game', default=None)
@click.option('--backfill', default=False, is_flag=True, 
    help='backfill game data, supresses influxdb update')
@click.argument('message')
@pass_appctx
def send_box(appctx, message, box, side, inning, team=None, game=None, backfill=None):
    """Sets the active template of the display"""
    topic = f"marquee/template/gmonster/box/{box}/{side}"
    if box == "inning":
        topic += f"/{inning}" if inning else "/10"
    # If this is a backfill supress the team and game to avoid updating influx
    if (team is not None) and not backfill:
        topic += f"/{team}"
        if game is not None:
            topic += f"/{game}"
    print(f"{topic} {message}")
    appctx.mqttc.publish(
            topic, payload=message
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
@click.option('-s', default=0, type=int, help='size')
@click.option('-o', '--offset', default=0, type=int, help='offset')
@click.argument('message')
@pass_appctx
def text(appctx, message="", x=0, y=0, b=None, r=0, s=16,  offset=0, clear_box=False):
    """Sends a text message to the display"""
    if b is not None:
        (x,y) = lookup_box(b,r, offset=offset)
    payload = x.to_bytes(2,"big") + y.to_bytes(1,"big")
    payload += bytearray(message.encode("utf-8"))
    appctx.mqttc.publish(
            f"{appctx.mqtt_topic}/text/{s}", payload=payload
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

    ctx.invoke(send, file_name=f"img/b_shadow.bmp", x_offset=(x-offset), y_offset=y)
    for digit in str(num):
        ctx.invoke(send, file_name=f"img/gold_{digit}.bmp", x_offset=x, y_offset=y)
        x += 8 

@cli.command()
@click.argument('num')
@pass_appctx
def update_batter(appctx, num):
    appctx.mqttc.publish(
            f"marquee/template/gmonster/batter", payload=str(num)
        ).wait_for_publish()

@cli.command()
@click.argument('status')
@pass_appctx
def update_game(appctx, status):
    appctx.mqttc.publish(
            f"marquee/template/gmonster/game", payload=str(status)
        ).wait_for_publish()

@cli.command()
@click.argument('num')
@click.option('-n', '--name', default="outs", help='count to update')
@pass_appctx
def update_count(appctx, name, num):
    appctx.mqttc.publish(
            f"marquee/template/gmonster/count/{name}", payload=str(num)
        ).wait_for_publish()

@cli.command()
@click.argument('status')
@click.option('-i', '--inning', default="0", help='inning')
@pass_appctx
def update_inning(appctx, inning, status):
    appctx.mqttc.publish(
            f"marquee/template/gmonster/inning/{inning}", payload=str(status)
        ).wait_for_publish()

@cli.command()
@click.argument('status')
@pass_appctx
def disable_win(appctx, status):
    appctx.mqttc.publish(
            f"marquee/template/gmonster/disable-win", payload=str(status)
        ).wait_for_publish()

@cli.command()
@click.argument('status')
@pass_appctx
def disable_close(appctx, status):
    appctx.mqttc.publish(
            f"marquee/template/gmonster/disable-close", payload=str(status)
        ).wait_for_publish()

#####
# Football Commands
#####
@cli.command()
@click.option('-g','--game-pk', default=None, help='game pk')
@click.option('--backfill', default=False, is_flag=True, help='backfill game data')
@click.option('--dry-run', default=False, is_flag=True, help='dry run')
@click.pass_context
def send_nfl_game(ctx, game_pk, backfill, dry_run):
    pregame_statuses = ("S", "P", "PW", "PI")
    #try:
    g = nfl.game(game_pk, secrets.MLB_GAME_URL)
    #except:
    #    print("Failed to get NFL data")
    #    exit(89)
    appctx = ctx.obj

    teams = g.get_teams()
    score = g.get_score()
    score_all = g.get_period_score()

    rows = ["", ""]
    for row,team in enumerate(("away", "home")):
        timeouts = ""
        for i in range(score[team]["timeouts"]):
            timeouts += '-'
        rows[row] = f'  {str(teams[team]).ljust(4)} {str(score_all[team][0]).ljust(4)} {str(score_all[team][1]).ljust(4)} {str(score_all[team][2]).ljust(4)} {str(score_all[team][3]).ljust(4)} {str(score[team]["score"]).ljust(2)} {str(timeouts).ljust(2)}'
    
    y=4
    team_colors = g.get_team_colors()
    ctx.invoke(fgcolor, red=team_colors["away"][0], green=team_colors["away"][1], blue=team_colors["away"][2])
    for r in rows:
        print(r)
        ctx.invoke(text, message=r.replace("0","O"), x=64, y=y, s=16)
        ctx.invoke(fgcolor, red=team_colors["home"][0], green=team_colors["home"][1], blue=team_colors["home"][2])
        y += 9
    ctx.invoke(fgcolor, red=128, green=128, blue=0)
    l = ["1st", "2nd", "3rd", "4th"]
    m = f'Q{str(g.get_current_period())} {str(g.get_clock())}  {l[g.get_down()-1]} and {g.get_yards()}'
    ctx.invoke( text, message=m.replace("0","O"), x=235, y=6, s=32 )

#####
# Election Commands
#####
@cli.command()
@click.option('--dry-run', default=False, is_flag=True, help='dry run')
@click.pass_context
def send_election(ctx, dry_run):
    try:
        e = election.election(base_url = secrets.ELECTION_URL)
    except Exception as e:
        print("Failed to get election data",e)
        exit(1)
    
    print(f"{e.get_next_polls_close()}")
    print(e.get_vote_delegates())
    ctx.invoke(clear)
    x=0
    y=0
    for code,delegates in e.get_vote_delegates().items():
        print(code,delegates,x,y)
        if code == "D":
            ctx.invoke(fgcolor, red=0, green=0, blue=255)
        else:
            ctx.invoke(fgcolor, red=255, green=0, blue=0)
        ctx.invoke(text, message=code, x=x, y=y, s=24)
        y += 3
        
        ctx.invoke(text, message=f'{"*"*(int(delegates/10))} - {delegates}'.replace("0","O"), x=14, y=y, s=16)
        y += 9

    print(e.get_hot_races())
    x=250
    y=0
    for index, race in enumerate(e.get_hot_races().items()):
        state, results = race
        print(index, state, results)
        ctx.invoke(fgcolor, red=255, green=255, blue=255)
        ctx.invoke(text, message=f"{state} {results.get('reporting',0) }% ".replace("0","O"), x=x, y=y, s=16)
        y += 8
        for code, p_votes in results["results"].items():
            if code == "D":
                ctx.invoke(fgcolor, red=0, green=0, blue=255)
            else:
                ctx.invoke(fgcolor, red=255, green=0, blue=0)
            ctx.invoke(text, message=f"{code}: {p_votes}% ".replace("0","O"), x=(x+3), y=y, s=16)
            y += 8
        print(x)
        x -= 10





#####
# Baseball Commands
#####
@cli.command()
@click.option('-g','--game-pk', default=None, help='game pk')
@click.option('--backfill', default=False, is_flag=True, help='backfill game data')
@click.option('--dry-run', default=False, is_flag=True, help='dry run')
@click.pass_context
def send_mlb_game(ctx, game_pk, backfill, dry_run):
    pregame_statuses = ("S", "P", "PW", "PI", "PR")
    game_status = ""
    try:
        g = mlb.game(game_pk, secrets.MLB_GAME_URL)
        # If status throws we didn't get valid game data
        game_status = g.get_game_status() 
    except:
        print("Failed to get MLB data")
        exit(89)
    appctx = ctx.obj

    if game_status in ("S"):
        ctx.invoke(update_game, status=game_status)
        print(f"Pregame {game_status}")
        exit(98)

    # Write Teams Playing
    teams = g.get_teams(short=True)
    for row,team in enumerate(("away", "home")):
        ctx.invoke(send_box, message=teams.get(team,""), box="team", side=team, backfill=backfill)

    # Write Pitchers
    pitchers = g.get_pitchers()
    for row,team in enumerate(("away", "home")):
        player = mlb.player(pitchers[team], secrets.MLB_PLAYER_URL)
        ctx.invoke(send_box, message=player.get_player_number(), box="pitcher", side=team, backfill=backfill)
    
    # Inning, backfill if requested
    (cur_inning, is_top_inning) = g.get_current_inning()
    ctx.invoke(update_inning, inning=cur_inning, status=g.get_inning_state())
    inning_start = 1 if backfill else cur_inning
    for inning in range(inning_start,cur_inning+1):
        inning_data = g.get_inning_score(inning)
        for row,team in enumerate(("away", "home")):
            s = inning_data.get(team,{}).get("runs",0)
            if not (inning == cur_inning and is_top_inning and team == "home" ):
                ctx.invoke(send_box, message=str(s), box="inning", side=team, inning=inning, team=teams.get(team, None), game=game_pk, backfill=backfill)
    
    # Write current score
    score = g.get_score()
    for row,team in enumerate(("away", "home")):
        for index,stat in enumerate(("runs", "hits", "errors")):
            s = score.get(team, {}).get(stat, 0)
            ctx.invoke(send_box, message=str(s), box=stat, side=team, team=teams.get(team, None), game=game_pk, backfill=backfill ) 
    
    # Write batter
    batter = g.get_batter()
    if not g.is_play_complete():
        batter_num = mlb.player(batter.get("id",None), secrets.MLB_PLAYER_URL).get_player_number()
        ctx.invoke(update_batter, num=batter_num)

    # Write pitch count
    outs = 0
    for k,v in g.get_count().items():
        color = "green" if k=="balls" else "red"
        if k == "outs":
            outs = v
        if k == "outs" or not g.is_play_complete():
            ctx.invoke(update_count, name=k, num=v) 

    # Write Stats
    p_team = "away"
    b_team = "home"
    if is_top_inning:
        pitcher_stats = g.get_player_boxscore(pitchers["home"]).get("pitching", {})
        p_team = "home"
        b_team = "away"
    else:
        pitcher_stats = g.get_player_boxscore(pitchers["away"]).get("pitching", {})
    batter_stats = g.get_player_boxscore(batter.get("id", None)).get("batting", {})
    batter_stats_season = g.get_player_season(batter.get("id", None)).get("batting", {})
    p_msg =  f'P T: { pitcher_stats.get("pitchesThrown", "") } '
    p_msg += f'K: { pitcher_stats.get("strikeOuts", "0") } S: { pitcher_stats.get("strikes", "") } '
    p_msg += f'{ pitcher_stats.get("strikePercentage", "")[1:3] }%'
    b_msg = f'B {batter_stats.get("summary", "-").split("|")[0].strip()} A: {batter_stats_season.get("avg")} P: {batter_stats_season.get("ops")}' 
    if game_status not in pregame_statuses:
        ctx.invoke(send_box, message=p_msg[:25], box="message", side=p_team)
        if not g.is_play_complete(): 
            ctx.invoke(send_box, message=b_msg[:25], box="message", side=b_team)  
        else:
            ctx.invoke(send_box, message="", box="message", side=b_team)
    ctx.invoke(update_game, status=game_status)
    if cur_inning == 8 and (g.get_inning_state()=="Middle" or (g.get_inning_state()=="Top" and outs == 3)):
        exit(80)
    if game_status in ("O"):
        for row,team in enumerate(("away", "home")):
            if ( teams.get(team,"") == "BOS" and 
                 score.get(team, {}).get("runs", 0) >= score.get("home", {}).get("runs", 0) and
                 score.get(team, {}).get("runs", 0) >= score.get("away", {}).get("runs", 0) ):
                 exit(81)
    print(f"game_status: {game_status}")
    # exitcode 99 if game is over
    if game_status in ("F", "FT"):
        print("Game is final")
        exit(99)
    elif game_status in pregame_statuses:
        print(f"Pregame {game_status}")
        exit(98)


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

    # Write Teams Playing
    teams = g.get_teams(short=True)
    for row,team in enumerate(("away", "home")):
        ctx.invoke(text, message=teams.get(team,""), x=19, y=4+(row*10))
    
    # Write Pitchers
    pitchers = g.get_pitchers()
    for row,team in enumerate(("away", "home")):
        player = mlb.player(pitchers[team], secrets.MLB_PLAYER_URL)
        clear_box(ctx, b=0, r=row)
        clear_box(ctx, b=99, r=row)
        ctx.invoke(text, message=player.get_player_number(), b=0, r=row)
    
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

    # Write score by inning
    (cur_inning, is_top_inning) = g.get_current_inning()
    for inning in range(1,cur_inning+1):
        inning_data = g.get_inning_score(inning)
        for row,team in enumerate(("away", "home")):
            s = inning_data.get(team,{}).get("runs",0)
            offset = 0
            if ( game_status != "F" and 
                g.get_inning_state() != "End" and g.get_inning_state() != "Middle" and
                ((inning == cur_inning and is_top_inning and team == "away" ) or 
                (inning == cur_inning and not is_top_inning and team == "home" )) ):
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
    ctx.invoke(send, file_name="img/batter_shadow.bmp", x_offset=200, y_offset=10)
    batter = g.get_batter()
    if not g.is_play_complete():
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
        if k == "outs" or not g.is_play_complete():
            print(k, v)
            for i in range(v):
                light(ctx, k, i, color)
    
    # Write Stats
    p_row = 4
    b_row = 14
    if is_top_inning:
        pitcher_stats = g.get_player_boxscore(pitchers["home"]).get("pitching", {})
        p_row = 14
        b_row = 4
    else:
        pitcher_stats = g.get_player_boxscore(pitchers["away"]).get("pitching", {})
    batter_stats = g.get_player_boxscore(batter.get("id", None)).get("batting", {})
    batter_stats_season = g.get_player_season(batter.get("id", None)).get("batting", {})
    p_msg =  f'P T:{ pitcher_stats.get("pitchesThrown", "") } '
    p_msg += f'K:{ pitcher_stats.get("strikeOuts", "0") } S:{ pitcher_stats.get("strikes", "") } '
    p_msg += f'{ pitcher_stats.get("strikePercentage", "")[1:3] }%'
    b_msg = f'B {batter_stats.get("summary", "-").split("|")[0].strip()} A:{batter_stats_season.get("avg")} P:{batter_stats_season.get("ops")}'
    
    ctx.invoke(send, file_name="img/green_monster_marquee_mask.bmp", x_start=325)   
    ctx.invoke(text, message=p_msg[:20], x=325, y=p_row)
    if not g.is_play_complete(): 
        ctx.invoke(text, message=b_msg[:20], x=325, y=b_row)     


#####
# Utility Functions
#####
def clear_box(ctx, b, r):
    (x,y) = lookup_box(b,r, offset=-1)
    ctx.invoke(send, file_name="img/shadow_box.bmp", x_offset=x, y_offset=(y-1))   

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
    ctx.invoke(send, file_name=f"img/{color}_light.bmp", x_offset=x, y_offset=y)    

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
    elif b == 99:
        x = 10
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
