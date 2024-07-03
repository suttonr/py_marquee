from .base import base

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

class box:
    def __init__(self, cord=(0,0), value="", h=9, w=9, fgcolor=bytearray(b'\xff\xff\xff'), bgcolor=bytearray(b'\x00\x20\x00')):
        self.x = cord[0]
        self.y = cord[1]
        self.h = h
        self.w = w
        self.value = value
        self.bgcolor = bgcolor
        self.fgcolor = fgcolor
    
    def set_values(self, cord=(0,0), value="", fgcolor=None, bgcolor=None):
        self.x = cord[0]
        self.y = cord[1]
        self.value = value
        self.bgcolor = bgcolor if bgcolor else self.bgcolor
        self.fgcolor = fgcolor if fgcolor else self.fgcolor

    def __eq__(self, other):
        return ( 
            self.value == other.value and 
            self.fgcolor == other.fgcolor and 
            self.bgcolor == other.bgcolor 
        )

    def get_cord(self, xoffset=0, yoffset=0):
        return (self.x + xoffset, self.y + yoffset) 


class gmonster(base):
    game_status = ""
    inning_status = ""
    current_inning = 0

    pitcher = { 
        "away" : box(lookup_box(0,0), w=11),
        "home" : box(lookup_box(0,1), w=11)
    }
    runs = { 
        "away" : box(lookup_box(11,0), w=10),
        "home" : box(lookup_box(11,1), w=10)
    }
    hits = { 
        "away" : box(lookup_box(12,0), w=10),
        "home" : box(lookup_box(12,1), w=10)
    }
    errors = { 
        "away" : box(lookup_box(13,0), w=10),
        "home" : box(lookup_box(13,1), w=10)
    }
    team = { 
        "away" : box((21,3), w=18),
        "home" : box((21,13), w=18)
    }
    message = { 
        "away" : box((325,3), w=122, bgcolor=bytearray(b'\x00\x64\x00')),
        "home" : box((325,13), w=122, bgcolor=bytearray(b'\x00\x64\x00'))
    }
    light = {
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

    inning = []

    def __init__(self, marquee):
        self.marquee = marquee
        for i in range(1,11):
            self.inning.append({
                "away" : box(lookup_box(i,0)),
                "home" : box(lookup_box(i,1))
            }) 
        self.display_mask()

    def display_mask(self):
        self.draw_bmp("templates/img/green_monster_marquee_mask.bmp")

    def display_rs_win(self):
        self.draw_bmp("templates/img/redsoxwin.bmp")

    #def __setattr__(self, name, value):
    #    self.__dict__[name] = value
    #    if name != "marquee":
    #        self.refresh(name)

    #def refresh(self, name):
    #    val = getattr(self, name, None)
    #    if type(val) is box:
    #        self.update_message_2(str(val.value), anchor=val.get_cord(), 
    #            fgcolor=val.fgcolor, bgcolor=val.bgcolor)
    # 
    def update_box(self, name, side, value=None, fgcolor=None, 
                   bgcolor=None, index = 0):
        cur_val = getattr(self, name, None)
        if isinstance(cur_val, list):
            cur_val = cur_val[index]
        
        xoffset = 0
        yoffset = 0
        if value is not None and len(str(value)) ==1:
            xoffset = 1

        if value is not None and len(cur_val[side].value) > len(value):
            self.draw_box(cur_val[side].get_cord(), cur_val[side].h, cur_val[side].w, cur_val[side].bgcolor )

        if ((value is not None and cur_val[side].value != value) or 
            (fgcolor is not None and cur_val[side].fgcolor != fgcolor)):
            cur_val[side].value = value if value is not None else cur_val[side].value
            cur_val[side].fgcolor = fgcolor if fgcolor is not None else cur_val[side].fgcolor
            self.update_message_2(
                str(cur_val[side].value).replace("0","O"), anchor=cur_val[side].get_cord(xoffset = xoffset, yoffset = yoffset), 
                fgcolor=cur_val[side].fgcolor, bgcolor=cur_val[side].bgcolor
            )

    def update_batter(self, at_bat):
        index = 0
        if len(str(at_bat)) > 1:
            self.draw_7seg_digit(at_bat[index])
            index += 1
        self.draw_7seg_digit(at_bat[index], x_offset=10)

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
        self.game_status = game_status
        for row,team in enumerate(("away", "home")):
            if ( game_status == "O" and 
                ( self.team[team].value == "BOS" and 
                    self.runs[team] >= self.runs["home"] and 
                    self.runs[team] >= self.runs["away"] )
                ):
                self.display_rs_win()


    def draw_light(self, cord, color=bytearray(b'\xff\xff\xff')):
        self.draw_box((cord[0],cord[1]+1), 4, 6, color)
        self.draw_box((cord[0]+1,cord[1]), 6, 4, color)

    def draw_7seg_digit(self, number, x_offset=0, y_offset=0, 
            fgcolor=bytearray(b'\xba\x99\x10'), bgcolor=bytearray(b'\x00\x00\x00')):
        seven_seg = {
            "a" : { "cord" : (201+x_offset, 11+y_offset), "h" : 1, "w" : 5 },
            "b" : { "cord" : (206+x_offset, 11+y_offset), "h" : 6, "w" : 1 },
            "c" : { "cord" : (206+x_offset, 17+y_offset), "h" : 6, "w" : 1 },
            "d" : { "cord" : (201+x_offset, 23+y_offset), "h" : 1, "w" : 5 },
            "e" : { "cord" : (201+x_offset, 17+y_offset), "h" : 6, "w" : 1 },
            "f" : { "cord" : (201+x_offset, 11+y_offset), "h" : 6, "w" : 1 },
            "g" : { "cord" : (201+x_offset, 17+y_offset), "h" : 1, "w" : 5 },
        }
        digit = {
            "1" : ["b", "c"],
            "2" : ["a", "b", "g", "e", "d"],
            "3" : ["a", "b", "c", "d", "g"],
            "4" : ["b", "c", "f", "g"],
            "5" : ["a", "c", "d", "f", "g"],
            "6" : ["a", "c", "d", "e", "f", "g"],
            "7" : ["a", "b", "c"],
            "8" : ["a", "b", "c", "d", "e", "f", "g"],
            "9" : ["a", "b", "c", "d", "f", "g"],
            "0" : ["a", "b", "c", "d", "e", "f"],
        }
        for seg,params in seven_seg.items():
            c = bgcolor
            if seg in digit[str(number)[0]]:
                c = fgcolor
            self.draw_box(**seven_seg[seg], color=c)
