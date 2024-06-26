import requests
import json
import os
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

    def get_num_innings(self):
        return len(self.data["scoreboard"]["linescore"]["innings"])
    
    def get_count(self):
        return self.data["scoreboard"]["currentPlay"]["count"]

    def get_game_status(self,code_type="statusCode"):
        return self.data["scoreboard"]["status"].get(code_type, "")

    def get_game_date(self):
        iso_ts = self.data["scoreboard"]["datetime"]["dateTime"][:-1]
        return datetime.fromisoformat(iso_ts)
    
    def get_pitchers(self):
        return self.data["scoreboard"]["probablePitchers"]
    
    def get_batter(self):
        return self.data["scoreboard"]["currentPlay"]["matchup"]["batter"]


class player:
    def __init__(self, playerid, base_url=""):
        self.id = playerid
        self.base_url = base_url
        if playerid:
            try:
                with open(f'./cache/player_{self.id}.json') as json_data:
                    self.data = json.load(json_data)
            except FileNotFoundError:
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