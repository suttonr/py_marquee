import time
import math

def foo():
    pass
class matrix():
    def __init__(self, width, height, np=None, mode="NP", cs=None, xoffset=0, yoffset=0):
        self.width = width
        self.height = height
        self.np = np
        self.brightness = 1
        self.mode = mode
        self.cs = cs

        self.buffer = {}
        self.dirty_pixels = []
        self.xoffset = xoffset
        self.yoffset = yoffset
    
    def xy2i(self,x,y):
        if ( x & 0x01 ):
            return self.height * (self.width - (x+1)) + (self.height-1-y)
        else:
            return self.height * (self.width - x) - (self.height-1-y+1)

    def update(self, address, value):
        if address not in self.buffer or self.buffer[address] != value:
            self.buffer.update({address : value})
            self.dirty_pixels.append(address)

    def scale_color(self, color, scale):
        ret = bytearray()
        for i in range(len(color)):
            ret += bytearray([int(math.sqrt(color[i] * color[i] * (scale/2)))])
        return ret
    
    def write_pixel(self, address, color):
        if self.mode == "NP":
            self.np[address] = color
        elif self.mode == "SPI" or self.mode == "PYSPI":
            port = self.yoffset + ( self.xoffset * 1 )
            print(port, address)
            data_to_send = int(15).to_bytes(1,"big") + ((port << 9) | address).to_bytes(2,"big") + color[1:2] + color[0:1] + color[2:3]
            if self.mode == "SPI":
                self.cs(0)
                self.np.write( data_to_send )
            if self.mode == "PYSPI":
                self.np.xfer3( data_to_send, 48_000_000, 0, 8)
        

    def send_np(self, fgcolor, bgcolor, fill_background=False, write_np=True, dirty_only=True):
        if dirty_only:
            for address in self.dirty_pixels:
                if address in self.buffer.keys():
                    self.write_pixel( self.xy2i(int(address[:3]),int(address[3:])), 
                        self.scale_color(self.buffer[address], self.brightness)
                    )
                self.dirty_pixels.remove(address) if address in self.dirty_pixels else None
        elif not fill_background:
            for k in self.buffer:
                if int(k[:3]) < self.width and int(k[3:]) < self.width:
                    self.write_pixel( self.xy2i(int(k[:3]),int(k[3:])), 
                        self.scale_color(self.buffer[k], self.brightness)
                    )
        else:
            for y in range(self.height):
                for x in range(self.width):
                    address = f"{x:03d}{y:03d}"
                    if address in self.buffer:
                        self.write_pixel(self.xy2i(x,y), 
                            self.scale_color(self.buffer[address], self.brightness)
                        )
                    else:
                        self.write_pixel(self.xy2i(x,y), bgcolor)
                    self.dirty_pixels.remove(address) if address in self.dirty_pixels else None
        if write_np and self.mode == "NP":
            self.np.write()

    def __repr__(self):
        for y in range(self.height):
            yloc = (y + self.yoffset) % self.height
            for x in range(self.width):
                xloc = (x + self.height) % self.width
                print( "x" if f"{xloc:03d}{yloc:03d}" in self.buffer else " ", end=" ")
            print(" ")
        return " "
                
