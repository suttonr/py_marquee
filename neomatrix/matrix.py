def foo():
    pass
class matrix():
    def __init__(self, width, height, np=None):
        self.width = width
        self.height = height
        self.np = np

        self.buffer = {}
        self.xoffset = 0
        self.yoffset = 0
    
    def xy2i(self,x,y):
        if ( x & 0x01 ):
            return self.height * (self.width - (x+1)) + y
        else:
            return self.height * (self.width - x) - (y+1)

    def send_np(self, fgcolor, bgcolor, write_np=True):
        for y in range(self.height):
            for x in range(self.width):
                if f"{x:03d}{y:03d}" in self.buffer:
                    self.np[self.xy2i(x,y)] = fgcolor
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
                