"""
Unit tests for display.py
"""

import unittest
from unittest.mock import patch

from ascii_art.display import monitor_work_area, geometry_fits_work_area, clamp_and_center_geometry


class MonitorWorkAreaTests(unittest.TestCase):
    def test_non_windows_returns_fallback_as_full_screen(self):
        # on non-Windows platforms, the fallback full-screen size is returned as-is
        with patch("ascii_art.display.platform.system", return_value="Linux"):
            result = monitor_work_area(12345, (1920, 1080))
        self.assertEqual(result, (0, 0, 1920, 1080))

    def test_windows_uses_monitor_work_area(self):
        # on Windows, the real work area (screen minus taskbar) is no larger than the fallback in either dimension
        with patch("ascii_art.display.platform.system", return_value="Windows"):
            result = monitor_work_area(1, (1920, 1080))
        self.assertLessEqual(result[2] - result[0], 1920)
        self.assertLessEqual(result[3] - result[1], 1080)

    def test_windows_falls_back_on_oserror(self):
        # if the Win32 MonitorFromWindow call fails, the fallback full-screen size is used
        with patch("ascii_art.display.platform.system", return_value="Windows"), \
             patch("ascii_art.display.ctypes.windll.user32.MonitorFromWindow", side_effect=OSError, create=True):
            result = monitor_work_area(2, (1920, 1080))
        self.assertEqual(result, (0, 0, 1920, 1080))

    def test_windows_falls_back_when_get_monitor_info_fails(self):
        # if GetMonitorInfoW reports failure (returns 0), the fallback full-screen size is used
        with patch("ascii_art.display.platform.system", return_value="Windows"), \
             patch("ascii_art.display.ctypes.windll.user32.GetMonitorInfoW", return_value=0, create=True):
            result = monitor_work_area(3, (1920, 1080))
        self.assertEqual(result, (0, 0, 1920, 1080))


class GeometryFitsWorkAreaTests(unittest.TestCase):
    def test_geometry_within_bounds_fits(self):
        # a window fully inside the work area fits
        self.assertTrue(geometry_fits_work_area(100, 100, 200, 200, (0, 0, 1920, 1080)))

    def test_geometry_extending_past_right_edge_does_not_fit(self):
        # a window extending past the work area's right edge does not fit
        self.assertFalse(geometry_fits_work_area(1900, 100, 200, 200, (0, 0, 1920, 1080)))

    def test_geometry_before_left_edge_does_not_fit(self):
        # a window positioned before the work area's left edge does not fit
        self.assertFalse(geometry_fits_work_area(-10, 100, 200, 200, (0, 0, 1920, 1080)))


class ClampAndCenterGeometryTests(unittest.TestCase):
    def test_geometry_smaller_than_work_area_is_centered_unchanged(self):
        # a size already within bounds is left unchanged and centered
        width, height, pos_x, pos_y = clamp_and_center_geometry(200, 100, (0, 0, 1920, 1080))
        self.assertEqual((width, height), (200, 100))
        self.assertEqual(pos_x, (1920 - 200) // 2)
        self.assertEqual(pos_y, (1080 - 100) // 2)

    def test_geometry_larger_than_work_area_is_clamped(self):
        # a size larger than the work area is clamped down to fit
        width, height, pos_x, pos_y = clamp_and_center_geometry(3000, 2000, (0, 0, 1920, 1080))
        self.assertEqual((width, height), (1920, 1080))
        self.assertEqual((pos_x, pos_y), (0, 0))

    def test_margin_shrinks_the_usable_area(self):
        # a margin reduces the effective work area the geometry is clamped into
        width, height, _pos_x, _pos_y = clamp_and_center_geometry(3000, 2000, (0, 0, 1920, 1080), margin=100)
        self.assertEqual((width, height), (1820, 980))

    def test_work_area_not_starting_at_origin_is_respected(self):
        # a work area offset from (0, 0) (e.g. a secondary monitor) positions/clamps relative to its own bounds
        width, height, pos_x, pos_y = clamp_and_center_geometry(200, 100, (1920, 0, 3840, 1080))
        self.assertEqual((width, height), (200, 100))
        self.assertEqual(pos_x, 1920 + (1920 - 200) // 2)
        self.assertEqual(pos_y, (1080 - 100) // 2)


if __name__ == "__main__":
    unittest.main()
