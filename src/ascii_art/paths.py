"""
Generic filesystem path helpers shared by ascii_generator.py and ui_logic.py.

Kept in its own module (rather than owned by either) so neither of those two
domain-specific modules has to import a generic helper from the other.
"""

import os
import platform
import subprocess


def ensure_dir_and_join(dir_path, filename):
    """Create dir_path if missing and return the joined path."""
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, filename)


def package_file_path(package_file, filename):
    """Return the path to filename alongside the given __file__ of a package module."""
    return os.path.join(os.path.dirname(os.path.abspath(package_file)), filename)


def open_with_default_app(path):
    """Open path with the OS's default handler for its file type."""
    system = platform.system()
    if system == "Windows":
        os.startfile(path)
    elif system == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
