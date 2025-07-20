import requests
import json
import os
import time
from datetime import datetime

class game:
    def __init__(self, gamepak, base_url=""):
        self.gamepak = gamepak
        self.base_url = base_url
        self.refresh()

    def refresh(self):
        res = requests.get(f"{self.base_url}gf?game_pk={self.gamepak}")
        res.raise_for_status()
        self.data = res.json()

    def get_teams(self, short=False):
        name_type = "abbreviation" if short else "locationName"
        return { 
            "away" : self.data["scoreboard"]["teams"]["away"][name_type],
            "home" : self.data["scoreboard"]["teams"]["home"][name_type] 
        }

    def get_score(self):
        return self.data["scoreboard"]["linescore"]["teams"]
    
    def get_inning_score(self, inning_num):
        for inning in self.data["scoreboard"]["linescore"]["innings"]:
            if inning.get("num", 0) == inning_num:
                return inning

    def get_current_inning(self):
        return ( self.data["scoreboard"]["linescore"]["currentInning"], 
                 self.data["scoreboard"]["linescore"]["isTopInning"] )

    def get_inning_state(self):
        return self.data["scoreboard"]["linescore"]["inningState"]

    def get_num_innings(self):
        return len(self.data["scoreboard"]["linescore"]["innings"])
    
    def get_count(self):
        return self.data["scoreboard"]["currentPlay"]["count"]

    def get_game_status(self,code_type="statusCode"):
        return self.data["scoreboard"]["status"].get(code_type, "")

    def get_game_date(self):
        iso_ts = self.data["scoreboard"]["datetime"]["dateTime"][:-1]
        return datetime.fromisoformat(iso_ts)
    
    def get_pregame_pitchers(self):
        return self.data["scoreboard"]["probablePitchers"]
    
    def get_batter(self):
        return self.data["scoreboard"]["currentPlay"]["matchup"]["batter"]

    def is_play_complete(self):
        return self.data["scoreboard"]["currentPlay"]["about"]["isComplete"]
    
    def get_pitchers(self):
        try:
            ret = {
                "home" : self.data.get("home_pitcher_lineup",[None])[-1] ,
                "away" : self.data.get("away_pitcher_lineup",[None])[-1]
            }
        except IndexError:
            ret = {"home" : 0, "away" : 0}
        return ret
    
    def get_player_boxscore(self, id):
        print("id",id)
        return ( self.data["boxscore"]["teams"]["away"]["players"].get(f"ID{ id }",{}).get("stats",{}) or 
                 self.data["boxscore"]["teams"]["home"]["players"].get(f"ID{ id }",{}).get("stats",{}) )

    def get_player_season(self, id):
        print("id",id)
        return ( self.data["boxscore"]["teams"]["away"]["players"].get(f"ID{ id }",{}).get("seasonStats",{}) or 
                 self.data["boxscore"]["teams"]["home"]["players"].get(f"ID{ id }",{}).get("seasonStats",{}) )
    
    def get_bases(self):
        offense_keys = []
        try:
            offense_keys = self.data["scoreboard"]["linescore"]["offense"].keys()
        except ( IndexError, KeyError, AttributeError ):
            pass
        return offense_keys
    
    def get_last_play(self):
        last_play_cache = f'./cache/last_play.json'
        pre_last_play = {"play_id": None}
        try:
            with open(last_play_cache) as json_data:
                pre_last_play = json.load(json_data)
            if pre_last_play.get("game_pk","0") != str(self.gamepak):
                pre_last_play = {"play_id": None}
        except FileNotFoundError:
            pre_last_play = {"play_id": None}
        except AssertionError:
            pre_last_play = {"play_id": None}
        
        try:
            home_plays = [ p for p in self.data.get("team_home",[]) if p.get("result", None) ]
            away_plays = [ p for p in self.data.get("team_away",[]) if p.get("result", None) ]
            if len(home_plays) and len(away_plays):
                last_play = home_plays[-1] if home_plays[-1].get("ab_number",0) >= away_plays[-1].get("ab_number",0) else away_plays[-1]
            elif len(home_plays):
                last_play = home_plays[-1]
            else:
                last_play = away_plays[-1]
        except ( IndexError, KeyError, AttributeError ):
            return None
        
        if (last_play.get("play_id") != pre_last_play.get("play_id") and 
            last_play.get("game_total_pitches",0) > pre_last_play.get("game_total_pitches",0)):
            with open(last_play_cache, 'w') as f:
                json.dump(last_play, f)
            last_play.update({"new_play":True})
        return  last_play



class player:
    def __init__(self, playerid, base_url="", cache_age=600):
        self.id = playerid
        self.base_url = base_url
        self.cache_age = cache_age
        if playerid:
            player_cache = f'./cache/player_{self.id}.json'
            try:
                cache_seconds = time.time() - os.path.getmtime(player_cache)
                assert( cache_seconds < cache_age )
                with open(player_cache) as json_data:
                    self.data = json.load(json_data)
            except FileNotFoundError:
                self.refresh()
            except AssertionError:
                self.refresh()

    def refresh(self):
        print(f"fetching {self.id} from api")
        res = requests.get(f"{self.base_url}{self.id}")
        res.raise_for_status()
        self.data = res.json()
        with open(f'./cache/player_{self.id}.json', 'w') as f:
            json.dump(self.data, f)
    
    def get_player_number(self):
        try:
            num = self.data["people"][0]["primaryNumber"]
        except ( IndexError, KeyError ):
            num = "00"
        return num
    
class schedule:
    def __init__(self, date, base_url=""):
        self.date = date
        self.base_url = base_url
        if date:
            try:
                with open(f'./cache/schedule_{self.date}.json') as json_data:
                    self.data = json.load(json_data)
            except FileNotFoundError:
                self.refresh()

    def refresh(self):
        print(f"fetching schedule for {self.date} from api")
        res = requests.get(f"{self.base_url}{self.date}")
        res.raise_for_status()
        j = res.json()
        self.data = j if isinstance(j, dict) else {}
        with open(f'./cache/schedule_{self.date}.json', 'w') as f:
            json.dump(self.data, f)
    
    def get_games(self, team_filter=None):
        ret=[]
        for date in self.data.get("schedule",{}).get("dates",[]):
            for game in date.get("games", []):
                g = { 
                    "gameDate" : game.get("gameDate", ""),
                    "gamePk" : game.get("gamePk", ""),
                    "awayTeam" : game.get("teams", {}).get("away", {}).get("team", {}).get("name", ""),
                    "homeTeam" : game.get("teams", {}).get("home", {}).get("team", {}).get("name", ""),
                }
                if team_filter:
                    if team_filter in g["awayTeam"] or team_filter in g["homeTeam"]:
                       ret.append(g)
                else: 
                    ret.append(g)

        return ret