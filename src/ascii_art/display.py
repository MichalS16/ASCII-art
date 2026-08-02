"""
Monitor/window-geometry helpers shared by user_interface.py's window
positioning code (remembered main-window position, result-window sizing).

Kept separate from paths.py (filesystem-only concerns) since this is display
geometry, not path handling.
"""

import ctypes
import platform

if platform.system() == "Windows":  # pragma: no branch - CI runs on windows-latest only
    import ctypes.wintypes as wintypes

    # mirrors the Win32 MONITORINFO struct used by GetMonitorInfoW
    class _MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    _MONITOR_DEFAULTTONEAREST = 2


def monitor_work_area(window_id, fallback_size):
    """Return (left, top, right, bottom) of the usable work area (screen
    minus taskbar/docks) of the monitor nearest the given window.

    window_id is a native window handle, e.g. from Tk's winfo_id(). Falls
    back to (0, 0, *fallback_size) - the full screen, no taskbar awareness -
    on non-Windows platforms or if the Win32 call fails for any reason, so
    callers always get a usable result.
    """
    if platform.system() == "Windows":
        try:
            monitor = ctypes.windll.user32.MonitorFromWindow(wintypes.HWND(window_id), _MONITOR_DEFAULTTONEAREST)
            info = _MONITORINFO()
            info.cbSize = ctypes.sizeof(_MONITORINFO)
            if ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                work = info.rcWork
                return work.left, work.top, work.right, work.bottom
        except OSError:
            pass

    fallback_width, fallback_height = fallback_size
    return 0, 0, fallback_width, fallback_height


def geometry_fits_work_area(pos_x, pos_y, width, height, work_area):
    """Return True if a window of size (width, height) at (pos_x, pos_y)
    fits entirely within work_area (left, top, right, bottom)."""
    work_left, work_top, work_right, work_bottom = work_area
    return work_left <= pos_x and work_top <= pos_y and pos_x + width <= work_right and pos_y + height <= work_bottom


def clamp_and_center_geometry(width, height, work_area, margin=0):
    """Clamp (width, height) to fit within work_area (minus an optional
    margin on each axis) and return (width, height, pos_x, pos_y) centered
    within it.

    Used to size/position a window so it never opens larger than or outside
    the monitor's usable work area.
    """
    work_left, work_top, work_right, work_bottom = work_area
    work_width = work_right - work_left - margin
    work_height = work_bottom - work_top - margin

    width = min(width, work_width)
    height = min(height, work_height)

    pos_x = max(work_left, min(work_left + (work_right - work_left - width) // 2, work_right - width))
    pos_y = max(work_top, min(work_top + (work_bottom - work_top - height) // 2, work_bottom - height))

    return width, height, pos_x, pos_y
