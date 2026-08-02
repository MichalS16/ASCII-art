"""
Unit tests for paths.py
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from ascii_art.paths import ensure_dir_and_join, open_with_default_app, package_file_path


class EnsureDirAndJoinTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def test_creates_missing_directory_and_joins_filename(self):
        # a nonexistent directory is created, then the filename is joined onto it
        dir_path = os.path.join(self.tmpdir, "nested")
        result = ensure_dir_and_join(dir_path, "file.txt")
        self.assertTrue(os.path.isdir(dir_path))
        self.assertEqual(result, os.path.join(dir_path, "file.txt"))

    def test_existing_directory_is_left_alone(self):
        # an already-existing directory is not recreated or modified
        result = ensure_dir_and_join(self.tmpdir, "file.txt")
        self.assertEqual(result, os.path.join(self.tmpdir, "file.txt"))


class PackageFilePathTests(unittest.TestCase):
    def test_joins_filename_next_to_given_file(self):
        # the filename is joined onto the directory of the given __file__, not the cwd
        result = package_file_path(__file__, "ReadMe.txt")
        self.assertEqual(result, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ReadMe.txt"))


class OpenWithDefaultAppTests(unittest.TestCase):
    def test_windows_uses_startfile(self):
        # on Windows, os.startfile is used to open the path
        with patch("ascii_art.paths.platform.system", return_value="Windows"), \
             patch("ascii_art.paths.os.startfile", create=True) as mock_startfile:
            open_with_default_app("C:\\file.txt")
        mock_startfile.assert_called_once_with("C:\\file.txt")

    def test_macos_uses_open(self):
        # on macOS, the "open" command is used to open the path
        with patch("ascii_art.paths.platform.system", return_value="Darwin"), \
             patch("ascii_art.paths.subprocess.Popen") as mock_popen:
            open_with_default_app("/tmp/file.txt")
        mock_popen.assert_called_once_with(["open", "/tmp/file.txt"])

    def test_linux_uses_xdg_open(self):
        # on Linux, "xdg-open" is used to open the path
        with patch("ascii_art.paths.platform.system", return_value="Linux"), \
             patch("ascii_art.paths.subprocess.Popen") as mock_popen:
            open_with_default_app("/tmp/file.txt")
        mock_popen.assert_called_once_with(["xdg-open", "/tmp/file.txt"])


if __name__ == "__main__":
    unittest.main()
