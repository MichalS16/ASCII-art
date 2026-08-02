"""
Integration tests running the generator against the real sample images
kept in assets/, so those files stay exercised rather than being dead fixtures.
"""

import os
import unittest

from ascii_art.ascii_generator import generator

from _paths import ASSETS_DIR

ASSET_IMAGES = ["emoji-smiley.jpg", "red-character.png", "tree-strom.jpg", "color-gradient.png"]


class AssetFixtureTests(unittest.TestCase):
    def test_all_asset_images_exist(self):
        # every fixture file listed above must actually exist on disk
        for name in ASSET_IMAGES:
            self.assertTrue(os.path.isfile(os.path.join(ASSETS_DIR, name)), f"missing fixture: {name}")

    def test_generator_handles_each_asset_image(self):
        # each real sample image generates a correctly-shaped text-image at a custom size
        for name in ASSET_IMAGES:
            with self.subTest(image=name):
                image_path = os.path.join(ASSETS_DIR, name)
                text_image, width, height = generator(0, image_path, [20, 15])
                self.assertEqual(width, 20)
                self.assertEqual(height, 15)
                lines = text_image.split("\n")
                self.assertEqual(len(lines), 15)
                for line in lines:
                    self.assertEqual(len(line), 20)

    def test_generator_handles_original_size_for_each_asset_image(self):
        # each real sample image generates a non-empty text-image at its original size
        for name in ASSET_IMAGES:
            with self.subTest(image=name):
                image_path = os.path.join(ASSETS_DIR, name)
                text_image, width, height = generator(0, image_path, "original")
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)
                self.assertTrue(text_image)

    def test_color_gradient_produces_varied_characters(self):
        # a smooth color gradient produces more than one distinct character, covering the "colored images" case
        image_path = os.path.join(ASSETS_DIR, "color-gradient.png")
        text_image, _, _ = generator(0, image_path, [40, 40])
        unique_characters = set(text_image) - {"\n"}
        self.assertGreater(len(unique_characters), 1)


if __name__ == "__main__":
    unittest.main()
