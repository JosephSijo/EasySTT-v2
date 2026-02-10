import ctypes
import os
import platform

# Only import Windows-specific libraries if on Windows and available
win32gui = None
win32con = None
win32api = None

if platform.system() == "Windows":
    try:
        import win32gui
        import win32con
        import win32api
    except ImportError:
        print("[Win32] pywin32 not found. Run 'pip install pywin32' for premium UI features.")

def apply_window_masking(hwnd: int, radius: int = 20):
    """
    Applies a rounded rectangle region to the window.
    This creates the 'masked' look for corners.
    """
    if not win32gui:
        return

    try:
        # Get window dimensions
        rect = win32gui.GetWindowRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]

        # Create Rounded Rect Region (GDI)
        hrgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w, h, radius, radius)
        
        # Set the window region
        ctypes.windll.user32.SetWindowRgn(hwnd, hrgn, True)
    except Exception as e:
        print(f"[Win32] Failed to apply masking: {e}")

def enable_acrylic_effect(hwnd: int, theme: str = "dark"):
    """
    Enables the Acrylic backdrop effect using DWM (Desktop Window Manager).
    Note: Requires Windows 10 (1803+) or Windows 11.
    """
    if not win32gui:
        return

    try:
        # Set the DWM Blur behind
        # In modern Win11, Mica is preferred (DWMWA_SYSTEMBACKDROP_TYPE)
        # But for wider compat, we use ACCENT_ENABLE_BLURBEHIND logic via DwmSetWindowAttribute
        
        # DWMWA_USE_IMMERSIVE_DARK_MODE (Windows 10 1903+)
        intensity = 1 if theme == "dark" else 0
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(ctypes.c_int(intensity)), 4
        )
        
        # Rounded Corners (Windows 11 only)
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33
        # DWMWCP_ROUND = 2
        corner_pref = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(corner_pref), 4
        )
        
    except Exception as e:
        print(f"[Win32] Failed to enable acrylic/mica: {e}")

def set_window_shadow(hwnd: int, enabled: bool = True):
    """
    Enables standard system drop shadows for a frameless window.
    """
    if not win32gui:
        return

    try:
        if enabled:
            # CS_DROPSHADOW (0x00020000)
            # Use GetClassLongPtr if available (64-bit), fallback to GetClassLong (32-bit)
            get_class_long = getattr(win32gui, "GetClassLongPtr", getattr(win32gui, "GetClassLong", None))
            set_class_long = getattr(win32gui, "SetClassLongPtr", getattr(win32gui, "SetClassLong", None))
            
            if get_class_long and set_class_long:
                style = get_class_long(hwnd, win32con.GCL_STYLE)
                set_class_long(hwnd, win32con.GCL_STYLE, style | 0x00020000)
    except Exception as e:
        print(f"[Win32] Failed to set shadow: {e}")
