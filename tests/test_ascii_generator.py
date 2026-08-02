"""
Unit tests for ascii_generator.py
"""

import os
import unittest

from PIL import Image

from ascii_art.ascii_generator import generator, pixel_to_character, resolve_target_size, save_text_image, CHARACTERS

from _tempcwd import IsolatedTempCwdMixin


def make_image(path, size=(20, 20), color=0):
    Image.new("L", size, color=color).save(path)


class ResolveTargetSizeTests(unittest.TestCase):
    def test_original_divides_by_symbol_dimensions(self):
        # "original" size divides the image's pixel dimensions by the 9x19 symbol size
        image = Image.new("L", (90, 190))
        self.assertEqual(resolve_target_size(image, "original"), (10, 10))

    def test_original_size_floors_non_divisible_dimensions(self):
        # 91x191 doesn't divide evenly by 9x19; result must floor-divide, not round or raise
        image = Image.new("L", (91, 191))
        self.assertEqual(resolve_target_size(image, "original"), (10, 10))

    def test_sms_size_is_fixed_12x12(self):
        # the SMS size setting always returns 12x12 regardless of the image's own dimensions
        image = Image.new("L", (500, 500))
        self.assertEqual(resolve_target_size(image, [12, 12]), (12, 12))

    def test_custom_size_is_passed_through(self):
        # an explicit [width, height] size is returned unchanged
        image = Image.new("L", (500, 500))
        self.assertEqual(resolve_target_size(image, [40, 30]), (40, 30))

    def test_original_size_clamps_tiny_images_to_at_least_one_symbol(self):
        # regression: a source image smaller than one 9x19 symbol cell used to
        # resolve to (0, 0), which crashes Pillow's resize() on a 0 dimension
        image = Image.new("L", (5, 5))
        self.assertEqual(resolve_target_size(image, "original"), (1, 1))


class PixelToCharacterTests(unittest.TestCase):
    def test_black_pixel_maps_to_darkest_character(self):
        # grayscale value 0 (black) maps to the first, darkest character
        self.assertEqual(pixel_to_character(0), CHARACTERS[0])

    def test_white_pixel_maps_to_lightest_character(self):
        # grayscale value 255 (white) maps to the last, lightest character
        self.assertEqual(pixel_to_character(255), CHARACTERS[-1])

    def test_all_grayscale_values_are_in_range(self):
        # every possible grayscale value (0-255) must map to some valid character
        for pixel in range(256):
            character = pixel_to_character(pixel)
            self.assertIn(character, CHARACTERS)


class GeneratorTests(IsolatedTempCwdMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.image_path = os.path.join(self.tmpdir, "test.png")
        make_image(self.image_path, size=(20, 20))

    def test_output_shape_matches_custom_size(self):
        # the generated text-image's line count and line length match the requested custom size
        text_image, width, height = generator(0, self.image_path, [5, 4])
        self.assertEqual(width, 5)
        self.assertEqual(height, 4)
        lines = text_image.split("\n")
        self.assertEqual(len(lines), 4)
        for line in lines:
            self.assertEqual(len(line), 5)

    def test_output_shape_matches_sms_size(self):
        # the generated text-image's shape matches the fixed 12x12 SMS size
        text_image, width, height = generator(0, self.image_path, [12, 12])
        self.assertEqual((width, height), (12, 12))
        self.assertEqual(len(text_image.split("\n")), 12)

    def test_black_image_uses_darkest_character(self):
        # an all-black source image produces only the darkest character
        text_image, _, _ = generator(0, self.image_path, [3, 3])
        self.assertTrue(all(ch == CHARACTERS[0] for ch in text_image if ch != "\n"))

    def test_white_image_uses_lightest_character(self):
        # an all-white source image produces only the lightest character
        make_image(self.image_path, size=(20, 20), color=255)
        text_image, _, _ = generator(0, self.image_path, [3, 3])
        self.assertTrue(all(ch == CHARACTERS[-1] for ch in text_image if ch != "\n"))

    def test_download_writes_file(self):
        # downstate=1 must write the generated text-image to Results/
        generator(1, self.image_path, [3, 3])
        expected = os.path.join("Results", "test - ascii_image.txt")
        self.assertTrue(os.path.isfile(expected))

    def test_no_download_when_downstate_not_one(self):
        # downstate=0 must not create the Results/ directory at all
        generator(0, self.image_path, [3, 3])
        self.assertFalse(os.path.isdir("Results"))

    def test_source_filename_without_extension_is_not_dropped(self):
        # regression: a source filename with no extension must not produce an empty base_name
        no_extension_path = os.path.join(self.tmpdir, "image")
        os.replace(self.image_path, no_extension_path)
        filename = save_text_image("some ascii text", no_extension_path)
        self.assertEqual(filename, os.path.join("Results", "image - ascii_image.txt"))
        self.assertTrue(os.path.isfile(filename))

    def test_original_size_on_tiny_image_does_not_crash(self):
        # regression: an image smaller than one 9x19 symbol cell used to crash
        # resize() with a 0 width/height; must now produce a 1x1 text-image
        make_image(self.image_path, size=(5, 5))
        text_image, width, height = generator(0, self.image_path, "original")
        self.assertEqual((width, height), (1, 1))
        self.assertEqual(text_image, "".join(ch for ch in text_image if ch != "\n"))


if __name__ == "__main__":
    unittest.main()
