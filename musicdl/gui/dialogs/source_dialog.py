# Source Selection Dialog
"""
Dialog for selecting music sources.
"""

from typing import List, Set, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QScrollArea, QWidget, QGridLayout, QDialogButtonBox, QPushButton
)

# Import SUPPORTED_MUSIC_SOURCES
try:
    from musicdl import DEFAULT_MUSIC_SOURCES, SUPPORTED_MUSIC_SOURCES
except ImportError:
    try:
        from musicdl.musicdl import DEFAULT_MUSIC_SOURCES, SUPPORTED_MUSIC_SOURCES
    except ImportError:
        DEFAULT_MUSIC_SOURCES = []
        SUPPORTED_MUSIC_SOURCES = []


class SourceSelectionDialog(QDialog):
    """Dialog for selecting which music sources to use."""
    
    def __init__(self, parent=None, selected_sources: Optional[List[str]] = None):
        super().__init__(parent)
        self.setWindowTitle("选择音乐源")
        self.resize(520, 420)
        self.selected_sources: Set[str] = set(selected_sources) if selected_sources else set()
        self.checkboxes = {}
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("选择要启用的音乐源")
        header.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(header)
        
        # Scroll Area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        content_widget = QWidget()
        self.grid_layout = QGridLayout(content_widget)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        
        row, col = 0, 0
        sorted_sources = sorted(SUPPORTED_MUSIC_SOURCES)
        
        for source in sorted_sources:
            cb = QCheckBox(source.replace("MusicClient", ""))
            cb.setChecked(source in self.selected_sources)
            self.checkboxes[source] = cb
            self.grid_layout.addWidget(cb, row, col)
            
            col += 1
            if col >= 3:  # 3 columns
                col = 0
                row += 1
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, stretch=1)
        
        # Quick Action Buttons
        btn_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self._select_all)
        btn_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("全不选")
        select_none_btn.clicked.connect(self._select_none)
        btn_layout.addWidget(select_none_btn)
        
        select_default_btn = QPushButton("默认")
        select_default_btn.clicked.connect(self._select_default)
        btn_layout.addWidget(select_default_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Dialog Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _select_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)
    
    def _select_none(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)
    
    def _select_default(self):
        for source, cb in self.checkboxes.items():
            cb.setChecked(source in DEFAULT_MUSIC_SOURCES)
    
    def get_selected_sources(self) -> List[str]:
        """Get list of selected sources."""
        return [source for source, cb in self.checkboxes.items() if cb.isChecked()]
