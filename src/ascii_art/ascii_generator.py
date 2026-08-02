"""Image -> ASCII text-image conversion (grayscale + character-density lookup)."""

import os
from PIL import Image

from ascii_art.paths import ensure_dir_and_join

# character size in points (symbol - 9x19)
SMS_SIZE = [12, 12]
RESULTS_DIR = "Results"

# characters ordered from darkest to lightest, used to represent grayscale values
CHARACTERS = ['$', '@', 'B', '%', '8', '&', 'W', 'M', '#', '*', 'o', 'a', 'h', 'k', 'b', 'd', 'p', 'q', 'w', 'm',
              'Z', 'O', '0', 'Q', 'L', 'C', 'J', 'U', 'Y', 'X', 'z', 'c', 'v', 'u', 'n', 'x', 'r', 'j', 'f', 't',
              '/', '\\', '|', '(', '1', '{', '[', '?', '-', '_', '+', '~', '<', 'i', '!', 'l', 'I', ';', ':', ',',
              '^', '`', '.', ' ']
GRAYSCALE_LEVELS = len(CHARACTERS)
GRAYSCALE_STEP = 256 // GRAYSCALE_LEVELS


def resolve_target_size(image, size):
    """Return (width, height) in text symbols for the requested size setting.

    "original" is floor-divided by the 9x19 symbol size, clamped to at least
    1x1 so a source image smaller than one symbol cell doesn't resolve to a
    0-sized target (Pillow's resize() raises on a zero width/height).
    """
    if size == "original":
        originwidth, originheight = image.size
        return max(originwidth // 9, 1), max(originheight // 19, 1)
    return size[0], size[1]


def pixel_to_character(pixel):
    """Map a single grayscale value (0-255) to its representative character."""
    index = min(pixel // GRAYSCALE_STEP, GRAYSCALE_LEVELS - 1)
    return CHARACTERS[index]


# byte translation table mapping grayscale value (0-255) -> character
_PIXEL_TRANSLATION_TABLE = bytes(ord(pixel_to_character(value)) for value in range(256))


def save_text_image(text_image, image_path):
    """Write text_image to RESULTS_DIR, named after image_path's base filename."""
    base_name, _extension = os.path.splitext(os.path.basename(image_path))
    filename = ensure_dir_and_join(RESULTS_DIR, base_name + " - ascii_image.txt")
    with open(filename, "w", encoding="utf-8") as file:
        file.write(text_image)
    return filename


def generator(downstate, image_path, size):
    """Convert the image at image_path into an ASCII text-image.

    Returns [text_image, width, height] where width/height are in text symbols.
    """
    image = Image.open(image_path)

    newwidth, newheight = resolve_target_size(image, size)
    image = image.resize((newwidth, newheight))

    # operation to convert image to field with gray scale value
    image = image.convert('L')

    # operation to assign a character to grayscale, mapped in C via translate()
    new_pixels = image.tobytes().translate(_PIXEL_TRANSLATION_TABLE).decode("ascii")

    # operation to create string of text image with lines
    text_image = [new_pixels[index:index + newwidth] for index in range(0, len(new_pixels), newwidth)]
    text_image = "\n".join(text_image)

    if downstate == 1:
        save_text_image(text_image, image_path)

    return [text_image, newwidth, newheight]
