# Main Window
"""
Main application window for MusicDL GUI.
"""

import os
import sys
import logging
import shutil
import time

import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error as ID3Error
from mutagen.flac import FLAC, Picture

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QProgressBar, QCheckBox, QFileDialog,
    QMessageBox, QComboBox, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QIcon

from .utils import resource_path
from .themes import ThemeManager
from .dialogs import SourceSelectionDialog, ThemeConfigDialog
from .widgets import SortableTableWidgetItem
from .workers import Worker, GUILoggerHandle, GlobalLogSignal, GUIProgress, GUIProgressSignal

# Import MusicClient
try:
    from musicdl import MusicClient, DEFAULT_MUSIC_SOURCES, SUPPORTED_MUSIC_SOURCES
    from modules.utils import LoggerHandle
    from modules.sources import MusicClientBuilder
except ImportError:
    try:
        from musicdl.musicdl import MusicClient, DEFAULT_MUSIC_SOURCES, SUPPORTED_MUSIC_SOURCES
        from musicdl.modules.utils import LoggerHandle
        from musicdl.modules.sources import MusicClientBuilder
    except ImportError:
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from musicdl import MusicClient, DEFAULT_MUSIC_SOURCES, SUPPORTED_MUSIC_SOURCES
        from modules import BuildMusicClient, LoggerHandle, MusicClientBuilder

# Import fetch_lyrics_via_lddc with fallback
try:
    from modules.utils.lddc_adapter import fetch_lyrics_via_lddc
except ImportError:
    try:
        from musicdl.modules.utils.lddc_adapter import fetch_lyrics_via_lddc
    except ImportError:
        def fetch_lyrics_via_lddc(*args, **kwargs):
            return None

# Fallback
try:
    SUPPORTED_MUSIC_SOURCES
except NameError:
    SUPPORTED_MUSIC_SOURCES = DEFAULT_MUSIC_SOURCES


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusicDL")
        self.resize(1100, 750)
        
        # Set Icon
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.settings = QSettings("MusicDL", "GUI")
        
        # Setup Global Log Signal
        self.log_signal = GlobalLogSignal()
        self.log_signal.log.connect(self._append_log)
        GUILoggerHandle.set_log_signal(self.log_signal)
        
        self.logger = GUILoggerHandle()
        self.tm = ThemeManager()
        
        self.music_client = None
        self.current_song_infos = {}
        self.is_searching = False
        self.is_parsing_playlist = False
        
        self._init_ui()
        self._apply_theme()
        self._init_client()
    
    def _apply_theme(self):
        """Apply the current theme stylesheet."""
        qss = self.tm.get_stylesheet()
        self.setStyleSheet(qss)
    
    def _init_client(self):
        """Initialize the music client."""
        saved_path = self.settings.value(
            "download_path", 
            os.path.join(os.getcwd(), 'musicdl_outputs')
        )
        if not os.path.exists(saved_path):
            try:
                os.makedirs(saved_path, exist_ok=True)
            except Exception:
                pass
        
        current_sources = self.settings.value("selected_sources", DEFAULT_MUSIC_SOURCES)
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
        self._update_log_level()
    
    def _init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # === Search & Settings Panel ===
        control_group = QGroupBox("搜索与设置")
        control_layout = QHBoxLayout(control_group)
        control_layout.setSpacing(10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入歌曲关键词...")
        self.search_input.returnPressed.connect(self._start_search)
        control_layout.addWidget(self.search_input, stretch=2)
        
        self.search_btn = QPushButton("🔍 搜索")
        self.search_btn.setProperty("accent", True)
        self.search_btn.clicked.connect(self._start_search)
        control_layout.addWidget(self.search_btn)
        
        control_layout.addStretch()
        
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setText(self.settings.value(
            "download_path", 
            os.path.join(os.getcwd(), 'musicdl_outputs')
        ))
        control_layout.addWidget(self.path_input, stretch=1)
        
        self.browse_btn = QPushButton("📁 选择目录")
        self.browse_btn.clicked.connect(self._browse_path)
        control_layout.addWidget(self.browse_btn)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.currentTextChanged.connect(self._update_log_level)
        control_layout.addWidget(QLabel("日志:"))
        control_layout.addWidget(self.log_level_combo)
        
        self.source_btn = QPushButton("⚙ 资源")
        self.source_btn.clicked.connect(self._select_sources)
        control_layout.addWidget(self.source_btn)
        
        self.theme_btn = QPushButton("🎨 外观")
        self.theme_btn.clicked.connect(self._open_theme_settings)
        control_layout.addWidget(self.theme_btn)
        
        main_layout.addWidget(control_group)
        
        # === Playlist Panel ===
        playlist_group = QGroupBox("歌单下载 (QQ/NetEase)")
        playlist_layout = QHBoxLayout(playlist_group)
        playlist_layout.setSpacing(10)
        
        playlist_layout.addWidget(QLabel("歌单URL:"))
        self.playlist_url_input = QLineEdit()
        self.playlist_url_input.setPlaceholderText("请输入网易云或QQ音乐歌单URL...")
        self.playlist_url_input.returnPressed.connect(self._start_parse_playlist)
        playlist_layout.addWidget(self.playlist_url_input, stretch=2)
        
        self.parse_playlist_btn = QPushButton("📋 解析歌单")
        self.parse_playlist_btn.clicked.connect(self._start_parse_playlist)
        playlist_layout.addWidget(self.parse_playlist_btn)
        
        main_layout.addWidget(playlist_group)
        
        # === Filter Panel ===
        filter_group = QGroupBox("筛选结果")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setSpacing(10)
        
        filter_layout.addWidget(QLabel("筛选列:"))
        self.filter_column_combo = QComboBox()
        self.filter_column_combo.addItems(["全部", "ID", "歌名", "歌手", "专辑", "大小", "时长", "来源"])
        self.filter_column_combo.currentIndexChanged.connect(self._filter_results)
        filter_layout.addWidget(self.filter_column_combo)
        
        filter_layout.addWidget(QLabel("关键词:"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("输入筛选关键词...")
        self.filter_input.textChanged.connect(self._filter_results)
        filter_layout.addWidget(self.filter_input, stretch=1)
        
        filter_layout.addStretch()
        main_layout.addWidget(filter_group)
        
        # === Splitter for Table & Logs ===
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter, stretch=1)
        
        # Results Table
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels(['ID', '歌名', '歌手', '专辑', '大小', '时长', '来源'])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSortingEnabled(True)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.doubleClicked.connect(self._download_selected)
        table_layout.addWidget(self.results_table)
        
        self.download_btn = QPushButton("⬇ 下载选中歌曲")
        self.download_btn.setProperty("accent", True)
        self.download_btn.clicked.connect(self._download_selected)
        table_layout.addWidget(self.download_btn)
        
        splitter.addWidget(table_container)
        
        # Logs Panel
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 12, 8, 8)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        splitter.addWidget(log_group)
        splitter.setSizes([550, 180])
        
        # Status Bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")
        
        # Add Progress Indicators to Status Bar
        self.progress_label = QLabel("")
        self.status_bar.addPermanentWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def _on_progress_updated(self, task_id, completed, total, speed, eta, description):
        """Update progress UI."""
        if total > 0:
            percentage = int(completed / total * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setVisible(True)
            
            # If it's the "overall" task (usually id 0 or large, but heuristic check)
            if "overall" in str(task_id): # The id comes as float, might be harder to check string
                # Our GUIProgress just uses floats. 
                pass
        
        # We rely on description to know what we are updating
        self.progress_label.setText(f"{speed} | ETA: {eta} | {description}")
    
    def _browse_path(self):
        """Open directory browser for download path."""
        directory = QFileDialog.getExistingDirectory(
            self, "选择保存目录", self.path_input.text()
        )
        if directory:
            self.path_input.setText(directory)
            self.settings.setValue("download_path", directory)
            self._init_client()
    
    def _update_log_level(self):
        """Update the logging level."""
        level_str = self.log_level_combo.currentText()
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        self.logger.log_level = level_map.get(level_str, logging.WARNING)
        self.settings.setValue("log_level", level_str)
        self._append_log("SYSTEM", f"日志等级已设置为: {level_str}")
    
    def _append_log(self, level: str, message: str):
        """Append a log message to the log area."""
        color = self.tm.get_log_color(level) if hasattr(self, 'tm') else "#888888"
        self.log_text.append(f'<span style="color:{color}">[{level}] {message}</span>')
    
    def _start_search(self):
        """Start or stop music search."""
        if self.is_searching:
            self.is_searching = False
            self.search_btn.setText("🔍 搜索")
            self.parse_playlist_btn.setEnabled(True)
            self.status_bar.showMessage("搜索已停止")
            return
        
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
        
        self.is_searching = True
        self.search_btn.setText("⏹ 停止")
        self.parse_playlist_btn.setEnabled(False)
        
        self.status_bar.showMessage(f"正在搜索: {keyword} ...")
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(0)
        self.current_song_infos = {}
        
        self.search_worker = Worker(self.music_client.search, keyword)
        self.search_worker.finished.connect(self._on_search_finished)
        self.search_worker.error.connect(self._on_worker_error)
        self.search_worker.start()
    
    def _on_search_finished(self, result):
        """Handle search completion."""
        if not self.is_searching:
            return
        self.is_searching = False
        self.search_btn.setText("🔍 搜索")
        self.parse_playlist_btn.setEnabled(True)
        
        search_results = result['data']
        self.status_bar.showMessage("搜索完成")
        self._display_song_list(search_results)
    
    def _start_parse_playlist(self):
        """Parse playlist URL and display songs."""
        playlist_url = self.playlist_url_input.text().strip()
        if not playlist_url:
            QMessageBox.warning(self, "提示", "请输入歌单URL")
            return
        
        self.is_parsing_playlist = True
        self.parse_playlist_btn.setEnabled(False)
        self.search_btn.setEnabled(False)
        self.status_bar.showMessage("正在解析歌单...")
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(0)
        self.current_song_infos = {}
        
        self.playlist_worker = Worker(self.music_client.parseplaylist, playlist_url)
        self.playlist_worker.finished.connect(self._on_playlist_parsed)
        self.playlist_worker.error.connect(self._on_worker_error)
        self.playlist_worker.start()
    
    def _on_playlist_parsed(self, result):
        """Handle playlist parsing completion."""
        self.is_parsing_playlist = False
        self.parse_playlist_btn.setEnabled(True)
        self.search_btn.setEnabled(True)
        
        song_infos = result['data']
        if not song_infos:
            self.status_bar.showMessage("歌单解析失败或为空")
            QMessageBox.warning(self, "提示", "未能解析到任何歌曲，请检查URL是否正确")
            return
        
        self.status_bar.showMessage(f"解析完成，共 {len(song_infos)} 首歌曲")
        
        # Group songs by source
        grouped_results = {}
        for song in song_infos:
            # Handle both object (SongInfo) and dict
            if isinstance(song, dict):
                source = song.get('source', 'Unknown')
            else:
                source = getattr(song, 'source', 'Unknown')
            
            if source not in grouped_results:
                grouped_results[source] = []
            grouped_results[source].append(song)
            
        self._display_song_list(grouped_results)
    
    def _display_song_list(self, search_results: dict):
        """Display song list in the table."""
        def safe_get(d, k):
            return str(d.get(k, ''))
        
        def parse_size(size_str):
            if not size_str:
                return 0.0
            s = size_str.upper().strip()
            multip = 1
            if 'KB' in s:
                multip = 1024
                s = s.replace('KB', '')
            elif 'MB' in s:
                multip = 1024 * 1024
                s = s.replace('MB', '')
            elif 'GB' in s:
                multip = 1024 * 1024 * 1024
                s = s.replace('GB', '')
            elif 'B' in s:
                s = s.replace('B', '')
            try:
                return float(s) * multip
            except Exception:
                return 0.0
        
        def parse_duration(dur_str):
            if not dur_str:
                return 0
            parts = dur_str.split(':')
            try:
                if len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    return int(parts[0])
            except Exception:
                return 0
        
        # Flatten songs
        all_songs = []
        for source, songs in search_results.items():
            for song in songs:
                all_songs.append((source, song))
        
        self.results_table.setRowCount(len(all_songs))
        self.current_song_infos = {}
        id_counter = 1
        
        for row, (source_name, song) in enumerate(all_songs):
            self.current_song_infos[str(id_counter)] = song
            
            # ID
            item_id = SortableTableWidgetItem(str(id_counter))
            item_id.setData(Qt.ItemDataRole.UserRole, id_counter)
            self.results_table.setItem(row, 0, item_id)
            
            # Name
            name = safe_get(song, 'song_name')
            item_name = SortableTableWidgetItem(name)
            item_name.setData(Qt.ItemDataRole.UserRole, name.lower())
            self.results_table.setItem(row, 1, item_name)
            
            # Singers
            singers = safe_get(song, 'singers')
            item_singers = SortableTableWidgetItem(singers)
            item_singers.setData(Qt.ItemDataRole.UserRole, singers.lower())
            self.results_table.setItem(row, 2, item_singers)
            
            # Album
            album = safe_get(song, 'album')
            item_album = SortableTableWidgetItem(album)
            item_album.setData(Qt.ItemDataRole.UserRole, album.lower())
            self.results_table.setItem(row, 3, item_album)
            
            # Size
            size_str = safe_get(song, 'file_size')
            item_size = SortableTableWidgetItem(size_str)
            item_size.setData(Qt.ItemDataRole.UserRole, parse_size(size_str))
            self.results_table.setItem(row, 4, item_size)
            
            # Duration
            dur_str = safe_get(song, 'duration')
            item_dur = SortableTableWidgetItem(dur_str)
            item_dur.setData(Qt.ItemDataRole.UserRole, parse_duration(dur_str))
            self.results_table.setItem(row, 5, item_dur)
            
            # Source
            item_source = SortableTableWidgetItem(source_name)
            item_source.setData(Qt.ItemDataRole.UserRole, source_name.lower())
            self.results_table.setItem(row, 6, item_source)
            
            id_counter += 1
        
        self.results_table.setSortingEnabled(True)
        self._filter_results()
    
    def _filter_results(self):
        """Filter table results based on input."""
        filter_text = self.filter_input.text().lower().strip()
        col_idx = self.filter_column_combo.currentIndex()
        target_col = col_idx - 1  # -1 if All
        
        for row in range(self.results_table.rowCount()):
            hidden = False
            if not filter_text:
                hidden = False
            else:
                if target_col == -1:
                    row_matches = False
                    for c in range(self.results_table.columnCount()):
                        item = self.results_table.item(row, c)
                        if item and filter_text in item.text().lower():
                            row_matches = True
                            break
                    hidden = not row_matches
                else:
                    item = self.results_table.item(row, target_col)
                    hidden = not (item and filter_text in item.text().lower())
            
            self.results_table.setRowHidden(row, hidden)
    
    def _download_selected(self):
        """Download selected songs."""
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
        
        # Initialize Progress Signal
        self.progress_signal = GUIProgressSignal()
        self.progress_signal.progress.connect(self._on_progress_updated)
        
        self.download_worker = Worker(self._download_and_process, songs_to_download, self.progress_signal)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.error.connect(self._on_worker_error)
        self.download_worker.start()
    
    def _download_and_process(self, songs_to_download, progress_signal):
        """Download and process songs (runs in worker thread)."""
        gui_progress = GUIProgress(signal=progress_signal)
        self.music_client.download(songs_to_download, progress_handler=gui_progress)
        
        target_dir = self.settings.value(
            "download_path", 
            os.path.join(os.getcwd(), 'musicdl_outputs')
        )
        
        self.log_signal.log.emit("INFO", f"Processing {len(songs_to_download)} downloaded files...")
        
        for song_info in songs_to_download:
            try:
                org_path = (
                    song_info.save_path if hasattr(song_info, 'save_path') 
                    else song_info.get('save_path') if hasattr(song_info, 'get') 
                    else None
                )
                
                self.log_signal.log.emit(
                    "DEBUG", 
                    f"Processing: song_name={getattr(song_info, 'song_name', 'Unknown')}, save_path={org_path}"
                )
                
                if not org_path or not os.path.exists(org_path):
                    self.log_signal.log.emit(
                        "WARNING", 
                        f"Skipping song - file not found: {getattr(song_info, 'song_name', 'Unknown')}"
                    )
                    continue
                
                # Construct new filename
                song_name = getattr(song_info, 'song_name', 'Unknown')
                singer = getattr(song_info, 'singers', 'Unknown')
                source = getattr(song_info, 'source', 'Unknown').replace('MusicClient', '')
                ext = getattr(song_info, 'ext', 'mp3')
                
                bitrate = getattr(song_info, 'bitrate', None)
                if not bitrate:
                    try:
                        from tinytag import TinyTag
                        tag = TinyTag.get(org_path)
                        if tag.bitrate:
                            bitrate = int(round(tag.bitrate))
                    except Exception:
                        pass
                
                bitrate_str = f"{bitrate}kbps" if bitrate else 'Unknown'
                
                def sanitize(s):
                    return "".join(c for c in s if c not in r'<>:"/\|?*')
                
                new_name = f"{sanitize(song_name)}-{sanitize(singer)}-{sanitize(source)}-{sanitize(bitrate_str)}.{ext}"
                new_path = os.path.join(target_dir, new_name)
                
                # Handle duplicates
                if os.path.exists(new_path):
                    base, extension = os.path.splitext(new_name)
                    counter = 1
                    while os.path.exists(os.path.join(target_dir, f"{base} ({counter}){extension}")):
                        counter += 1
                    new_path = os.path.join(target_dir, f"{base} ({counter}){extension}")
                
                shutil.move(org_path, new_path)
                self.log_signal.log.emit("INFO", f"Moved file to: {new_path}")
                
                time.sleep(0.5)
                
                # Embed cover art
                try:
                    cover_url = getattr(song_info, 'cover_url', None)
                    if cover_url:
                        self.log_signal.log.emit("INFO", f"Downloading cover for {new_name}...")
                        cover_resp = requests.get(cover_url, timeout=10)
                        cover_resp.raise_for_status()
                        cover_data = cover_resp.content
                        
                        if ext.lower() == 'mp3':
                            audio = MP3(new_path, ID3=ID3)
                            try:
                                audio.add_tags()
                            except ID3Error:
                                pass
                            audio.tags.add(APIC(
                                encoding=3,
                                mime='image/jpeg',
                                type=3,
                                desc='Cover',
                                data=cover_data
                            ))
                            audio.save()
                            self.log_signal.log.emit("INFO", "Cover art embedded (MP3).")
                        elif ext.lower() == 'flac':
                            audio = FLAC(new_path)
                            image = Picture()
                            image.type = 3
                            image.mime = 'image/jpeg'
                            image.desc = 'Cover'
                            image.data = cover_data
                            audio.add_picture(image)
                            audio.save()
                            self.log_signal.log.emit("INFO", "Cover art embedded (FLAC).")
                except Exception as e:
                    self.log_signal.log.emit("WARNING", f"Failed to embed cover: {str(e)}")
                
                # Save info file
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
                        fp.write('-' * 20 + ' Lyrics ' + '-' * 20 + '\n')
                        fp.write(f'{getattr(song_info, "lyric", "")}\n')
                        fp.write('=' * 50 + '\n')
                    self.log_signal.log.emit("INFO", f"Saved info to {txt_name}")
                except Exception as e:
                    self.log_signal.log.emit("ERROR", f"Failed to save txt info: {str(e)}")
                
                # Fetch lyrics via LDDC
                try:
                    self.log_signal.log.emit("INFO", f"Fetching lyrics via LDDC for {new_name}...")
                    # We need to construct a song_info compatible object or dict
                    # The current song_info might be a dict or object, checking and creating a proxy
                    lddc_info = {
                        'source': getattr(song_info, 'source', 'Unknown') or song_info.get('source', 'Unknown'),
                        'song_name': getattr(song_info, 'song_name', 'Unknown') or song_info.get('song_name', 'Unknown'),
                        'singers': getattr(song_info, 'singers', 'Unknown') or song_info.get('singers', 'Unknown'),
                        'album': getattr(song_info, 'album', 'Unknown') or song_info.get('album', 'Unknown'),
                        'duration': getattr(song_info, 'duration', 'Unknown') or song_info.get('duration', 'Unknown'),
                        'save_path': new_path
                    }
                    
                    lyrics = fetch_lyrics_via_lddc(lddc_info, embed=True)
                    if lyrics:
                        self.log_signal.log.emit("INFO", f"LDDC: Fetched lyrics for {new_name}")
                        # Update txt file
                        txt_name = os.path.splitext(new_name)[0] + ".txt"
                        txt_path = os.path.join(target_dir, txt_name)
                        if os.path.exists(txt_path):
                             with open(txt_path, 'r', encoding='utf-8') as f:
                                 lines = f.readlines()
                             with open(txt_path, 'w', encoding='utf-8') as f:
                                 in_lyrics = False
                                 for line in lines:
                                     if 'Lyrics' in line and '-'*20 in line:
                                         f.write(line)
                                         f.write(f'{lyrics}\n')
                                         in_lyrics = True
                                     elif in_lyrics and '='*50 in line:
                                         in_lyrics = False
                                         f.write(line)
                                     elif not in_lyrics:
                                         f.write(line)
                        self.log_signal.log.emit("INFO", f"LDDC: Updated lyrics in {txt_name}")
                    else:
                        self.log_signal.log.emit("INFO", f"LDDC: No lyrics found for {new_name}")

                except Exception as e:
                    self.log_signal.log.emit("WARNING", f"LDDC fetch failed: {str(e)}")
                
                # Cleanup empty folders
                parent_dir = os.path.dirname(org_path)
                try:
                    if parent_dir and os.path.exists(parent_dir) and not os.listdir(parent_dir):
                        os.rmdir(parent_dir)
                        grandparent = os.path.dirname(parent_dir)
                        if grandparent and os.path.exists(grandparent) and not os.listdir(grandparent):
                            os.rmdir(grandparent)
                except Exception:
                    pass
            
            except Exception as e:
                self.log_signal.log.emit(
                    "ERROR", 
                    f"Failed to process {getattr(song_info, 'song_name', 'Unknown')}: {str(e)}"
                )
        
        return songs_to_download
    
    def _on_download_finished(self, result):
        """Handle download completion."""
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.status_bar.showMessage("所有任务处理完毕")
        QMessageBox.information(
            self, "完成", 
            "选中的歌曲已处理完毕。\n(已自动重命名并整理到根目录)"
        )
    
    def _on_worker_error(self, error_msg):
        """Handle worker errors."""
        if not self.is_searching and not self.is_parsing_playlist:
            return
        self.is_searching = False
        self.is_parsing_playlist = False
        self.search_btn.setText("🔍 搜索")
        self.search_btn.setEnabled(True)
        self.parse_playlist_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.status_bar.showMessage("发生错误")
        QMessageBox.critical(self, "错误", f"发生意外错误: {error_msg}")
        self._append_log("ERROR", error_msg)
    
    def _select_sources(self):
        """Open source selection dialog."""
        was_searching = self.is_searching
        if was_searching:
            self.is_searching = False
            self.search_btn.setText("🔍 搜索")
            self.status_bar.showMessage("搜索已暂停 (正在设置源...)")
        
        current_sources = self.music_client.music_sources
        dialog = SourceSelectionDialog(self, current_sources)
        if dialog.exec():
            new_sources = dialog.get_selected_sources()
            if not new_sources:
                QMessageBox.warning(self, "警告", "未选择任何源，将使用默认源！")
                new_sources = DEFAULT_MUSIC_SOURCES
            
            self.settings.setValue("selected_sources", new_sources)
            self._init_client()
            self._append_log(
                "SYSTEM", 
                f"音乐源已更新: {', '.join([s.replace('MusicClient', '') for s in new_sources])}"
            )
            
            if was_searching and self.search_input.text().strip():
                self._start_search()
    
    def _open_theme_settings(self):
        """Open theme configuration dialog."""
        dialog = ThemeConfigDialog(self.tm, self)
        if dialog.exec():
            new_colors = dialog.get_colors()
            selected_preset = dialog.get_selected_preset()
            
            if selected_preset:
                self.tm.apply_preset(selected_preset)
            else:
                self.tm.colors = new_colors
                self.tm.current_preset = None
                self.tm.save()
            
            self._apply_theme()
            self._append_log("SYSTEM", f"外观设置已更新: {self.tm.get_current_display_name()}")
    
    def _cleanup_temp_folders(self):
        """Delete temporary client folders."""
        download_path = self.settings.value(
            "download_path", 
            os.path.join(os.getcwd(), 'musicdl_outputs')
        )
        temp_folders = list(MusicClientBuilder.REGISTERED_MODULES.keys())
        
        cleaned_count = 0
        for folder in temp_folders:
            target_path = os.path.join(download_path, folder)
            if os.path.exists(target_path) and os.path.isdir(target_path):
                try:
                    shutil.rmtree(target_path)
                    cleaned_count += 1
                    self.log_signal.log.emit("INFO", f"Cleaned up temporary folder: {folder}")
                except Exception as e:
                    self.log_signal.log.emit("WARNING", f"Failed to clean up {folder}: {str(e)}")
        
        if cleaned_count > 0:
            self.log_signal.log.emit("INFO", f"Total {cleaned_count} temporary folders cleaned.")
    
    def closeEvent(self, event):
        """Handle application close."""
        self._cleanup_temp_folders()
        event.accept()
