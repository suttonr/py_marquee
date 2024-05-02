import requests

class game:
    def __init__(self, gamepak):
        self.gamepak = gamepak
        self.refresh()

    def refresh(self):
        res = requests.get(f"https://baseballsavant.mlb.com/gf?game_pk={self.gamepak}")
        res.raise_for_status()
        self.data = res.json()

    def get_teams(self):
        return { 
            "away" : self.data["scoreboard"]["teams"]["away"]["locationName"],
            "home" : self.data["scoreboard"]["teams"]["home"]["locationName"] 
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

