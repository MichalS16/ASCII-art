"""
Unit tests for main.py
"""

import unittest
from unittest.mock import patch

from ascii_art import main


class MainTests(unittest.TestCase):
    def test_main_calls_run(self):
        # the entry point delegates straight to user_interface.run()
        with patch("ascii_art.main.run") as mock_run:
            main.main()
            mock_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
