import requests
import json
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from .base import base, box

class weather(base):
    def __init__(self, marquee, location = (42.850613,-71.506748), xoffset=421, yoffset=4, show_label=True, 
        fgcolor=bytearray(b'\xba\x99\x10'), bgcolor=bytearray(b'\x00\x00\x00'),
        label_color=bytearray(b'\xff\x00\x00'), clear=True):
        super().__init__(marquee, clear=clear)

        self.show_label = show_label
        self.xoffset = xoffset
        self.yoffset = yoffset
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor
        self.label_color = label_color
        self.temp = None
        self.forecast_hourly = None
        self.urls = None
        self.timer = None
        try:
            print("weather url", f"https://api.weather.gov/points/{location[0]},{location[1]}")
            res = requests.get(f"https://api.weather.gov/points/{location[0]},{location[1]}")
            res.raise_for_status()
            self.urls = res.json().get("properties", None)
        except Exception as e:
            print("failed to load urls",e)
        self.refresh()


    def __del__(self):
        if self.timer:
            print("weather timer cancel")
            self.timer.cancel()

    def refresh(self):
        try:
            print("Refreshing hourly forcast")
            res = requests.get(self.urls["forecastHourly"])
            res.raise_for_status()
            self.forecast_hourly = res.json()["properties"]
        except Exception as e:
            print("failed to load forecastHourly", e)
    
        if self.temp is None and len(self.forecast_hourly.get("periods", [])) > 1:
            self.temp = self.forecast_hourly.get("periods", [])[0].get("temperature", "--")
        
        # Refresh forcast every 30m
        self.timer = threading.Timer(60*30, self.refresh)
        self.timer.start()



    def temperature(self, temp):
        self.temp = int(float(temp))
    
    def display_forcast(self, interval="hourly", count=4, xoffset=270, yoffset=0,
            fgcolor=None, bgcolor=None):
        if self.forecast_hourly:
            forecast = self.forecast_hourly.get("periods", [])
        else:
            forecast = []
        if len(forecast) < count:
            return

        x = xoffset
        fg = fgcolor if fgcolor else self.label_color
        bg = bgcolor if bgcolor else self.bgcolor
        for period in forecast[2:count+2]:
            message = period.get("shortForecast", "NA").split(" ")[-1]
            self.update_message_2(message, fgcolor=fg, 
                bgcolor=bg, font_size=16, anchor=(x, yoffset))
            message = period.get("probabilityOfPrecipitation", {}).get("value","--")
            self.update_message_2(f"{str(message).rjust(2)}%", fgcolor=fg, 
                bgcolor=bg, font_size=16, anchor=(x+3, yoffset+9))
            message = period.get("startTime", "NA").split("T")[-1][:5]
            self.update_message_2(message, fgcolor=fg, 
                bgcolor=bg, font_size=16, anchor=(x, yoffset+16))
            x += 32

    
    def display_temperature(self, xoffset=421, yoffset=4,
            fgcolor=None, bgcolor=None):
        try:
            temp_message = f"{int(self.temp)}" #°
            offset = len(str(self.temp)) * 10
        except:
            temp_message = "NA"
            offset = 20
        
        fg = fgcolor if fgcolor else self.label_color
        bg = bgcolor if bgcolor else self.bgcolor

        self.update_message_2(temp_message, fgcolor=fg, 
            bgcolor=bg, font_size=32, anchor=(xoffset, yoffset))
        self.draw_box((xoffset + offset, yoffset), 4, 4, fg)
        self.draw_box((xoffset + offset + 1, yoffset+1), 2, 2, bg)



