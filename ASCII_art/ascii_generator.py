"""
Ascii-art generator section of ASCII_art program

How to ASCII generator: Please run "main.py" in current folder

created by: Michal S.
"""

# import modules
from PIL import Image

# function to generate ASCII text-image
def generator(downstate, image_path, size):
    image=Image.open(image_path)

    # operation to determine user size requirements
    if size=="original":
        originwidth, originheight=image.size
        newwidth=originwidth
        newheight=originheight
        size=[newwidth, newheight]
    elif size==[12, 12]:
        newwidth=12
        newheight=12
        image=image.resize((newwidth, int(newheight)))
    else:
        newwidth=size[0]
        newheight=size[1]
        image=image.resize((newwidth, int(newheight)))

    # operation to convert image to field with gray scale value
    image=image.convert('L')
    pixels=image.getdata()

    # operation to use optimal characters representation and assign to grayscale
    if size[0]<50 or size[1]<50:
        characters=['$', 'W', 'h', 'w', 'J', 'v', 'f', '1', '~', ';', " "]
        new_pixels=[characters[pixel//25] for pixel in pixels]
    else:
        characters=['$', '@', 'B', '%', '8', '&', 'W', 'M', '#', '*', 'o', 'a', 'h', 'k', 'b', 'd', 'p', 'q', 'w', 'm', 'Z', 'O', '0', 'Q', 'L', 'C', 'J', 'U', 'Y', 'X', 'z', 'c', 'v', 'u', 'n', 'x', 'r', 'j', 'f', 't', '/', '\\', '|', '(', '1', '{', '[', '?', '-', '_', '+', '~', '<', 'i', '!', 'l', 'I', ';', ':', ',', '^', '`', '.', ' ']
        new_pixels=[characters[pixel//4] for pixel in pixels]

    # operation to create string of text image with lines
    new_pixels=''.join(new_pixels)
    new_pixels_count=len(new_pixels)
    text_image=[new_pixels[index:index+newwidth] for index in range(0, new_pixels_count, newwidth)]
    text_image="\n".join(text_image) 

    # operation to download image
    if downstate==1:
        filename="Results-Výsledky/"+''.join(image_path.split("/")[-1].split(".")[:-1])+" - ascii_image.txt"
        with open(filename, "w") as file:
            file.write(text_image)

    # return image in textform
    return text_image