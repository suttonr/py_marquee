import requests
from datetime import datetime
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
import json
import time

gamma8 = [
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,
    1,  1,  1,  1,  1,  1,  1,  1,  1,  2,  2,  2,  2,  2,  2,  2,
    2,  3,  3,  3,  3,  3,  3,  3,  4,  4,  4,  4,  4,  5,  5,  5,
    5,  6,  6,  6,  6,  7,  7,  7,  7,  8,  8,  8,  9,  9,  9, 10,
   10, 10, 11, 11, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16,
   17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 24, 24, 25,
   25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 35, 36,
   37, 38, 39, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 50,
   51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68,
   69, 70, 72, 73, 74, 75, 77, 78, 79, 81, 82, 83, 85, 86, 87, 89,
   90, 92, 93, 95, 96, 98, 99,101,102,104,105,107,109,110,112,114,
  115,117,119,120,122,124,126,127,129,131,133,135,137,138,140,142,
  144,146,148,150,152,154,156,158,160,162,164,167,169,171,173,175,
  177,180,182,184,186,189,191,193,196,198,200,203,205,208,210,213,
  215,218,220,223,225,228,231,233,236,239,241,244,247,249,252,255 
]

class election:
    def __init__(self, base_url=""):
        self.base_url = base_url
        self.refresh()

    def refresh(self):
        res = requests.get(f"{self.base_url}/national_level_summary/file.json")
        print(res)
        res.raise_for_status()
        self.data = res.json()
        res = requests.get(f"{self.base_url}/hot_races/file.json")
        res.raise_for_status()
        self.hot_races = res.json()
    
    def get_percent_in(self):
        return self.data["percentIn"]
    
    def get_next_polls_close(self):
        return self.data["nextPollsClose"]
    
    def get_vote_counts(self):
        ret = {}
        for canidate in self.data["candidates"]:
            ret[canidate["partyCode"]] = canidate["votes"]["count"]
        return ret

    def get_vote_delegates(self):
        ret = {}
        for canidate in self.data["candidates"]:
            ret[canidate["partyCode"]] = canidate["delegates"]
        return ret
    
    def get_hot_races(self):
        ret = {}
        for race in self.hot_races:
            race_data = {
                "reporting" : race.get("precinctsReporting",0),
                "results" : {}
            }
            include_result = True
            for result in race.get("results", []):
                race_data["results"][result.get("partyCode","x")] = result.get("votes",{}).get("percentage",0)
                include_result = include_result and not result.get("isWinner",False)
            if include_result:
                ret[race.get("stateCode")] = race_data
        return ret


