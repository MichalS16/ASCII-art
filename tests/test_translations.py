"""
Unit tests for translations.py
"""

import unittest

from ascii_art.translations import ENGLISH, CZECH


class TranslationsTests(unittest.TestCase):
    def test_english_and_czech_have_the_same_keys(self):
        # both language dicts must define exactly the same set of keys, or a switch would show missing text
        self.assertEqual(set(ENGLISH.keys()), set(CZECH.keys()))

    def test_no_translation_value_is_empty(self):
        # no translation string is empty in either language
        for lang in (ENGLISH, CZECH):
            for key, value in lang.items():
                self.assertTrue(value, f"empty translation for key: {key}")


if __name__ == "__main__":
    unittest.main()
