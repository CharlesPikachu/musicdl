# Theme Manager
"""
Manages theme state, persistence, and application.
"""

from typing import Dict, Optional
from PyQt6.QtCore import QSettings

from .presets import THEME_PRESETS, get_preset_names
from .stylesheet import generate_stylesheet
from .system_theme import get_default_theme_name


class ThemeManager:
    """
    Manages theme colors, presets, and persistence.
    
    Features:
    - Auto-detect Windows dark/light mode on first launch
    - Save/load user theme preferences
    - Apply theme presets or custom colors
    """
    
    # Key used to mark if user has set theme manually
    USER_THEME_SET_KEY = "user_theme_set"
    CURRENT_PRESET_KEY = "current_preset"
    
    def __init__(self):
        self.settings = QSettings("MusicDL", "Theme")
        self.colors: Dict[str, str] = {}
        self.current_preset: Optional[str] = None
        self._load()
    
    def _load(self):
        """Load theme from settings or auto-detect."""
        # Check if user has manually set a theme before
        user_set = self.settings.value(self.USER_THEME_SET_KEY, False, type=bool)
        
        if user_set:
            # Load user's saved preset or custom colors
            saved_preset = self.settings.value(self.CURRENT_PRESET_KEY, None)
            if saved_preset and saved_preset in THEME_PRESETS:
                self._apply_preset(saved_preset)
            else:
                # Load custom colors
                self._load_custom_colors()
        else:
            # First launch: auto-detect Windows theme
            default_preset = get_default_theme_name()
            self._apply_preset(default_preset)
    
    def _apply_preset(self, preset_name: str):
        """Apply a preset theme."""
        if preset_name in THEME_PRESETS:
            self.current_preset = preset_name
            self.colors = THEME_PRESETS[preset_name].copy()
    
    def _load_custom_colors(self):
        """Load custom colors from settings."""
        # Use classic_light as base
        base_preset = THEME_PRESETS.get('classic_light', {})
        self.colors = base_preset.copy()
        
        # Override with saved custom colors
        for key in self.colors.keys():
            if key == 'name':
                continue
            saved = self.settings.value(f"color_{key}")
            if saved:
                self.colors[key] = saved
        
        self.current_preset = None  # Custom
    
    def save(self):
        """Save current theme to settings."""
        self.settings.setValue(self.USER_THEME_SET_KEY, True)
        
        if self.current_preset:
            self.settings.setValue(self.CURRENT_PRESET_KEY, self.current_preset)
        else:
            # Save custom colors
            self.settings.setValue(self.CURRENT_PRESET_KEY, "")
            for key, value in self.colors.items():
                if key != 'name':
                    self.settings.setValue(f"color_{key}", value)
    
    def apply_preset(self, preset_name: str):
        """
        Apply a theme preset and save.
        
        Args:
            preset_name: Internal name of the preset (e.g., 'deep_space')
        """
        if preset_name in THEME_PRESETS:
            self._apply_preset(preset_name)
            self.save()
    
    def set_color(self, key: str, value: str):
        """Set a custom color value."""
        self.colors[key] = value
        self.current_preset = None  # Now using custom theme
    
    def get_color(self, key: str) -> str:
        """Get a color value by key."""
        return self.colors.get(key, '#888888')
    
    def get_log_color(self, level_name: str) -> str:
        """Get log color for a specific log level."""
        key = f"log_{level_name.lower()}"
        return self.colors.get(key, '#888888')
    
    def get_stylesheet(self) -> str:
        """Generate and return the QSS stylesheet."""
        return generate_stylesheet(self.colors)
    
    def get_current_preset_name(self) -> Optional[str]:
        """Get the current preset name or None if using custom."""
        return self.current_preset
    
    def get_current_display_name(self) -> str:
        """Get display name of current theme."""
        if self.current_preset and self.current_preset in THEME_PRESETS:
            return THEME_PRESETS[self.current_preset].get('name', self.current_preset)
        return "自定义 (Custom)"
    
    def reset_to_default(self):
        """Reset to system-detected default theme."""
        default_preset = get_default_theme_name()
        self.apply_preset(default_preset)
    
    @staticmethod
    def get_all_presets() -> Dict[str, str]:
        """Get all preset names and their display names."""
        return {key: preset['name'] for key, preset in THEME_PRESETS.items()}
