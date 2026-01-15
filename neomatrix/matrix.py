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

        # Precomputed constants for efficiency
        self.header = b'\x0f'
        self.spi_buffer = bytearray()
        self.brightness_factors = self._precompute_brightness_factors()
        self.xy2i_cache = {}  # Cache for xy2i calculations
    
    def xy2i(self,x,y):
        key = (x, y)
        if key not in self.xy2i_cache:
            if ( x & 0x01 ):
                result = self.height * (self.width - (x+1)) + (self.height-1-y)
            else:
                result = self.height * (self.width - x) - (self.height-1-y+1)
            self.xy2i_cache[key] = result
        return self.xy2i_cache[key]

    def update(self, address, value):
        if address not in self.buffer or self.buffer[address] != value:
            self.buffer.update({address : value})
            self.dirty_pixels.append(address)

    def _precompute_brightness_factors(self):
        """Precompute brightness scaling factors to avoid sqrt calculations"""
        factors = {}
        for brightness in range(101):  # 0.00 to 1.00
            scale = brightness / 100.0
            if scale == 1.0:
                factors[brightness] = None  # No scaling needed
            else:
                # Precompute the scaling factor: sqrt(scale/2)
                factors[brightness] = math.sqrt(scale / 2)
        return factors

    def scale_color(self, color, scale):
        brightness_key = int(scale * 100)
        factor = self.brightness_factors.get(brightness_key, self.brightness_factors[100])
        if factor is None:  # brightness = 1.0
            return color
        ret = bytearray()
        for i in range(len(color)):
            ret += bytearray([int(color[i] * factor)])
        return ret

    def construct_data(self, address, color):
        port = self.yoffset + (self.xoffset * 3)
        addr_part = ((port << 9) | address).to_bytes(2, "big")
        color_part = color[1:2] + color[0:1] + color[2:3]
        return self.header + addr_part + color_part
    
    def write_pixel(self, address, color):
        if self.mode == "NP":
            self.np[address] = color
        elif self.mode == "SPI" or self.mode == "PYSPI":
            port = self.yoffset + ( self.xoffset * 3 )
            data_to_send = int(15).to_bytes(1,"big") + ((port << 9) | address).to_bytes(2,"big") + color[1:2] + color[0:1] + color[2:3]
            if self.mode == "SPI":
                self.cs(0)
                self.np.write( data_to_send )
            if self.mode == "PYSPI":
                self.np.xfer3( data_to_send, 48_000_000, 0, 8)
        

    def send_np(self, fgcolor, bgcolor, fill_background=False, write_np=True, dirty_only=True):
        to_remove = set()
        chunk_data = bytearray()
        chunk_count = 0
        chunk_size = 16  # Send 16 pixels at a time (96 bytes)

        def send_chunk():
            nonlocal chunk_data, chunk_count
            if chunk_data:
                if self.mode == "SPI":
                    self.cs(0)
                    self.np.write(chunk_data)
                elif self.mode == "PYSPI":
                    self.np.xfer3(chunk_data, 48_000_000, 0, 8)
                chunk_data = bytearray()
                chunk_count = 0

        if dirty_only:
            for address in self.dirty_pixels:
                pixel_addr = self.xy2i(int(address[:3]), int(address[3:]))
                color = self.scale_color(self.buffer[address], self.brightness)
                if self.mode == "NP":
                    self.np[pixel_addr] = color
                else:  # SPI modes - send in chunks
                    data = self.construct_data(pixel_addr, color)
                    chunk_data += data
                    chunk_count += 1
                    if chunk_count >= chunk_size:
                        send_chunk()
                to_remove.add(address)
        elif not fill_background:
            for k in self.buffer:
                if int(k[:3]) < self.width and int(k[3:]) < self.width:
                    pixel_addr = self.xy2i(int(k[:3]), int(k[3:]))
                    color = self.scale_color(self.buffer[k], self.brightness)
                    if self.mode == "NP":
                        self.np[pixel_addr] = color
                    else:  # SPI modes - send in chunks
                        data = self.construct_data(pixel_addr, color)
                        chunk_data += data
                        chunk_count += 1
                        if chunk_count >= chunk_size:
                            send_chunk()
        else:
            for y in range(self.height):
                for x in range(self.width):
                    address = f"{x:03d}{y:03d}"
                    pixel_addr = self.xy2i(x, y)
                    if address in self.buffer:
                        color = self.scale_color(self.buffer[address], self.brightness)
                    else:
                        color = bgcolor
                    if self.mode == "NP":
                        self.np[pixel_addr] = color
                    else:  # SPI modes - send in chunks
                        data = self.construct_data(pixel_addr, color)
                        chunk_data += data
                        chunk_count += 1
                        if chunk_count >= chunk_size:
                            send_chunk()
                    if address in self.dirty_pixels:
                        to_remove.add(address)

        # Send any remaining chunk
        send_chunk()

        # Clean up dirty pixels
        for addr in to_remove:
            if addr in self.dirty_pixels:
                self.dirty_pixels.remove(addr)

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
