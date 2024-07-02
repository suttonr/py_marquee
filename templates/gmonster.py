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
    inning = []

    def __init__(self, marquee):
        self.marquee = marquee
        for i in range(1,11):
            self.inning.append({
                "away" : box(lookup_box(i,0)),
                "home" : box(lookup_box(i,1))
            }) 
        self.draw_bmp("templates/img/green_monster_marquee_mask.bmp")

    #def __setattr__(self, name, value):
    #    self.__dict__[name] = value
    #    if name != "marquee":
    #        self.refresh(name)

    #def refresh(self, name):
    #    val = getattr(self, name, None)
    #    if type(val) is box:
    #        self.update_message_2(str(val.value), anchor=val.get_cord(), 
    #            fgcolor=val.fgcolor, bgcolor=val.bgcolor)
      
    def update_box(self, name, side, value="", fgcolor=bytearray(b'\xff\xff\xff'), 
                   bgcolor=bytearray(b'\x00\x00\x00'), index = 0):
        cur_val = getattr(self, name, None)
        if isinstance(cur_val, list):
            cur_val = cur_val[index]
        
        xoffset = 0
        yoffset = 1
        if len(str(value)) ==1:
            xoffset = 3

        if len(cur_val[side].value) > len(value):
            self.draw_box(cur_val[side].get_cord(), cur_val[side].h, cur_val[side].w, cur_val[side].bgcolor )

        if (cur_val[side].value != value or cur_val[side].fgcolor != fgcolor):
            cur_val[side].value = value
            cur_val[side].fgcolor = fgcolor
            self.update_message_2(
                str(cur_val[side].value), anchor=cur_val[side].get_cord(xoffset = xoffset, yoffset = yoffset), 
                fgcolor=cur_val[side].fgcolor, bgcolor=cur_val[side].bgcolor
            )

