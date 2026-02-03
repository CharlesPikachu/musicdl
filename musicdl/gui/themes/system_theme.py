# Windows System Theme Detection
"""
Detects Windows dark/light mode for automatic theme selection.
"""

import sys


def is_windows_dark_mode() -> bool:
    """
    Check if Windows is using dark mode.
    
    Returns:
        True if dark mode is enabled, False otherwise.
        Returns False on non-Windows systems.
    """
    if sys.platform != 'win32':
        return False
    
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0  # 0 = Dark Mode, 1 = Light Mode
    except Exception:
        return False


def get_default_theme_name() -> str:
    """
    Get the default theme name based on Windows color mode.
    
    Returns:
        'deep_space' for dark mode, 'classic_light' for light mode.
    """
    if is_windows_dark_mode():
        return 'deep_space'
    return 'classic_light'
