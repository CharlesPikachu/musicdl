# Theme Configuration Dialog
"""
Dialog for theme and appearance settings.
"""

from typing import Dict, Callable

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGridLayout, QDialogButtonBox,
    QColorDialog, QComboBox, QFrame
)
from PyQt6.QtGui import QColor

from ..themes import ThemeManager, THEME_PRESETS


class ThemeConfigDialog(QDialog):
    """Dialog for configuring theme and appearance settings."""
    
    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.tm = theme_manager
        self.temp_colors = theme_manager.colors.copy()
        self.current_preset = theme_manager.get_current_preset_name()
        
        self.setWindowTitle("外观设置")
        self.resize(480, 580)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # === Preset Selection Section ===
        preset_section = QWidget()
        preset_layout = QVBoxLayout(preset_section)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(8)
        
        preset_header = QLabel("主题预设")
        preset_header.setStyleSheet("font-size: 15px; font-weight: 600;")
        preset_layout.addWidget(preset_header)
        
        preset_row = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("自定义 (Custom)", "custom")
        for key, preset in THEME_PRESETS.items():
            self.preset_combo.addItem(preset['name'], key)
        
        # Set current selection
        if self.current_preset:
            index = self.preset_combo.findData(self.current_preset)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)
        
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_row.addWidget(self.preset_combo, stretch=1)
        
        apply_btn = QPushButton("应用预设")
        apply_btn.clicked.connect(self._apply_selected_preset)
        preset_row.addWidget(apply_btn)
        
        preset_layout.addLayout(preset_row)
        layout.addWidget(preset_section)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #ccc;")
        layout.addWidget(separator)
        
        # === Custom Colors Section ===
        colors_header = QLabel("自定义颜色")
        colors_header.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(colors_header)
        
        hint_label = QLabel("点击色块可自定义颜色，修改后预设将变为「自定义」")
        hint_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(hint_label)
        
        # Scroll Area for color pickers
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setSpacing(10)
        self.grid.setContentsMargins(8, 8, 8, 8)
        
        # Readable names for color keys
        self.labels_map = {
            "window_bg": "窗口背景",
            "window_text": "通用文字",
            "input_bg": "输入框背景",
            "input_text": "输入框文字",
            "btn_bg": "按钮背景",
            "btn_text": "按钮文字",
            "btn_hover": "按钮悬停",
            "btn_accent": "强调按钮",
            "table_bg": "表格背景",
            "table_text": "表格文字",
            "table_selected": "表格选中",
            "border_color": "边框颜色",
            "accent_color": "强调色",
            "log_debug": "日志 DEBUG",
            "log_info": "日志 INFO",
            "log_warning": "日志 WARNING",
            "log_error": "日志 ERROR",
            "log_system": "日志 SYSTEM"
        }
        
        self.btn_map: Dict[str, QPushButton] = {}
        
        # Group colors logically
        ui_keys = [k for k in self.temp_colors.keys() 
                   if not k.startswith('log_') and k != 'name']
        log_keys = [k for k in self.temp_colors.keys() if k.startswith('log_')]
        sorted_keys = ui_keys + log_keys
        
        row = 0
        for key in sorted_keys:
            if key not in self.labels_map:
                continue
                
            label_text = self.labels_map.get(key, key)
            self.grid.addWidget(QLabel(label_text), row, 0)
            
            btn = QPushButton()
            btn.setFixedSize(90, 28)
            self._update_btn_style(btn, self.temp_colors.get(key, '#888888'))
            btn.clicked.connect(lambda checked, k=key, b=btn: self._pick_color(k, b))
            
            self.grid.addWidget(btn, row, 1)
            self.btn_map[key] = btn
            row += 1
        
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)
        
        # Reset Button
        reset_layout = QHBoxLayout()
        reset_btn = QPushButton("恢复系统默认")
        reset_btn.clicked.connect(self._reset_to_system_default)
        reset_layout.addWidget(reset_btn)
        reset_layout.addStretch()
        layout.addLayout(reset_layout)
        
        # Dialog Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _update_btn_style(self, btn: QPushButton, color_str: str):
        """Update button to show the color."""
        # Determine text color based on brightness
        color = QColor(color_str)
        brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        text_color = "#000000" if brightness > 128 else "#ffffff"
        
        btn.setStyleSheet(f"""
            background-color: {color_str}; 
            color: {text_color};
            border: 1px solid #555; 
            border-radius: 4px;
            font-size: 11px;
        """)
        btn.setText(color_str)
    
    def _pick_color(self, key: str, btn: QPushButton):
        """Open color picker for a specific color."""
        curr_color = QColor(self.temp_colors.get(key, '#888888'))
        color = QColorDialog.getColor(curr_color, self, "选择颜色")
        if color.isValid():
            hex_color = color.name()
            self.temp_colors[key] = hex_color
            self._update_btn_style(btn, hex_color)
            # Mark as custom
            self.current_preset = None
            self.preset_combo.setCurrentIndex(0)  # "Custom"
    
    def _on_preset_changed(self, index: int):
        """Handle preset combo box change."""
        pass  # Just tracks selection, apply on button click
    
    def _apply_selected_preset(self):
        """Apply the selected preset."""
        preset_key = self.preset_combo.currentData()
        if preset_key and preset_key != "custom" and preset_key in THEME_PRESETS:
            self.current_preset = preset_key
            self.temp_colors = THEME_PRESETS[preset_key].copy()
            # Update all color buttons
            for key, btn in self.btn_map.items():
                if key in self.temp_colors:
                    self._update_btn_style(btn, self.temp_colors[key])
    
    def _reset_to_system_default(self):
        """Reset to system-detected default theme."""
        from ..themes import get_default_theme_name
        default_preset = get_default_theme_name()
        
        if default_preset in THEME_PRESETS:
            self.current_preset = default_preset
            self.temp_colors = THEME_PRESETS[default_preset].copy()
            
            # Update combo selection
            index = self.preset_combo.findData(default_preset)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)
            
            # Update color buttons
            for key, btn in self.btn_map.items():
                if key in self.temp_colors:
                    self._update_btn_style(btn, self.temp_colors[key])
    
    def get_colors(self) -> Dict[str, str]:
        """Get the configured colors."""
        return self.temp_colors
    
    def get_selected_preset(self):
        """Get the selected preset name or None for custom."""
        return self.current_preset
