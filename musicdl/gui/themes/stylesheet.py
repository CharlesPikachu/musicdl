# Modern QSS Stylesheet Generator
"""
Generates beautiful Qt stylesheets with modern aesthetics.
"""

from typing import Dict


def generate_stylesheet(colors: Dict[str, str]) -> str:
    """
    Generate a modern QSS stylesheet from color dictionary.
    
    Args:
        colors: Dictionary of color values from theme preset
        
    Returns:
        Complete QSS stylesheet string
    """
    c = colors
    
    # Get colors with defaults
    def get(key: str, default: str = '#888888') -> str:
        return c.get(key, default)
    
    qss = f"""
/* ========================================
   MusicDL Modern Theme
   Generated Stylesheet
   ======================================== */

/* === Base Styles === */
QWidget {{
    background-color: {get('window_bg')};
    color: {get('window_text')};
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {get('window_bg')};
}}

/* === Labels === */
QLabel {{
    background-color: transparent;
    color: {get('window_text')};
    padding: 2px;
}}

/* === Line Edits (Input Fields) === */
QLineEdit {{
    background-color: {get('input_bg')};
    color: {get('input_text')};
    border: 1px solid {get('border_color')};
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: {get('accent_color')};
    selection-color: {get('window_bg')};
}}

QLineEdit:focus {{
    border: 2px solid {get('accent_color')};
    padding: 7px 11px;
}}

QLineEdit:hover {{
    border-color: {get('accent_color')};
}}

QLineEdit:disabled {{
    background-color: {get('btn_bg')};
    color: {get('border_color')};
}}

/* === Text Edits (Log Area) === */
QTextEdit {{
    background-color: {get('input_bg')};
    color: {get('input_text')};
    border: 1px solid {get('border_color')};
    border-radius: 8px;
    padding: 8px;
    selection-background-color: {get('accent_color')};
}}

QTextEdit:focus {{
    border: 2px solid {get('accent_color')};
}}

/* === Buttons === */
QPushButton {{
    background-color: {get('btn_bg')};
    color: {get('btn_text')};
    border: 1px solid {get('border_color')};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 18px;
}}

QPushButton:hover {{
    background-color: {get('btn_hover')};
    border-color: {get('accent_color')};
}}

QPushButton:pressed {{
    background-color: {get('border_color')};
}}

QPushButton:disabled {{
    background-color: {get('btn_bg')};
    color: {get('border_color')};
    border-color: {get('border_color')};
}}

/* Primary/Accent Button (can be applied via setProperty) */
QPushButton[accent="true"] {{
    background-color: {get('btn_accent')};
    color: white;
    border: none;
}}

QPushButton[accent="true"]:hover {{
    background-color: {get('btn_accent_hover')};
}}

/* === Combo Boxes === */
QComboBox {{
    background-color: {get('input_bg')};
    color: {get('input_text')};
    border: 1px solid {get('border_color')};
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 100px;
}}

QComboBox:hover {{
    border-color: {get('accent_color')};
}}

QComboBox:focus {{
    border: 2px solid {get('accent_color')};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 24px;
    border: none;
}}

QComboBox::down-arrow {{
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: {get('input_bg')};
    color: {get('input_text')};
    border: 1px solid {get('border_color')};
    border-radius: 6px;
    selection-background-color: {get('table_selected')};
    selection-color: white;
    padding: 4px;
}}

/* === Group Boxes === */
QGroupBox {{
    background-color: transparent;
    border: 1px solid {get('border_color')};
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 0 8px;
    background-color: {get('window_bg')};
    color: {get('accent_color')};
}}

/* === Tables === */
QTableWidget {{
    background-color: {get('table_bg')};
    color: {get('table_text')};
    border: 1px solid {get('border_color')};
    border-radius: 8px;
    gridline-color: {get('border_color')};
    selection-background-color: {get('table_selected')};
    selection-color: white;
}}

QTableWidget::item {{
    padding: 8px;
    border: none;
}}

QTableWidget::item:alternate {{
    background-color: {get('table_alt_bg')};
}}

QTableWidget::item:selected {{
    background-color: {get('table_selected')};
    color: white;
}}

QTableWidget::item:hover {{
    background-color: {get('btn_hover')};
}}

/* Header View */
QHeaderView {{
    background-color: transparent;
}}

QHeaderView::section {{
    background-color: {get('btn_bg')};
    color: {get('btn_text')};
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid {get('border_color')};
    font-weight: 600;
}}

QHeaderView::section:hover {{
    background-color: {get('btn_hover')};
}}

QHeaderView::section:first {{
    border-top-left-radius: 8px;
}}

QHeaderView::section:last {{
    border-top-right-radius: 8px;
}}

/* === Check Boxes === */
QCheckBox {{
    color: {get('window_text')};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {get('border_color')};
    border-radius: 4px;
    background-color: {get('input_bg')};
}}

QCheckBox::indicator:hover {{
    border-color: {get('accent_color')};
}}

QCheckBox::indicator:checked {{
    background-color: {get('accent_color')};
    border-color: {get('accent_color')};
}}

/* === Scroll Areas === */
QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* === Scroll Bars === */
QScrollBar:vertical {{
    background-color: {get('scrollbar_bg')};
    width: 12px;
    margin: 4px 2px 4px 2px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {get('scrollbar_handle')};
    min-height: 30px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {get('accent_color')};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: {get('scrollbar_bg')};
    height: 12px;
    margin: 2px 4px 2px 4px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: {get('scrollbar_handle')};
    min-width: 30px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {get('accent_color')};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* === Splitter === */
QSplitter::handle {{
    background-color: {get('border_color')};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QSplitter::handle:hover {{
    background-color: {get('accent_color')};
}}

/* === Status Bar === */
QStatusBar {{
    background-color: {get('btn_bg')};
    color: {get('window_text')};
    border-top: 1px solid {get('border_color')};
    padding: 4px 8px;
}}

QStatusBar::item {{
    border: none;
}}

/* === Progress Bar === */
QProgressBar {{
    background-color: {get('btn_bg')};
    border: 1px solid {get('border_color')};
    border-radius: 6px;
    text-align: center;
    color: {get('window_text')};
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {get('accent_color')};
    border-radius: 5px;
}}

/* === Dialog Buttons === */
QDialogButtonBox {{
    button-layout: 0;
}}

QDialogButtonBox QPushButton {{
    min-width: 80px;
}}

/* === Message Box === */
QMessageBox {{
    background-color: {get('window_bg')};
}}

QMessageBox QLabel {{
    color: {get('window_text')};
}}

/* === Tool Tips === */
QToolTip {{
    background-color: {get('input_bg')};
    color: {get('input_text')};
    border: 1px solid {get('border_color')};
    border-radius: 4px;
    padding: 6px;
}}

/* === Frame === */
QFrame {{
    border: none;
}}

QFrame[frameShape="4"] {{
    background-color: {get('border_color')};
    max-height: 1px;
}}

QFrame[frameShape="5"] {{
    background-color: {get('border_color')};
    max-width: 1px;
}}
"""
    return qss
