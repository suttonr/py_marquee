#!/usr/bin/env python3
import sys,os
import jmespath
import json
import click
import time
import secrets

import mlb

@click.group()
@click.option('-d', '--debug', default=False, is_flag=True)
@click.pass_context
def cli(ctx, debug):
    pass


@cli.command()
@click.option('-d', default=None, type=str, help='date')
@click.option('-f', default=None, type=str, help='team filter')
@click.pass_context
def get_schedule(ctx, f, d):
    sch = mlb.schedule(d, secrets.MLB_SCHEDULE_URL)

    for game in sch.get_games(f):
        print(f'{game.get("gameDate")}  {game.get("gamePk")}  {game.get("awayTeam")} vs {game.get("homeTeam")}')


if __name__ == '__main__':
    cli()