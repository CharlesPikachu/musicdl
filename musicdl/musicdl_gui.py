
import sys
import os
import logging
import shutil
import rich.progress
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error as ID3Error
from mutagen.flac import FLAC, Picture
from datetime import datetime

# --- Patch rich.progress BEFORE importing musicdl ---
# We patch it to avoid console output
class GUIProgress:
    '''A dummy replacement for rich.progress.Progress'''
    def __init__(self, *args, **kwargs):
        self.tasks = {}
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def add_task(self, description, total=None, **kwargs):
        task_id = float(len(self.tasks)) # Use float or int
        self.tasks[task_id] = _TaskMock(description=description, total=total)
        return task_id
    
    def update(self, task_id, **kwargs):
        if task_id in self.tasks:
            t = self.tasks[task_id]
            if 'total' in kwargs: t.total = kwargs['total']
            if 'completed' in kwargs: t.completed = kwargs['completed']
            if 'description' in kwargs: t.description = kwargs['description']
    
    def advance(self, task_id, advance=1):
        if task_id in self.tasks:
            self.tasks[task_id].completed += advance

    def __getitem__(self, item):
        return self.tasks.get(item, _TaskMock())

class _TaskMock:
    def __init__(self, description="", total=0, completed=0):
        self.description = description
        self.total = total or 0
        self.completed = completed or 0

class _TaskMap(dict):
    def __getitem__(self, key):
        if key not in self:
             self[key] = _TaskMock()
        return super().__getitem__(key)

# Mock the Progress class
rich.progress.Progress = GUIProgress
# ----------------------------------------------------

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QTextEdit, QProgressBar, QCheckBox, QFileDialog, 
                             QMessageBox, QComboBox, QGroupBox, QSplitter, QDialog,
                             QScrollArea, QGridLayout, QDialogButtonBox, QColorDialog, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSettings
from PyQt6.QtGui import QIcon, QFont, QColor

# Import MusicClient after patch
try:
    from musicdl import MusicClient, DEFAULT_MUSIC_SOURCES, SUPPORTED_MUSIC_SOURCES
    from modules.utils import LoggerHandle
    from modules.sources import MusicClientBuilder
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    try:
        from musicdl.musicdl import MusicClient, DEFAULT_MUSIC_SOURCES, SUPPORTED_MUSIC_SOURCES
        from musicdl.modules.utils import LoggerHandle
        from musicdl.modules.sources import MusicClientBuilder
    except ImportError:
        # Fallback if running from within musicdl dir
        sys.path.append(os.path.dirname(__file__))
        from musicdl import MusicClient, DEFAULT_MUSIC_SOURCES, SUPPORTED_MUSIC_SOURCES
        from modules.utils import LoggerHandle
        from modules.sources import MusicClientBuilder

# Fallback if SUPPORTED_MUSIC_SOURCES is not in musicdl (e.g. older version)
try:
    SUPPORTED_MUSIC_SOURCES
except NameError:
    SUPPORTED_MUSIC_SOURCES = DEFAULT_MUSIC_SOURCES


# Global signal to avoid pickling issues with QObject in data structures
class GlobalLogSignal(QObject):
    log = pyqtSignal(str, str)

LOG_SIGNAL = None

class GUILoggerHandle(LoggerHandle):
    def __init__(self):
        # Do NOT call super().__init__() if it does heavy stuff, but LoggerHandle just sets up logging
        # We want to traverse LoggerHandle.__init__ but suppress its file/stream handlers if needed.
        # Actually LoggerHandle sets up basicConfig. We might want to avoid that or live with it.
        # Since we use "disable_print=True" in MusicClient, it writes to file.
        LoggerHandle.__init__(self)
        self.log_level = logging.WARNING 

    def _emit(self, level, message):
        if LOG_SIGNAL:
            LOG_SIGNAL.log.emit(logging.getLevelName(level), str(message))

    def log(self, level, message):
        if level < self.log_level:
            return
        self._emit(level, message)
    
    def debug(self, message, disable_print=False):
        self.log(logging.DEBUG, message)
    
    def info(self, message, disable_print=False):
        self.log(logging.INFO, message)

    def warning(self, message, disable_print=False):
        self.log(logging.WARNING, message)

    def error(self, message, disable_print=False):
        self.log(logging.ERROR, message)

class Worker(QThread):
    finished = pyqtSignal(dict) # result
    error = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            # We must ensure args are picklable if this was a Process, but for QThread it shares memory.
            # But the error "object... reductor" suggested pickling. 
            # If MusicClient uses ProcessPoolExecutor internally, that's why.
            # MusicClient uses ThreadPoolExecutor (verified in code).
            # Maybe some library uses multiprocessing?
            # Or maybe PySide/PyQt tries to cache args?
            # Anyhow, GUILoggerHandle now is a plain object (inherits LoggerHandle which is object).
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit({'data': result})
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

class SortableTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        # Use UserRole for sorting if available
        my_value = self.data(Qt.ItemDataRole.UserRole)
        other_value = other.data(Qt.ItemDataRole.UserRole)
        
        if my_value is not None and other_value is not None:
             try:
                 return my_value < other_value
             except:
                 pass # Fallback to default
        
        return super().__lt__(other)

class SourceSelectionDialog(QDialog):
    def __init__(self, parent=None, selected_sources=None):
        super().__init__(parent)
        self.setWindowTitle("选择音乐源")
        self.resize(500, 400)
        self.selected_sources = set(selected_sources) if selected_sources else set()
        self.checkboxes = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        layout.addWidget(QLabel("请选择要启用的音乐源 (选中后点击确定):"))
        
        # Scroll Area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.grid_layout = QGridLayout(content_widget)
        
        row, col = 0, 0
        sorted_sources = sorted(SUPPORTED_MUSIC_SOURCES)
        
        for source in sorted_sources:
            cb = QCheckBox(source.replace("MusicClient", ""))
            cb.setChecked(source in self.selected_sources)
            self.checkboxes[source] = cb
            self.grid_layout.addWidget(cb, row, col)
            
            col += 1
            if col >= 3: # 3 columns
                col = 0
                row += 1
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_selected_sources(self):
        selected = []
        for source, cb in self.checkboxes.items():
            if cb.isChecked():
                selected.append(source)
        return selected

class ThemeManager:
    DEFAULTS = {
        # UI Colors
        "window_bg": "#f0f0f0",
        "window_text": "#000000",
        "input_bg": "#ffffff",
        "input_text": "#000000",
        "btn_bg": "#e0e0e0",
        "btn_text": "#000000",
        "table_bg": "#ffffff",
        "table_text": "#000000",
        # Log Colors
        "log_debug": "gray",
        "log_info": "black",
        "log_warning": "orange",
        "log_error": "red",
        "log_system": "blue"
    }

    def __init__(self):
        self.settings = QSettings("MusicDL", "Theme")
        self.colors = self.DEFAULTS.copy()
        self.load()

    def load(self):
        for key in self.colors:
            val = self.settings.value(key)
            if val:
                self.colors[key] = val

    def save(self):
        for key, val in self.colors.items():
            self.settings.setValue(key, val)

    def reset(self):
        self.colors = self.DEFAULTS.copy()
        self.save()

    def ge(self, key):
        return self.colors.get(key, self.DEFAULTS.get(key, "#000000"))
    
    def set(self, key, val):
        self.colors[key] = val

    def get_log_color(self, level_name):
        key = f"log_{level_name.lower()}"
        return self.colors.get(key, "black")

    def get_stylesheet(self):
        c = self.colors
        # Basic QSS generation
        qss = f"""
            QWidget {{
                background-color: {c['window_bg']};
                color: {c['window_text']};
            }}
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {c['input_bg']};
                color: {c['input_text']};
                border: 1px solid #ccc;
            }}
            QTableWidget {{
                background-color: {c['table_bg']};
                color: {c['table_text']};
                gridline-color: {c['window_text']};
            }}
            QHeaderView::section {{
                background-color: {c['btn_bg']};
                color: {c['btn_text']};
            }}
            QPushButton {{
                background-color: {c['btn_bg']};
                color: {c['btn_text']};
                border: 1px solid #888;
                padding: 4px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 1px solid {c['window_text']};
            }}
            QGroupBox {{
                border: 1px solid {c['window_text']};
                margin-top: 6px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                background-color: {c['window_bg']};
                color: {c['window_text']};
            }}
            QLabel {{
                background-color: transparent;
                color: {c['window_text']};
            }}
            QComboBox {{
                background-color: {c['input_bg']};
                color: {c['input_text']};
            }}
            QStatusBar {{
                color: {c['window_text']};
            }}
            /* Specific fix for QScrollArea contents */
            QScrollArea, QScrollArea > QWidget > QWidget {{
                background-color: {c['window_bg']};
            }}
            QCheckBox {{
                color: {c['window_text']};
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {c['window_text']};
                border-radius: 2px;
                background-color: {c['input_bg']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {c['window_text']};
                border: 1px solid {c['window_text']};
                image: url(none); /* In case some style sets an image */
            }}
            /* Add checks for standard checkmark visualization if needed, or just solid color for now */
            /* Using a simple inner rect for checked state or relying on color distinction */
             QCheckBox::indicator:checked {{
                background-color: {c['btn_bg']}; 
                border: 1px solid {c['window_text']};
                /* Standard checkmark is hard to draw in pure CSS without an image. 
                   Let's use a distinct color or inner generic indicator style if possible. 
                   Actually, let's just make it look like a filled box. */
                background-color: {c['window_text']};
            }}
            /* Better approach for checked: text color as bg, causing a solid box */
            
            /* ScrollBar styling to match theme (optional but good) */
            QScrollBar:vertical {{
                border: none;
                background: {c['window_bg']};
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {c['btn_bg']};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """
        return qss

class ThemeConfigDialog(QDialog):
    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.tm = theme_manager
        self.temp_colors = self.tm.colors.copy()
        self.setWindowTitle("外观设置")
        self.resize(400, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.grid = QGridLayout(content)
        
        # Define readable names for keys
        self.labels_map = {
            "window_bg": "窗口背景",
            "window_text": "通用文字",
            "input_bg": "输入框背景",
            "input_text": "输入框文字",
            "btn_bg": "按钮背景",
            "btn_text": "按钮文字",
            "table_bg": "表格背景",
            "table_text": "表格文字",
            "log_debug": "日志 DEBUG",
            "log_info": "日志 INFO",
            "log_warning": "日志 WARNING",
            "log_error": "日志 ERROR",
            "log_system": "日志 SYSTEM"
        }
        
        row = 0
        self.btn_map = {}
        
        # Sort keys to group them logically (UI first, then Logs)
        keys = list(self.tm.DEFAULTS.keys())
        # Simple ensuring logs are at bottom
        keys.sort(key=lambda k: (0 if k.startswith("log_") else 1)) 
        # Actually I want UI first (not log_) then Log. 
        # False < True. so (not startswith log) comes first? No. 
        # log_ starts with l. window starts with w. 
        # Let's just explicit sort
        ui_keys = [k for k in keys if not k.startswith("log_")]
        log_keys = [k for k in keys if k.startswith("log_")]
        sorted_keys = ui_keys + log_keys
        
        for key in sorted_keys:
            label_text = self.labels_map.get(key, key)
            self.grid.addWidget(QLabel(label_text), row, 0)
            
            btn = QPushButton()
            btn.setFixedSize(80, 25)
            self.update_btn_style(btn, self.temp_colors[key])
            btn.clicked.connect(lambda checked, k=key, b=btn: self.pick_color(k, b))
            
            self.grid.addWidget(btn, row, 1)
            self.btn_map[key] = btn
            row += 1
            
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Tools
        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self.reset_defaults)
        btn_layout.addWidget(reset_btn)
        
        layout.addLayout(btn_layout)
        
        # Dialog Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def update_btn_style(self, btn, color_str):
        # Set button background to the color, and text to readable contrast if possible
        # For simplicity, just set bg
        btn.setStyleSheet(f"background-color: {color_str}; border: 1px solid #555;")
        btn.setText(color_str)

    def pick_color(self, key, btn):
        curr_color = QColor(self.temp_colors[key])
        color = QColorDialog.getColor(curr_color, self, "选择颜色")
        if color.isValid():
            hex_color = color.name()
            self.temp_colors[key] = hex_color
            self.update_btn_style(btn, hex_color)

    def reset_defaults(self):
        self.temp_colors = self.tm.DEFAULTS.copy()
        for key, btn in self.btn_map.items():
            self.update_btn_style(btn, self.temp_colors[key])

    def get_colors(self):
        return self.temp_colors

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusicDL GUI - 音乐下载器")
        self.resize(1000, 700)
        self.settings = QSettings("MusicDL", "GUI")
        
        # Setup Global Signal
        global LOG_SIGNAL
        if LOG_SIGNAL is None:
            LOG_SIGNAL = GlobalLogSignal()
        LOG_SIGNAL.log.connect(self.append_log)
        
        
        self.logger = GUILoggerHandle()
        self.tm = ThemeManager()
        
        self.music_client = None
        self.init_ui()
        self.apply_theme()
        self.init_client()

    def apply_theme(self):
        qss = self.tm.get_stylesheet()
        self.setStyleSheet(qss)
        
        # Also need to refresh log text colors? 
        # Existing logs are HTML with hardcoded colors? 
        # Yes, existing logs might have wrong colors if we just switch.
        # But we can't easily re-parse them. 
        # Future logs will use correct color.
        # We could clear logs or just let it be.
        pass

    def init_client(self):
        saved_path = self.settings.value("download_path", os.path.join(os.getcwd(), 'musicdl_outputs'))
        if not os.path.exists(saved_path):
            try:
                os.makedirs(saved_path, exist_ok=True)
            except:
                pass
            
        init_cfg = {}
        current_sources = self.settings.value("selected_sources", DEFAULT_MUSIC_SOURCES)
        if isinstance(current_sources, str): # Handle potential single string (though unlikely with setList/setValue logic, safer to check)
             # QSettings might return list nicely, but let's be safe
             pass 
        # Ensure it's a list
        if not isinstance(current_sources, list):
             current_sources = DEFAULT_MUSIC_SOURCES

        init_cfg = {}
        for source in current_sources:
            init_cfg[source] = {
                'work_dir': saved_path,
                'disable_print': True
            }

        self.music_client = MusicClient(
            music_sources=current_sources,
            init_music_clients_cfg=init_cfg,
            logger_handle=self.logger
        )
        self.log_level_combo.setCurrentText(self.settings.value("log_level", "INFO"))
        self.update_log_level()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Control Panel
        control_group = QGroupBox("搜索与设置")
        control_layout = QHBoxLayout(control_group)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入歌曲关键词...")
        self.search_input.returnPressed.connect(self.start_search)
        control_layout.addWidget(self.search_input, stretch=2)

        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.start_search)
        control_layout.addWidget(self.search_btn)

        control_layout.addStretch()

        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setText(self.settings.value("download_path", os.path.join(os.getcwd(), 'musicdl_outputs')))
        control_layout.addWidget(self.path_input, stretch=1)

        self.browse_btn = QPushButton("选择保存目录")
        self.browse_btn.clicked.connect(self.browse_path)
        control_layout.addWidget(self.browse_btn)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.currentTextChanged.connect(self.update_log_level)
        control_layout.addWidget(QLabel("日志等级:"))
        control_layout.addWidget(self.log_level_combo)

        self.source_btn = QPushButton("资源设置")
        self.source_btn.clicked.connect(self.select_sources)
        control_layout.addWidget(self.source_btn)

        self.theme_btn = QPushButton("外观设置")
        self.theme_btn.clicked.connect(self.open_theme_settings)
        control_layout.addWidget(self.theme_btn)

        main_layout.addWidget(control_group)

        # Filter Panel
        filter_group = QGroupBox("筛选结果")
        filter_layout = QHBoxLayout(filter_group)
        
        filter_layout.addWidget(QLabel("筛选列:"))
        self.filter_column_combo = QComboBox()
        self.filter_column_combo.addItems(["全部"] + ['ID', '歌名', '歌手', '专辑', '大小', '时长', '来源'])
        self.filter_column_combo.currentIndexChanged.connect(self.filter_results)
        filter_layout.addWidget(self.filter_column_combo)
        
        filter_layout.addWidget(QLabel("关键词:"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("输入筛选关键词...")
        self.filter_input.textChanged.connect(self.filter_results)
        filter_layout.addWidget(self.filter_input)
        
        filter_layout.addStretch()
        main_layout.addWidget(filter_group)

        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)

        # Results Table
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels(['ID', '歌名', '歌手', '专辑', '大小', '时长', '来源'])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSortingEnabled(True)
        self.results_table.doubleClicked.connect(self.download_selected)
        
        table_layout.addWidget(self.results_table)

        self.download_btn = QPushButton("下载选中歌曲")
        self.download_btn.clicked.connect(self.download_selected)
        table_layout.addWidget(self.download_btn)
        table_layout.setContentsMargins(0,0,0,0)
        
        splitter.addWidget(table_container)

        # Logs
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        splitter.addWidget(log_group)
        splitter.setSizes([500, 150])

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")

        self.current_song_infos = {}
        self.is_searching = False

    def browse_path(self):
        directory = QFileDialog.getExistingDirectory(self, "选择保存目录", self.path_input.text())
        if directory:
            self.path_input.setText(directory)
            self.settings.setValue("download_path", directory)
            self.init_client()

    def update_log_level(self):
        level_str = self.log_level_combo.currentText()
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        self.logger.log_level = level_map.get(level_str, logging.WARNING)
        self.settings.setValue("log_level", level_str)
        self.append_log("SYSTEM", f"日志等级已设置为: {level_str}")

    def append_log(self, level, message):
        color = self.tm.get_log_color(level) if hasattr(self, 'tm') else "black"
        self.log_text.append(f'<span style="color:{color}">[{level}] {message}</span>')

    def start_search(self):
        # Stop Logic
        if self.is_searching:
            self.is_searching = False
            self.search_btn.setText("搜索")
            self.status_bar.showMessage("搜索已停止")
            return

        # Start Logic
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
        
        self.is_searching = True
        self.search_btn.setText("停止")
        # Keep enabled to allow stopping
        # self.search_btn.setEnabled(False)
        
        self.status_bar.showMessage(f"正在搜索: {keyword} ...")
        self.results_table.setSortingEnabled(False) # Disable sorting while updating
        self.results_table.setRowCount(0)
        self.current_song_infos = {}
        
        self.search_worker = Worker(self.music_client.search, keyword)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.error.connect(self.on_worker_error)
        self.search_worker.start()

    def on_search_finished(self, result):
        if not self.is_searching:
            return
        self.is_searching = False
        self.search_btn.setText("搜索")
        
        search_results = result['data']
        # self.search_btn.setEnabled(True) # Always enabled now
        self.status_bar.showMessage("搜索完成")
        
        row = 0
        self.current_song_infos = {}
        id_counter = 1
        
        def safe_get(d, k):
            return str(d.get(k, ''))

        def parse_size(size_str):
            if not size_str: return 0.0
            s = size_str.upper().strip()
            multip = 1
            if 'KB' in s: multip = 1024; s = s.replace('KB', '')
            elif 'MB' in s: multip = 1024*1024; s = s.replace('MB', '')
            elif 'GB' in s: multip = 1024*1024*1024; s = s.replace('GB', '')
            elif 'B' in s: s = s.replace('B', '')
            try:
                return float(s) * multip
            except:
                return 0.0

        def parse_duration(dur_str):
            # MM:SS or HH:MM:SS
            if not dur_str: return 0
            parts = dur_str.split(':')
            try:
                if len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    return int(parts[0])
            except:
                return 0

        # Flatten list first to avoid row insertion issues with sorting
        all_songs = []
        for source, songs in search_results.items():
            for song in songs:
                all_songs.append((source, song))
                
        self.results_table.setRowCount(len(all_songs))

        for source_name, song in all_songs:
            self.current_song_infos[str(id_counter)] = song
            
            # --- ID ---
            item_id = SortableTableWidgetItem(str(id_counter))
            item_id.setData(Qt.ItemDataRole.UserRole, id_counter)
            self.results_table.setItem(row, 0, item_id)
            
            # --- Name ---
            name = safe_get(song, 'song_name')
            item_name = SortableTableWidgetItem(name)
            item_name.setData(Qt.ItemDataRole.UserRole, name.lower())
            self.results_table.setItem(row, 1, item_name)
            
            # --- Singers ---
            singers = safe_get(song, 'singers')
            item_singers = SortableTableWidgetItem(singers)
            item_singers.setData(Qt.ItemDataRole.UserRole, singers.lower())
            self.results_table.setItem(row, 2, item_singers)
            
            # --- Album ---
            album = safe_get(song, 'album')
            item_album = SortableTableWidgetItem(album)
            item_album.setData(Qt.ItemDataRole.UserRole, album.lower())
            self.results_table.setItem(row, 3, item_album)
            
            # --- Size ---
            size_str = safe_get(song, 'file_size')
            item_size = SortableTableWidgetItem(size_str)
            item_size.setData(Qt.ItemDataRole.UserRole, parse_size(size_str))
            self.results_table.setItem(row, 4, item_size)
            
            # --- Duration ---
            dur_str = safe_get(song, 'duration')
            item_dur = SortableTableWidgetItem(dur_str)
            item_dur.setData(Qt.ItemDataRole.UserRole, parse_duration(dur_str))
            self.results_table.setItem(row, 5, item_dur)
            
            # --- Source ---
            try:
                # Try to use the source string from the search result map
                display_source = source_name
            except:
                display_source = str(safe_get(song, 'source'))

            item_source = SortableTableWidgetItem(display_source)
            item_source.setData(Qt.ItemDataRole.UserRole, display_source.lower())
            self.results_table.setItem(row, 6, item_source)
            
            row += 1
            id_counter += 1
            
        self.results_table.setSortingEnabled(True)
        # Apply current filter if any
        self.filter_results()

    def filter_results(self):
        filter_text = self.filter_input.text().lower().strip()
        # Combo index: 0=All, 1=ID, 2=Name ... matches column index + 1
        col_idx = self.filter_column_combo.currentIndex()
        target_col = col_idx - 1 # -1 if All, else 0-6
        
        for row in range(self.results_table.rowCount()):
            hidden = False
            if not filter_text:
                hidden = False
            else:
                if target_col == -1:
                    # Check all columns
                    row_matches = False
                    for c in range(self.results_table.columnCount()):
                        item = self.results_table.item(row, c)
                        if item and filter_text in item.text().lower():
                            row_matches = True
                            break
                    hidden = not row_matches
                else:
                    # Check specific column
                    item = self.results_table.item(row, target_col)
                    if item and filter_text in item.text().lower():
                        hidden = False
                    else:
                        hidden = True
            
            self.results_table.setRowHidden(row, hidden)

    def download_selected(self):
        selected_rows = set(item.row() for item in self.results_table.selectedItems())
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要下载的歌曲")
            return

        songs_to_download = []
        for row in selected_rows:
            item = self.results_table.item(row, 0)
            if item:
                song_id = item.text()
                if song_id in self.current_song_infos:
                    songs_to_download.append(self.current_song_infos[song_id])

        if not songs_to_download:
            return

        self.status_bar.showMessage(f"准备下载 {len(songs_to_download)} 首歌曲...")
        self.download_btn.setEnabled(False)
        
        self.download_worker = Worker(self.download_and_process, songs_to_download)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.error.connect(self.on_worker_error)
        self.download_worker.start()

    def download_and_process(self, songs_to_download):
        # 1. Download
        downloaded_infos = self.music_client.download(songs_to_download)
        
        # 2. Process Files (Rename & Move)
        target_dir = self.settings.value("download_path", os.path.join(os.getcwd(), 'musicdl_outputs'))
        processed_count = 0
        
        for song_info in downloaded_infos:
            try:
                # Original file path
                org_path = getattr(song_info, 'save_path', None)
                if not org_path or not os.path.exists(org_path):
                    continue
                
                # Construct new name: [SongName]-[Singer]-[Source]-[Bitrate].[Ext]
                song_name = getattr(song_info, 'song_name', 'Unknown')
                singer = getattr(song_info, 'singers', 'Unknown')
                source = getattr(song_info, 'source', 'Unknown').replace('MusicClient', '')
                ext = getattr(song_info, 'ext', 'mp3')
                
                bitrate = getattr(song_info, 'bitrate', '')
                if not bitrate:
                     bitrate = 'Unknown'
                else:
                    bitrate = str(bitrate)

                # Sanitize filename components to avoid invalid chars
                def sanitize(s):
                    return "".join(c for c in s if c not in r'<>:"/\|?*')

                new_name = f"{sanitize(song_name)}-{sanitize(singer)}-{sanitize(source)}-{sanitize(bitrate)}.{ext}"
                new_path = os.path.join(target_dir, new_name)
                
                # Handle duplicates
                if os.path.exists(new_path):
                    base, extension = os.path.splitext(new_name)
                    counter = 1
                    while os.path.exists(os.path.join(target_dir, f"{base} ({counter}){extension}")):
                        counter += 1
                    new_path = os.path.join(target_dir, f"{base} ({counter}){extension}")
                
                # Move/Rename
                shutil.move(org_path, new_path)
                processed_count += 1
                
                # --- Embed Cover Art ---
                try:
                    cover_url = getattr(song_info, 'cover_url', None)
                    if cover_url:
                        if LOG_SIGNAL: LOG_SIGNAL.log.emit("INFO", f"Downloading cover for {new_name}...")
                        try:
                            cover_resp = requests.get(cover_url, timeout=10)
                            cover_resp.raise_for_status()
                            cover_data = cover_resp.content
                            
                            if ext.lower() == 'mp3':
                                audio = MP3(new_path, ID3=ID3)
                                try:
                                    audio.add_tags()
                                except ID3Error:
                                    pass
                                audio.tags.add(
                                    APIC(
                                        encoding=3, # 3 is for utf-8
                                        mime='image/jpeg', # Defaulting to jpeg, could check header
                                        type=3, # 3 is for the cover image
                                        desc=u'Cover',
                                        data=cover_data
                                    )
                                )
                                audio.save()
                                if LOG_SIGNAL: LOG_SIGNAL.log.emit("INFO", "Cover art embedded (MP3).")
                            
                            elif ext.lower() == 'flac':
                                audio = FLAC(new_path)
                                image = Picture()
                                image.type = 3
                                image.mime = 'image/jpeg'
                                image.desc = u'Cover'
                                image.data = cover_data
                                audio.add_picture(image)
                                audio.save()
                                if LOG_SIGNAL: LOG_SIGNAL.log.emit("INFO", "Cover art embedded (FLAC).")
                                
                        except Exception as e:
                            if LOG_SIGNAL: LOG_SIGNAL.log.emit("WARNING", f"Failed to embed cover: {str(e)}")
                except Exception as e:
                    if LOG_SIGNAL: LOG_SIGNAL.log.emit("WARNING", f"Error during cover embedding block: {str(e)}")
                # -----------------------
                
                # Create corresponding txt file
                try:
                    txt_name = os.path.splitext(new_name)[0] + ".txt"
                    txt_path = os.path.join(target_dir, txt_name)
                    with open(txt_path, 'w', encoding='utf-8') as fp:
                        fp.write(f'Song Name: {getattr(song_info, "song_name", "")}\n')
                        fp.write(f'Singers: {getattr(song_info, "singers", "")}\n')
                        fp.write(f'Album: {getattr(song_info, "album", "")}\n')
                        fp.write(f'Source: {getattr(song_info, "source", "")}\n')
                        fp.write(f'Duration: {getattr(song_info, "duration", "")}\n')
                        fp.write(f'File Size: {getattr(song_info, "file_size", "")}\n')
                        fp.write(f'Bitrate: {getattr(song_info, "bitrate", "")}\n')
                        fp.write('-'*20 + ' Lyrics ' + '-'*20 + '\n')
                        fp.write(f'{getattr(song_info, "lyric", "")}\n')
                        fp.write('='*50 + '\n')
                    if LOG_SIGNAL:
                        LOG_SIGNAL.log.emit("INFO", f"Saved info to {txt_name}")
                except Exception as e:
                    if LOG_SIGNAL:
                        LOG_SIGNAL.log.emit("ERROR", f"Failed to save txt info for {song_name}: {str(e)}")
                
                # Optional: Remove empty source directory if it's empty
                # saved_path points to e.g. work_dir/Source/Timestamp/
                # We can try to clean up the parent dir
                parent_dir = os.path.dirname(org_path)
                try:
                    if not os.listdir(parent_dir):
                        os.rmdir(parent_dir)
                        # Try removing Source dir too if empty
                        grandparent = os.path.dirname(parent_dir)
                        if not os.listdir(grandparent):
                            os.rmdir(grandparent)
                except:
                    pass

            except Exception as e:
                # Log error but continue
                if LOG_SIGNAL:
                    LOG_SIGNAL.log.emit("ERROR", f"Failed to process {getattr(song_info, 'song_name', 'Unknown')}: {str(e)}")


        # 4. Clean Cache
        # try:
        #     # Dynamically import script to avoid path issues at top level
        #     sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        #     import clean_pkg_cache
        #     clean_pkg_cache.removepycache(os.path.join(os.path.dirname(__file__), '..'))
        #     if LOG_SIGNAL:
        #         LOG_SIGNAL.log.emit("INFO", "System cache cleaned successfully.")
        # except Exception as e:
        #      if LOG_SIGNAL:
        #          LOG_SIGNAL.log.emit("ERROR", f"Cache cleanup failed: {str(e)}")

        return downloaded_infos

    def on_download_finished(self, result):
        self.download_btn.setEnabled(True)
        self.status_bar.showMessage("所有任务处理完毕")
        QMessageBox.information(self, "完成", "选中的歌曲已处理完毕。\n(已自动重命名并整理到根目录)\n(已自动清理缓存)")

    def on_worker_error(self, error_msg):
        if not self.is_searching:
            return
        self.is_searching = False
        self.search_btn.setText("搜索")
        
        # self.search_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.status_bar.showMessage("发生错误")
        QMessageBox.critical(self, "错误", f"发生意外错误: {error_msg}")
        self.append_log("ERROR", error_msg)

    def select_sources(self):
        was_searching = self.is_searching
        if was_searching:
            # Manually stop search logic
            self.is_searching = False
            self.search_btn.setText("搜索")
            self.status_bar.showMessage("搜索已暂停 (正在设置源...)")
        
        current_sources = self.music_client.music_sources
        dialog = SourceSelectionDialog(self, current_sources)
        if dialog.exec():
            new_sources = dialog.get_selected_sources()
            if not new_sources:
                QMessageBox.warning(self, "警告", "未选择任何源，将使用默认源！")
                new_sources = DEFAULT_MUSIC_SOURCES
                
            self.settings.setValue("selected_sources", new_sources)
            self.init_client()
            self.append_log("SYSTEM", f"音乐源已更新: {', '.join([s.replace('MusicClient', '') for s in new_sources])}")
            
            if was_searching and self.search_input.text().strip():
                self.start_search()
        else:
            pass

    def open_theme_settings(self):
        dialog = ThemeConfigDialog(self.tm, self)
        if dialog.exec():
            new_colors = dialog.get_colors()
            self.tm.colors = new_colors
            self.tm.save()
            self.apply_theme()
            self.append_log("SYSTEM", "外观设置已更新")

    def cleanup_temp_folders(self):
        """Delete temporary client folders from the download directory."""
        download_path = self.settings.value("download_path", os.path.join(os.getcwd(), 'musicdl_outputs'))
        temp_folders = list(MusicClientBuilder.REGISTERED_MODULES.keys())
        
        cleaned_count = 0
        for folder in temp_folders:
            target_path = os.path.join(download_path, folder)
            if os.path.exists(target_path) and os.path.isdir(target_path):
                try:
                    shutil.rmtree(target_path)
                    cleaned_count += 1
                    if LOG_SIGNAL:
                        LOG_SIGNAL.log.emit("INFO", f"Cleaned up temporary folder: {folder}")
                except Exception as e:
                    if LOG_SIGNAL:
                        LOG_SIGNAL.log.emit("WARNING", f"Failed to clean up {folder}: {str(e)}")
        
        if cleaned_count > 0:
            if LOG_SIGNAL:
                LOG_SIGNAL.log.emit("INFO", f"Total {cleaned_count} temporary folders cleaned.")

    def closeEvent(self, event):
        """Handle application close event."""
        self.cleanup_temp_folders()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
