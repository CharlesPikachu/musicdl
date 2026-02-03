# Theme System Package
"""
Theme management system with presets and Windows dark mode detection.
"""

from .manager import ThemeManager
from .presets import THEME_PRESETS, get_preset_names
from .system_theme import is_windows_dark_mode, get_default_theme_name

__all__ = [
    'ThemeManager',
    'THEME_PRESETS',
    'get_preset_names',
    'is_windows_dark_mode',
    'get_default_theme_name'
]
