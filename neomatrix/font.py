font = [
    bytearray(b'\x00\x00\x00\x00\x00'), # 20
    bytearray(b'\x00\x00\x5f\x00\x00'), # 21 !
    bytearray(b'\x00\x07\x00\x07\x00'), # 22 "
    bytearray(b'\x14\x7f\x14\x7f\x14'), # 23 #
    bytearray(b'\x24\x2a\x7f\x2a\x12'), # 24 $
    bytearray(b'\x23\x13\x08\x64\x62'), # 25 %
    bytearray(b'\x36\x49\x55\x22\x50'), # 26 &
    bytearray(b'\x00\x05\x03\x00\x00'), # 27 '
    bytearray(b'\x00\x1c\x22\x41\x00'), # 28 (
    bytearray(b'\x00\x41\x22\x1c\x00'), # 29 )len
    bytearray(b'\x14\x08\x3e\x08\x14'), # 2a *
    bytearray(b'\x08\x08\x3e\x08\x08'), # 2b +
    bytearray(b'\x00\x50\x30\x00\x00'), # 2c ,
    bytearray(b'\x08\x08\x08\x08\x08'), # 2d -
    bytearray(b'\x00\x60\x60\x00\x00'), # 2e .
    bytearray(b'\x20\x10\x08\x04\x02'), # 2f /
    bytearray(b'\x3e\x51\x49\x45\x3e'), # 30 0
    bytearray(b'\x00\x42\x7f\x40\x00'), # 31 1
    bytearray(b'\x42\x61\x51\x49\x46'), # 32 2
    bytearray(b'\x21\x41\x45\x4b\x31'), # 33 3
    bytearray(b'\x18\x14\x12\x7f\x10'), # 34 4
    bytearray(b'\x27\x45\x45\x45\x39'), # 35 5
    bytearray(b'\x3c\x4a\x49\x49\x30'), # 36 6
    bytearray(b'\x01\x71\x09\x05\x03'), # 37 7
    bytearray(b'\x36\x49\x49\x49\x36'), # 38 8
    bytearray(b'\x06\x49\x49\x29\x1e'), # 39 9
    bytearray(b'\x00\x36\x36\x00\x00'), # 3a :
    bytearray(b'\x00\x56\x36\x00\x00'), # 3b ;
    bytearray(b'\x08\x14\x22\x41\x00'), # 3c <
    bytearray(b'\x11\x11\x11\x11\x11'), # 3d =
    bytearray(b'\x00\x41\x22\x14\x08'), # 3e >
    bytearray(b'\x02\x01\x51\x09\x06'), # 3f ?
    bytearray(b'\x32\x49\x79\x41\x3e'), # 40 @
    bytearray(b'\x7e\x11\x11\x11\x7e'), # 41 A
    bytearray(b'\x7f\x49\x49\x49\x36'), # 42 B
    bytearray(b'\x3e\x41\x41\x41\x22'), # 43 C
    bytearray(b'\x7f\x41\x41\x22\x1c'), # 44 D
    bytearray(b'\x7f\x49\x49\x49\x41'), # 45 E
    bytearray(b'\x7f\x09\x09\x09\x01'), # 46 F
    bytearray(b'\x3e\x41\x49\x49\x7a'), # 47 G
    bytearray(b'\x7f\x08\x08\x08\x7f'), # 48 H
    bytearray(b'\x00\x41\x7f\x41\x00'), # 49 I
    bytearray(b'\x20\x40\x41\x3f\x01'), # 4a J
    bytearray(b'\x7f\x08\x14\x22\x41'), # 4b K
    bytearray(b'\x7f\x40\x40\x40\x40'), # 4c L
    bytearray(b'\x7f\x02\x0c\x02\x7f'), # 4d M
    bytearray(b'\x7f\x04\x08\x10\x7f'), # 4e N
    bytearray(b'\x3e\x41\x41\x41\x3e'), # 4f O
    bytearray(b'\x7f\x09\x09\x09\x06'), # 50 P
    bytearray(b'\x3e\x41\x51\x21\x5e'), # 51 Q
    bytearray(b'\x7f\x09\x19\x29\x46'), # 52 R
    bytearray(b'\x46\x49\x49\x49\x31'), # 53 S
    bytearray(b'\x01\x01\x7f\x01\x01'), # 54 T
    bytearray(b'\x3f\x40\x40\x40\x3f'), # 55 U
    bytearray(b'\x1f\x20\x40\x20\x1f'), # 56 V
    bytearray(b'\x3f\x40\x38\x40\x3f'), # 57 W
    bytearray(b'\x63\x14\x08\x14\x63'), # 58 X
    bytearray(b'\x07\x08\x70\x08\x07'), # 59 Y
    bytearray(b'\x61\x51\x49\x45\x43'), # 5a Z
    bytearray(b'\x00\x7f\x41\x41\x00'), # 5b [
    bytearray(b'\x02\x04\x08\x10\x20'), # 5c ¥
    bytearray(b'\x00\x41\x41\x7f\x00'), # 5d ]
    bytearray(b'\x04\x02\x01\x02\x04'), # 5e ^
    bytearray(b'\x40\x40\x40\x40\x40'), # 5f _
    bytearray(b'\x00\x01\x02\x04\x00'), # 60 `
    bytearray(b'\x20\x54\x54\x54\x78'), # 61 a
    bytearray(b'\x7f\x48\x44\x44\x38'), # 62 b
    bytearray(b'\x38\x44\x44\x44\x20'), # 63 c
    bytearray(b'\x38\x44\x44\x48\x7f'), # 64 d
    bytearray(b'\x38\x54\x54\x54\x18'), # 65 e
    bytearray(b'\x08\x7e\x09\x01\x02'), # 66 f
    bytearray(b'\x0c\x52\x52\x52\x3e'), # 67 g
    bytearray(b'\x7f\x08\x04\x04\x78'), # 68 h
    bytearray(b'\x00\x44\x7d\x40\x00'), # 69 i
    bytearray(b'\x20\x40\x44\x3d\x00'), # 6a j
    bytearray(b'\x7f\x10\x28\x44\x00'), # 6b k
    bytearray(b'\x00\x41\x7f\x40\x00'), # 6c l
    bytearray(b'\x7c\x04\x18\x04\x78'), # 6d m
    bytearray(b'\x7c\x08\x04\x04\x78'), # 6e n
    bytearray(b'\x38\x44\x44\x44\x38'), # 6f o
    bytearray(b'\x7c\x14\x14\x14\x08'), # 70 p
    bytearray(b'\x08\x14\x14\x18\x7c'), # 71 q
    bytearray(b'\x7c\x08\x04\x04\x08'), # 72 r
    bytearray(b'\x48\x54\x54\x54\x20'), # 73 s
    bytearray(b'\x04\x3f\x44\x40\x20'), # 74 t
    bytearray(b'\x3c\x40\x40\x20\x7c'), # 75 u
    bytearray(b'\x1c\x20\x40\x20\x1c'), # 76 v
    bytearray(b'\x3c\x40\x30\x40\x3c'), # 77 w
    bytearray(b'\x44\x28\x10\x28\x44'), # 78 x
    bytearray(b'\x0c\x50\x50\x50\x3c'), # 79 y
    bytearray(b'\x44\x64\x54\x4c\x44'), # 7a z
    bytearray(b'\x00\x08\x36\x41\x00'), # 7b {
    bytearray(b'\x00\x00\x7f\x00\x00'), # 7c |
    bytearray(b'\x00\x41\x36\x08\x00'), # 7d }
    bytearray(b'\x10\x08\x08\x10\x08'), # 7e ←
    bytearray(b'\x78\x46\x41\x46\x78'), # 7f →
]

def draw_message(message):
    message_len=len(message)

    ret={}
    for letter_pos in range(message_len):
        offset = 1 + (letter_pos * 6)
        for x in range(len(font[0])):
            for y in range(8):
                if ((font[ord(message[letter_pos])-32][x] >> y) & 0x01):
                    ret[f"{x+offset:03d}{y:03d}"] = bytearray(b'\xff\x00\x00')
    return ret
