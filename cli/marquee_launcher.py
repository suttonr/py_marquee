#!/usr/bin/env python3
import sys,os
import click
import time
import secrets
import subprocess
from zoneinfo import ZoneInfo
from datetime import datetime, timezone, timedelta
import logging
logger = logging.getLogger(__name__)

import mlb

@click.group()
@click.option('-d', '--debug', default=False, is_flag=True)
@click.pass_context
def cli(ctx, debug):
    pass


@cli.command()
@click.option('-f', default=None, type=str, help='team filter')
@click.option('-s', '--sleep', default=30, type=int, help='sleep time betwen checks')
@click.option('-l', '--launch', default=False, is_flag=True, help='launch game when found')
@click.pass_context
def find_games(ctx, f, sleep, launch):
    while True:
        ctx.invoke(get_schedule, f=f, launch=launch)
        time.sleep(sleep * 60)

@cli.command()
@click.option('-d', default=None, type=str, help='date, default=today')
@click.option('-f', default=None, type=str, help='team filter')
@click.option('-l', '--launch', default=False, is_flag=True, help='launch watch if game starts this hour')
@click.pass_context
def get_schedule(ctx, f, d, launch):
    now = datetime.now(ZoneInfo("America/New_York"))
    date_str = d if d is not None else now.strftime("%Y-%m-%d")
    try:
        sch = mlb.schedule(date_str, secrets.MLB_SCHEDULE_URL)
    except:
        logger.error(f"Failed to get schedule for date {date_str} and filter {f}")

    for game in sch.get_games(f):
        game_dt = datetime.fromisoformat(game.get("gameDate"))
        delta_to_game = game_dt - now
        print(f'{game.get("gameDate")}  {game.get("gamePk")}  {game.get("awayTeam")} vs {game.get("homeTeam")} in {delta_to_game}')
        if (launch and game_dt > now and delta_to_game < timedelta(hours=1)):
            ctx.invoke(watch_mlb_game, game_pk=game.get("gamePk") )


@cli.command()
@click.option('-g','--game-pk', default=None, help='game pk')
@click.option('-i','--interval', default=20, type=int, help='interval to update')
@click.pass_context
def watch_mlb_game(ctx, game_pk, interval):
    logger.info(f"Started watching gp={game_pk}")
    retcode = 0
    sweet_caroline = False
    dirty_water = False
    while retcode == 0 or retcode == 80 or retcode == 81 or retcode == 89 or retcode == 98:
        result = subprocess.run(["python3", "matrix-cli.py", "send-mlb-game", "-g", str(game_pk)], capture_output=True, text=True)
        retcode = int(result.returncode)
        sleep_time = interval
        print("result:", retcode)
        for line in result.stdout.split('\n'):
            logger.info(line)
        for line in result.stderr.split("\n"):
            logger.error(line)
        if retcode == 0:
            logger.debug("Game is active")
        elif retcode == 80:
            logger.debug("Game is active")
            if not sweet_caroline:
                logger.info("Sweet Caroline")
                r = subprocess.run(["/usr/bin/curl", "http://192.168.2.178/apps/api/493/trigger?access_token=cd3abd09-23eb-4e75-acca-f0ecbbab11d0"], capture_output=True, text=True)
                sweet_caroline = True
        elif retcode == 81:
            logger.debug("Game is active")
            if not dirty_water:
                logger.info("Dirty Water")
                r = subprocess.run(["/usr/bin/curl", "http://192.168.2.178/apps/api/489/trigger?access_token=d45b8e96-30a9-4987-9fea-0936c4af7a28"], capture_output=True, text=True)
                dirty_water = True
        elif retcode == 98:
            logger.info("Pregame, longer sleep interval")
            sleep_time *= 10
        elif retcode == 99:
            logger.info("Game has ended, stopping polling")
        else:
            logger.error("Error sending")
        time.sleep(sleep_time)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, 
        format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
        level=logging.INFO)
    cli(auto_envvar_prefix='MARQUEE')