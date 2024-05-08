import requests
from datetime import datetime
class game:
    def __init__(self, gamepak, base_url=""):
        self.gamepak = gamepak
        self.base_url = base_url
        self.refresh()

    def refresh(self):
        res = requests.get(f"{self.base_url}{self.gamepak}/landing")
        res.raise_for_status()
        self.data = res.json()

    def get_teams(self):
        return { 
            "away" : self.data["awayTeam"]["name"]["default"],
            "home" : self.data["homeTeam"]["name"]["default"] 
        }

    def get_score(self):
        return {
            "home" : { "score" : self.data["homeTeam"]["score"],  "shots" : self.data["homeTeam"]["sog"], },
            "away" : { "score" : self.data["awayTeam"]["score"],  "shots" : self.data["awayTeam"]["sog"], }
        }
    
    def get_inning_score(self, inning_num):
        for inning in self.data["summary"]["linescore"]["byPeriod"]:
            if inning.get("periodDescriptor", {}).get("number", 0) == inning_num:
                return inning

    def get_current_inning(self):
        return ( self.data["periodDescriptor"]["number"] )

    def get_num_innings(self):
        return len(self.data["summary"]["linescore"]["byPeriod"])

    # def get_game_status(self,code_type="statusCode"):
    #     return self.data["scoreboard"]["status"].get(code_type, "")
# 
    # def get_game_date(self):
    #     iso_ts = self.data["scoreboard"]["datetime"]["dateTime"][:-1]
    #     return datetime.fromisoformat(iso_ts)


