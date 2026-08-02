"""Shared path helpers for tests."""

import os

# Path to the `assets` directory, which contains test images and other files.
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
