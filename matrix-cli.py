import os
import click
from base64 import b64encode
from PIL import Image

@click.command()
@click.option('--file-name', default=None, help='File to send')
@click.option('--clear', default=False, is_flag=True,
              help='Clear display before sending')
@click.option('--debug', default=False, is_flag=True,
              help='Enable debug logging')
def send(clear, file_name, debug):
    """Sends a file to mqtt topic"""
    
    click.echo(f"File: {file_name}")
    im = Image.open(file_name)

    data = bytearray()
    for y in range(im.size[1]):
        for x in range(im.size[0]):
            if debug:
                print(y)
            if sum(im.getpixel((x,y))) > 0:
                data += bytearray([x,y] + list(im.getpixel((x,y))))
                if debug:
                    print(bytearray([x,y] + list(im.getpixel((x,y)))) )   
    if debug:
        print(data)
    print(b64encode(data))

if __name__ == '__main__':
    send()





#data = bytearray()
#for y in range(im.size[1]):
#    for x in range(im.size[0]):
#        print(x,y)
#        if y==x:
#            data += bytearray([x,y,128,128,128] )
#            print(x,y,"x")
#            #print(bytearray([x,y] + list(im.getpixel((x,im.size[1]-1-y)))) )         
#
#print(data)
#print(b64encode(data))