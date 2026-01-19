from .fonts.font import font_5x8
#from ..marquee.marquee import marquee
from PIL import ImageFont
from PIL import Image

class box:
    def __init__(self, cord=(0,0), value="", h=8, w=8, fgcolor=bytearray(b'\xff\xff\xff'), bgcolor=bytearray(b'\x00\x20\x00')):
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

class base:
    marquee = None
    
    def __init__(self, marquee, brightness=1, clear=True):
        self.marquee = marquee
        if clear:
            self.marquee.set_brightness(brightness)
            self.marquee.clear()
    def __del__(self):
        # Cancel any active scroll animation
        if hasattr(self, '_scroll_callback') and self._scroll_callback:
            from animation_manager import unregister_animation
            unregister_animation(self._scroll_callback)
        print("base template destroyed")

    def process_raw(self, message):
        if ( (len(message) % 6) == 0 ):
            for m in range(0,len(message),6):
                self.marquee.set_pixel(message[m:m+6])
        else:
            print("Message error:", message)

    def update_message(self, message, anchor=(0,0), fgcolor=bytearray(b'\x00\x00\x00'), bgcolor=None):
        # Handle both string and bytearray inputs
        if isinstance(message, str):
            message_bytes = bytearray(message, encoding="utf-8")
        elif isinstance(message, bytearray):
            message_bytes = message
        else:
            message_bytes = bytearray(str(message), encoding="utf-8")

        for x,y,b in font_5x8(message_bytes, fgcolor=fgcolor):
            # Calculate final coordinates
            final_x = x + anchor[0]
            final_y = y + anchor[1]

            # Skip pixels that would be at negative coordinates (off-screen to the left/top)
            if final_x < 0 or final_y < 0:
                continue

            # For now, also skip pixels that might be too far right/bottom
            # The matrix system should handle this, but let's be safe
            self.marquee.set_pixel( final_x.to_bytes(2,"big") + final_y.to_bytes(1,"big") + b  )
    
    def update_message_2(self, message, fgcolor=bytearray(b'\x00\x00\x00'), bgcolor=None, font_size=16, anchor=(0,0)):
        font = ImageFont.truetype("templates/fonts/BitPotion.ttf",font_size)
        # print("Message2", message, fgcolor, bgcolor)
        message_bit = font.getmask(message)
        i=0
        if bgcolor == None:
            bgcolor = self.marquee.bgcolor

        for y in range(message_bit.size[1]):
            for x in range(message_bit.size[0]):
                # Calculate final coordinates
                final_x = x + anchor[0]
                final_y = y + anchor[1]

                # Skip pixels that would be at negative coordinates
                if final_x < 0 or final_y < 0:
                    i += 1
                    continue

                bit_color = fgcolor if message_bit[i] else bgcolor
                self.marquee.set_pixel( final_x.to_bytes(2,"big") + final_y.to_bytes(1,"big") + bit_color )
                i += 1

    def draw_box(self, cord, h, w, color):
        for x in range(cord[0], cord[0] + w):
            for y in range(cord[1], cord[1] + h):
                self.marquee.set_pixel( x.to_bytes(2,"big") +  y.to_bytes(1,"big") + color )

    def draw_diamond(self, cord, h, w, color):
        for x in range(w):
            for y in range(h):
                c = [ int(w/2), int(h/2) ]
                if abs(x - c[0]) + abs(y - c[1]) <= min(c):
                    self.marquee.set_pixel( (cord[0]+x).to_bytes(2,"big") +  (cord[1]+y).to_bytes(1,"big") + color )

    def draw_bmp(self, file_name="", x_offset=0, y_offset=0, x_start=0, y_start=0, x_end=0, y_end=0):
        im = Image.open(file_name)
        range_x_end = x_end if x_end else im.size[0]
        range_y_end = y_end if y_end else im.size[1]

        for y in range(y_start, range_y_end):
            for x in range(x_start, range_x_end):
                if sum(im.getpixel((x,y))) > 0:
                    data = bytearray()
                    data += (x+x_offset).to_bytes(2,"big") + (y+y_offset).to_bytes(1,"big")
                    data += bytearray(list(im.getpixel((x,y))))
                    self.process_raw(data)

    def draw_7seg_digit(self, number, x_offset=0, y_offset=0,
            fgcolor=bytearray(b'\xba\x99\x10'), bgcolor=bytearray(b'\x00\x00\x00')):
        seven_seg = {
            "a" : { "cord" : (x_offset, y_offset), "h" : 1, "w" : 5 },
            "b" : { "cord" : (5+x_offset, y_offset), "h" : 6, "w" : 1 },
            "c" : { "cord" : (5+x_offset, 6+y_offset), "h" : 7, "w" : 1 },
            "d" : { "cord" : (x_offset, 12+y_offset), "h" : 1, "w" : 5 },
            "e" : { "cord" : (x_offset, 6+y_offset), "h" : 7, "w" : 1 },
            "f" : { "cord" : (x_offset, y_offset), "h" : 6, "w" : 1 },
            "g" : { "cord" : (x_offset, 6+y_offset), "h" : 1, "w" : 5 },
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

    def scroll_text(self, text, speed=0.05, fgcolor=None, bgcolor=None, direction="left", loop=True, y_offset=0, font_size=16):
        """Scroll text horizontally across the matrix display using TrueType font.

        Args:
            text (str): Text to scroll
            speed (float): Seconds between animation frames (default: 0.05 for ~20 FPS)
            fgcolor (bytearray): Foreground color (default: class fgcolor)
            bgcolor (bytearray): Background color (default: class bgcolor)
            direction (str): "left" or "right" scrolling direction
            loop (bool): Whether to loop continuously (default: True)
            y_offset (int): Vertical offset for text position
            font_size (int): Font size for TrueType rendering (default: 16)
        """
        from animation_manager import unregister_animation

        # Cancel any existing scroll timer/animation
        if hasattr(self, '_scroll_callback') and self._scroll_callback:
            unregister_animation(self._scroll_callback)

        # Set default colors
        if fgcolor is None:
            fgcolor = self.marquee.fgcolor
        if bgcolor is None:
            bgcolor = self.marquee.bgcolor

        # Get font for width calculation
        font = ImageFont.truetype("templates/fonts/BitPotion.ttf", font_size)
        text_width = font.getbbox(text)[2]  # Get text width using font metrics

        # Get display width (assuming first matrix width, adjust if needed)
        display_width = 64  # Standard matrix width

        # Initialize scroll state
        if not hasattr(self, '_scroll_state'):
            self._scroll_state = {}

        scroll_id = id(text)  # Unique identifier for this scroll instance
        self._scroll_state[scroll_id] = {
            'position': display_width if direction == "left" else -text_width,
            'text': text,  # Store original string for update_message_2
            'speed': speed,
            'fgcolor': fgcolor,
            'bgcolor': bgcolor,
            'direction': direction,
            'loop': loop,
            'y_offset': y_offset,
            'font_size': font_size,
            'text_width': text_width,
            'display_width': display_width,
            'subpixel_accumulator': 0,  # Accumulate subpixel movement
            'pixel_step': 1,  # Move 1 pixel at a time for smooth visible motion
        }

        def scroll_frame(current_time):
            state = self._scroll_state.get(scroll_id)
            if not state:
                return  # Scroll was cancelled
            
            # Draw text at current position using TrueType font
            self.update_message_2(state['text'], fgcolor=state['fgcolor'], bgcolor=state['bgcolor'],
                                font_size=state['font_size'], anchor=(state['position'], state['y_offset']))

            # Update position
            if state['direction'] == "left":
                state['position'] -= 1
                # Check if text has scrolled completely off screen
                if state['position'] < -state['text_width']:
                    if state['loop']:
                        state['position'] = state['display_width']
                    else:
                        # Stop scrolling
                        if scroll_id in self._scroll_state:
                            del self._scroll_state[scroll_id]
                        unregister_animation(scroll_frame)
                        return
            else:  # right direction
                state['position'] += 1
                # Check if text has scrolled completely off screen
                if state['position'] > state['display_width']:
                    if state['loop']:
                        state['position'] = -state['text_width']
                    else:
                        # Stop scrolling
                        if scroll_id in self._scroll_state:
                            del self._scroll_state[scroll_id]
                        unregister_animation(scroll_frame)
                        return

        # Register with main loop instead of creating Timer thread
        self._scroll_callback = scroll_frame
        from animation_manager import register_animation
        register_animation(scroll_frame, speed)
