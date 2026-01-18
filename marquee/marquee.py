
class marquee:
    fgcolor = bytearray(b'\x32\x00\x00')
    bgcolor = bytearray(b'\x00\x00\x00')
    matrices = []

    def __init__(self, matrices=[]):
        self.matrices = matrices
    
    def set_brightness(self, bright):
        for i in range(len(self.matrices)):
            #print("b",i,bright,bright/100)
            self.matrices[i].brightness = bright / 100

    def set_pixel(self, message):
        if ( len(message) == 6 ):
            # print(f"{message[0]:03d}{message[1]:03d} : {message[2]} {message[3]} {message[4]}")
            x = int.from_bytes(bytearray(message[0:2]), "big")
            y = int.from_bytes(bytearray(message[2:3]), "big")
            i = int( y / 8 )
            j = int( x / 64 )
            port = i + (j * 3)
            #print("matrix:", i, j, port, len(self.matrices), x, y)
            if ( port < len(self.matrices) ):
                #self.matrices[port].buffer.update({f"{(x-int(j*64)):03d}{(y-(i*8)):03d}" : (message[3],message[4],message[5])})
                self.matrices[port].update(f"{(x-int(j*64)):03d}{(y-(i*8)):03d}", (message[3],message[4],message[5]))
            else:
                print("Invalid Matric Index:", i, j, port, len(self.matrices) )

    def get_pixels(self):
        ret = []
        for i in range(len(self.matrices)):
            matrix_pixels = {}
            for k,v in self.matrices[i].buffer.items():
                #print(f'{i} {self.matrices[i].xoffset} {self.matrices[i].yoffset}')
                x = int(k[0:3]) + (self.matrices[i].xoffset * 64)
                y = int(k[3:6]) + (self.matrices[i].yoffset * 8)
                matrix_pixels.update( { f"{x:03d}{y:03d}": v } )
            ret.append(matrix_pixels)
        return ret

    def clear(self, index=None):
        print("clearing")
        if index == None:
            for i in range(len(self.matrices)):
                print("clearing",i)
                self.matrices[i].buffer={}
                self.matrices[i].dirty_pixels=[]
        else:
            self.matrices[index].buffer={}
            self.matrices[index].dirty_pixels=[]
        print("done",len(self.matrices))

    def dirty_matrices(self, refresh=False):
        ret = []
        for i in range(len(self.matrices)):
            if self.matrices[i].is_dirty():
                ret.append(i)
                if refresh:
                    self.matrices[i].send_np(
                        self.fgcolor, self.bgcolor, fill_background, False, dirty_only=True
                    )
        return ret


    def send(self, fill_background=False, dirty_only=True):
        for i in range(len(self.matrices)):
            if dirty_only == False:
                self.dirty_matrices(refresh=True)
            self.matrices[i].send_np(self.fgcolor, self.bgcolor, fill_background, False, dirty_only=dirty_only)

    def write(self):
        for i in range(len(self.matrices)):
            if self.matrices[i].mode == "NP":
                self.matrices[i].np.write()
