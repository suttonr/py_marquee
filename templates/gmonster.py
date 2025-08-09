from datetime import datetime
from zoneinfo import ZoneInfo

from .base import base, box
from .clock import clock

def lookup_box(b, r, offset=0):
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
    if r == 0:
        y = 4
    elif r == 1:
        y = 14
    return ((x+offset) , y)

class gmonster(base):
    def __init__(self, marquee):
        #self.marquee = marquee
        super().__init__(marquee)
        self.game_status = ""
        self.inning_status = ""
        self.current_inning = 0
        self.disable_win = False
        self.disable_close = False
        self.clock = None
        self.hr = False
        self.bgcolor = bytearray(b'\x00\x64\x00')

        self.pitcher = { 
            "away" : box(lookup_box(0,0), w=10),
            "home" : box(lookup_box(0,1), w=10)
        }
        self.runs = { 
            "away" : box(lookup_box(11,0), w=10),
            "home" : box(lookup_box(11,1), w=10)
        }
        self.hits = { 
            "away" : box(lookup_box(12,0), w=10),
            "home" : box(lookup_box(12,1), w=10)
        }
        self.errors = { 
            "away" : box(lookup_box(13,0), w=10),
            "home" : box(lookup_box(13,1), w=10)
        }
        self.team = { 
            "away" : box((21,3), w=18),
            "home" : box((21,13), w=18)
        }
        self.message = { 
            "away" : box((325,3), w=122, bgcolor=bytearray(b'\x00\x64\x00')),
            "home" : box((325,13), w=122, bgcolor=bytearray(b'\x00\x64\x00'))
        }
        self.light = {
            "balls" : [ 
                box((232,15), fgcolor=bytearray(b'\x3f\xed\x7f'), bgcolor=bytearray(b'\x00\x00\x00')),
                box((240,15), fgcolor=bytearray(b'\x3f\xed\x7f'), bgcolor=bytearray(b'\x00\x00\x00')), 
                box((248,15), fgcolor=bytearray(b'\x3f\xed\x7f'), bgcolor=bytearray(b'\x00\x00\x00')), 
            ],
            "strikes" : [ 
                box((272,15), fgcolor=bytearray(b'\xff\x06\x2f'), bgcolor=bytearray(b'\x00\x00\x00')),
                box((280,15), fgcolor=bytearray(b'\xff\x06\x2f'), bgcolor=bytearray(b'\x00\x00\x00')), 
            ],
            "outs" : [ 
                box((305,15), fgcolor=bytearray(b'\xff\x06\x2f'), bgcolor=bytearray(b'\x00\x00\x00')),
                box((313,15), fgcolor=bytearray(b'\xff\x06\x2f'), bgcolor=bytearray(b'\x00\x00\x00')), 
            ]
        }
        self.bases = [ False, False, False ]

        self.inning = []
        for i in range(1,11):
            self.inning.append({
                "away" : box(lookup_box(i,0)),
                "home" : box(lookup_box(i,1))
            }) 
        self.display_mask()
    
    def __del__(self):
        print("gmonster template destroyed")

    def display_mask(self, x_start=0):
        self.draw_bmp("templates/img/green_monster_marquee_mask.bmp",x_start=x_start)

    def display_rs_win(self):
        self.draw_bmp("templates/img/redsoxwin.bmp")

    def display_hr(self):
        self.draw_bmp("templates/img/hr.bmp")
        self.hr = True
    
    def refresh_board(self):
        boxes = [
            "pitcher",
            "runs",
            "hits",
            "errors",
            "team",
        ]

        if self.hr:
            self.display_mask()
            self.hr = False
        
        for i, inning in enumerate(self.inning):
            for side,box in inning.items():
                self.update_box("inning", side, index=i, refresh=True)
        
        for box in boxes:
            for side in ("away", "home"):
                self.update_box(box, side, refresh=True)

    
    def display_pregram(self):
        dt = datetime.now(ZoneInfo("America/New_York"))
        t = dt.strftime("%b %e").upper()
        y = dt.strftime("%Y")
        self.update_box("inning", "away", value="", index=0)
        padding = int((11-len(t))/2) if len(t) <= 10 else 1
        for inning in range(padding, min(len(t)+padding,10)):
            self.update_box("inning", "away", value=str(t[inning-padding]), index=inning)
            if inning >= 3 and inning <= 6:
                self.update_box("inning", "home", value=str(y[inning-3]), index=inning)
        if self.clock is None:
            self.clock = clock(self.marquee, xoffset=400, yoffset=4, show_label=False,
                fgcolor=bytearray(b'\xff\xff\xff'), bgcolor=bytearray(b'\x00\x64\x00'),
                tz_list=['America/New_York'], clear=False )

    def update_box(self, name, side, value=None, fgcolor=None, 
                   bgcolor=None, index = 0, refresh=False):
        self.refresh_board()
        cur_val = getattr(self, name, None)
        if isinstance(cur_val, list):
            cur_val = cur_val[index]
        
        xoffset = 0
        yoffset = 0
        if value is not None and len(str(value)) ==1:
            xoffset = 1

        if ((value is not None and len(cur_val[side].value) > len(value)) or 
            (name =="message" and cur_val[side].value != value)):
            self.draw_box(cur_val[side].get_cord(), cur_val[side].h, cur_val[side].w, cur_val[side].bgcolor )

        if ((value is not None and cur_val[side].value != value) or 
            (fgcolor is not None and cur_val[side].fgcolor != fgcolor) or refresh):
            cur_val[side].value = value if value is not None else cur_val[side].value
            cur_val[side].fgcolor = fgcolor if fgcolor is not None else cur_val[side].fgcolor
            self.update_message_2(
                str(cur_val[side].value).replace("0","O"), anchor=cur_val[side].get_cord(xoffset = xoffset, yoffset = yoffset), 
                fgcolor=cur_val[side].fgcolor, bgcolor=cur_val[side].bgcolor
            )

        if ( name =="message" and 
             value == "HOME RUN" and 
              self.team[team].value == "BOS"):
            self.display_hr()

    def update_batter(self, at_bat):
        index = 0
        if len(str(at_bat)) > 1:
            self.draw_7seg_digit(at_bat[index], x_offset=201, y_offset=11)
            index += 1
        self.draw_7seg_digit(at_bat[index], x_offset=211, y_offset=11)

    def update_count(self, name, value):
        num_lights = len(self.light[name])
        for index in range(num_lights):
            self.update_light(name, index, index < int(value))

    def update_light(self, name, index=0, value=False):
        cur_val = self.light[name][index]
        if cur_val.value != value:
            color = cur_val.fgcolor if value else cur_val.bgcolor
            self.draw_light(cur_val.get_cord(), color )

    def update_current_inning(self, inning, inning_status=None):
        self.current_inning = inning
        if inning_status:
            self.inning_status = inning_status
        
        for index, inning in enumerate(self.inning):
            for row,team in enumerate(("away", "home")):
                if ( index == (int(self.current_inning) - 1) and 
                    (( self.inning_status == "Top" and team == "away") or
                    ( self.inning_status == "Bottom" and team == "home")) ):
                    self.update_box("inning", team, index=index, fgcolor=bytearray(b'\xff\xff\x00'))
                else:
                    self.update_box("inning", team, index=index, fgcolor=bytearray(b'\xff\xff\xff'))

    def update_game_status(self, game_status):
        pregame_statuses = ("S", "P", "PW", "PI", "PR")
        prev_status = self.game_status
        self.game_status = game_status

        if game_status in pregame_statuses:
            self.display_pregram()
            return

        if prev_status in pregame_statuses and game_status not in pregame_statuses:
            if self.clock is not None:
                self.clock.__del__()
                self.clock = None
                self.display_mask(x_start=325)
            for index, inning in enumerate(self.inning):
                for row,team in enumerate(("away", "home")):
                        self.update_box("inning", team, index=index, value="")

        for row,team in enumerate(("away", "home")):
            if ( not self.disable_win and ( self.game_status == "O" or self.game_status == "F" ) and 
                 self.team[team].value == "BOS" and 
                 int(self.runs[team].value) >= int(self.runs["home"].value) and 
                 int(self.runs[team].value) >= int(self.runs["away"].value)
                ):
                self.display_rs_win()

    def update_bases(self, first=None, second=None, third=None ):
        self.bases[0] = first if first is not None else self.bases[0]
        self.bases[1] = second if second is not None else self.bases[1]
        self.bases[2] = third if third is not None else self.bases[2]
        self.draw_bases((426,2), 23)

    def draw_light(self, cord, color=bytearray(b'\xff\xff\xff')):
        self.draw_box((cord[0],cord[1]+1), 4, 6, color)
        self.draw_box((cord[0]+1,cord[1]), 6, 4, color)

    def draw_bases(self, cord, width, color=bytearray(b'\xff\xff\x00')):
        w = int(width/2)
        iw = int(width*0.4)
        p = int(w*0.6)
        cords = [
            (cord[0]+w,cord[1]+iw),
            (cord[0]+p,cord[1]),
            (cord[0],cord[1]+iw),
        ]
        for i,c in enumerate(cords):
            base_color = color if self.bases[i] else self.bgcolor
            self.draw_diamond(c, int(iw+2), int(iw+2), (b'\x00\x00\x00'))
            self.draw_diamond(c, int(iw), int(iw), base_color)

