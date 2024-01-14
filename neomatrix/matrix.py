def foo():
    pass
class matrix():
    def __init__(self, width, height, np=None):
        self.width = width
        self.height = height
        self.np = np

        self.buffer = {}
    
    def xy2i(self,x,y):
        if ( x & 0x01 ):
            return self.height * (self.width - (x+1)) + y
        else:
            return self.height * (self.width - x) - (y+1)

    def send_np(self, write_np=True):
        for y in range(self.height):
            for x in range(self.width):
                if f"{x:03d}{y:03d}" in self.buffer:
                    self.np[self.xy2i(x,y)] = (128,0,0)
                else:
                    self.np[self.xy2i(x,y)] = (0,0,0)

        if write_np:
            self.np.write()

    def __repr__(self):
        for y in range(self.height):
            for x in range(self.width):
                print( "x" if f"{x:03d}{y:03d}" in self.buffer else " ", end=" ")
            print(" ")
        return " "
                