# Theme Presets
"""
Modern theme presets for MusicDL GUI.
Each preset defines a complete color palette.
"""

from typing import Dict, List

# Theme preset definitions
THEME_PRESETS: Dict[str, Dict[str, str]] = {
    # Deep Space - Dark theme with tech blue accents
    'deep_space': {
        'name': '深空黑 (Deep Space)',
        'window_bg': '#0d1117',
        'window_text': '#c9d1d9',
        'input_bg': '#161b22',
        'input_text': '#c9d1d9',
        'btn_bg': '#21262d',
        'btn_text': '#c9d1d9',
        'btn_hover': '#30363d',
        'btn_accent': '#238636',
        'btn_accent_hover': '#2ea043',
        'table_bg': '#0d1117',
        'table_text': '#c9d1d9',
        'table_alt_bg': '#161b22',
        'table_selected': '#1f6feb',
        'border_color': '#30363d',
        'accent_color': '#58a6ff',
        'scrollbar_bg': '#161b22',
        'scrollbar_handle': '#30363d',
        'log_debug': '#8b949e',
        'log_info': '#58a6ff',
        'log_warning': '#d29922',
        'log_error': '#f85149',
        'log_system': '#a371f7',
    },
    
    # Aurora - Purple gradient, elegant modern
    'aurora': {
        'name': '极光紫 (Aurora)',
        'window_bg': '#1a1625',
        'window_text': '#e2d9f3',
        'input_bg': '#251f31',
        'input_text': '#e2d9f3',
        'btn_bg': '#352f44',
        'btn_text': '#e2d9f3',
        'btn_hover': '#4a4458',
        'btn_accent': '#8b5cf6',
        'btn_accent_hover': '#a78bfa',
        'table_bg': '#1a1625',
        'table_text': '#e2d9f3',
        'table_alt_bg': '#251f31',
        'table_selected': '#7c3aed',
        'border_color': '#4a4458',
        'accent_color': '#c4b5fd',
        'scrollbar_bg': '#251f31',
        'scrollbar_handle': '#4a4458',
        'log_debug': '#9ca3af',
        'log_info': '#c4b5fd',
        'log_warning': '#fbbf24',
        'log_error': '#f87171',
        'log_system': '#a78bfa',
    },
    
    # Forest - Natural green, eye-friendly
    'forest': {
        'name': '森林绿 (Forest)',
        'window_bg': '#1a2421',
        'window_text': '#d1e7dd',
        'input_bg': '#1e2d28',
        'input_text': '#d1e7dd',
        'btn_bg': '#2d4a3e',
        'btn_text': '#d1e7dd',
        'btn_hover': '#3d6b54',
        'btn_accent': '#198754',
        'btn_accent_hover': '#20c997',
        'table_bg': '#1a2421',
        'table_text': '#d1e7dd',
        'table_alt_bg': '#1e2d28',
        'table_selected': '#198754',
        'border_color': '#3d6b54',
        'accent_color': '#75b798',
        'scrollbar_bg': '#1e2d28',
        'scrollbar_handle': '#3d6b54',
        'log_debug': '#8fbc8f',
        'log_info': '#75b798',
        'log_warning': '#ffc107',
        'log_error': '#dc3545',
        'log_system': '#20c997',
    },
    
    # Rose Gold - Warm tones, refined luxury
    'rose_gold': {
        'name': '玫瑰金 (Rose Gold)',
        'window_bg': '#1f1a1a',
        'window_text': '#f5e6e8',
        'input_bg': '#2a2020',
        'input_text': '#f5e6e8',
        'btn_bg': '#3d2e30',
        'btn_text': '#f5e6e8',
        'btn_hover': '#5a4547',
        'btn_accent': '#b76e79',
        'btn_accent_hover': '#d4a5ab',
        'table_bg': '#1f1a1a',
        'table_text': '#f5e6e8',
        'table_alt_bg': '#2a2020',
        'table_selected': '#b76e79',
        'border_color': '#5a4547',
        'accent_color': '#d4a5ab',
        'scrollbar_bg': '#2a2020',
        'scrollbar_handle': '#5a4547',
        'log_debug': '#c9b1b1',
        'log_info': '#d4a5ab',
        'log_warning': '#f0ad4e',
        'log_error': '#e74c3c',
        'log_system': '#b76e79',
    },
    
    # Classic Light - Optimized light theme
    'classic_light': {
        'name': '经典浅色 (Classic Light)',
        'window_bg': '#f8f9fa',
        'window_text': '#212529',
        'input_bg': '#ffffff',
        'input_text': '#212529',
        'btn_bg': '#e9ecef',
        'btn_text': '#212529',
        'btn_hover': '#dee2e6',
        'btn_accent': '#0d6efd',
        'btn_accent_hover': '#0b5ed7',
        'table_bg': '#ffffff',
        'table_text': '#212529',
        'table_alt_bg': '#f8f9fa',
        'table_selected': '#0d6efd',
        'border_color': '#ced4da',
        'accent_color': '#0d6efd',
        'scrollbar_bg': '#e9ecef',
        'scrollbar_handle': '#adb5bd',
        'log_debug': '#6c757d',
        'log_info': '#0d6efd',
        'log_warning': '#fd7e14',
        'log_error': '#dc3545',
        'log_system': '#6f42c1',
    },
}


def get_preset_names() -> List[str]:
    """Get list of all preset internal names."""
    return list(THEME_PRESETS.keys())


def get_preset_display_names() -> Dict[str, str]:
    """Get mapping of internal names to display names."""
    return {key: preset['name'] for key, preset in THEME_PRESETS.items()}
