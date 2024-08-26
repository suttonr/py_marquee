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
    sch = mlb.schedule(date_str, secrets.MLB_SCHEDULE_URL)

    for game in sch.get_games(f):
        game_dt = datetime.fromisoformat(game.get("gameDate"))
        delta_to_game = game_dt - now
        print(f'{game.get("gameDate")}  {game.get("gamePk")}  {game.get("awayTeam")} vs {game.get("homeTeam")} in {delta_to_game}')
        if launch and len(sch.get_games(f)) == 1 and game_dt > now and delta_to_game < timedelta(hours=1):
            ctx.invoke(watch_mlb_game, game_pk=game.get("gamePk") )


@cli.command()
@click.option('-g','--game-pk', default=None, help='game pk')
@click.option('-i','--interval', default=30, type=int, help='interval to update')
@click.pass_context
def watch_mlb_game(ctx, game_pk, interval):
    logger.info(f"Started watching gp={game_pk}")
    retcode = 0
    while retcode == 0 or retcode == 98:
        result = subprocess.run(["python3", "matrix-cli.py", "send-mlb-game", "-g", str(game_pk)], capture_output=True, text=True)
        retcode = int(result.returncode)
        print("result:", retcode)
        for line in result.stdout.split('\n'):
            logger.info(line)
        for line in result.stderr.split("\n"):
            logger.error(line)
        if retcode == 0:
            logger.debug("Game is active")
            time.sleep(interval)
        elif retcode == 98:
            logger.info("Pregame, longer sleep interval")
            time.sleep(interval * 4)
        elif retcode == 99:
            logger.info("Game has ended, stopping polling")
        else:
            logger.error("Error sending")

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, 
        format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
        level=logging.INFO)
    cli(auto_envvar_prefix='MARQUEE')