def foo():
    pass
class matrix():
    def __init__(self, width, height, np=None):
        self.width = width
        self.height = height
        self.np = np
        self.brightness = 1

        self.buffer = {}
        self.xoffset = 0
        self.yoffset = 0
    
    def xy2i(self,x,y):
        if ( x & 0x01 ):
            return self.height * (self.width - (x+1)) + (self.height-1-y)
        else:
            return self.height * (self.width - x) - (self.height-1-y+1)

    def scale_color(self, color, scale):
        ret = bytearray()
        for i in range(len(color)):
            ret += bytearray([int(color[i] * scale)])
        return ret
    
    def send_np(self, fgcolor, bgcolor, fill_background=False, write_np=True):
        if not fill_background:
            for k in self.buffer:
                if int(k[:3]) < self.width and int(k[3:]) < self.width:
                    self.np[self.xy2i(int(k[:3]),int(k[3:]))] = self.scale_color(self.buffer[k], self.brightness)
        else:
            for y in range(self.height):
                for x in range(self.width):
                    if f"{x:03d}{y:03d}" in self.buffer:
                        self.np[self.xy2i(x,y)] = self.scale_color(self.buffer[f"{x:03d}{y:03d}"], self.brightness)
                    else:
                        self.np[self.xy2i(x,y)] = bgcolor

        if write_np:
            self.np.write()

    def __repr__(self):
        for y in range(self.height):
            yloc = (y + self.yoffset) % self.height
            for x in range(self.width):
                xloc = (x + self.height) % self.width
                print( "x" if f"{xloc:03d}{yloc:03d}" in self.buffer else " ", end=" ")
            print(" ")
        return " "
                