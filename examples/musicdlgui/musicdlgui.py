'''
Function:
    Implementation of MusicdlGUI
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import sys
import requests
from PyQt5 import *
from PyQt5 import QtCore
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from musicdl import musicdl
from PyQt5.QtWidgets import *
from musicdl.modules.utils.misc import touchdir, sanitize_filepath


'''MusicdlGUI'''
class MusicdlGUI(QWidget):
    def __init__(self):
        super(MusicdlGUI, self).__init__()
        # initialize
        self.setWindowTitle('MusicdlGUI —— Charles的皮卡丘')
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icon.ico')))
        self.setFixedSize(900, 480)
        self.initialize()
        # search sources
        self.src_names = ['QQMusicClient', 'KuwoMusicClient', 'MiguMusicClient', 'QianqianMusicClient', 'KugouMusicClient', 'NeteaseMusicClient']
        self.label_src = QLabel('Search Engine:')
        self.check_boxes = []
        for src in self.src_names:
            cb = QCheckBox(src, self)
            cb.setCheckState(QtCore.Qt.Checked)
            self.check_boxes.append(cb)
        # input boxes
        self.label_keyword = QLabel('Keywords:')
        self.lineedit_keyword = QLineEdit('尾戒')
        self.button_keyword = QPushButton('Search')
        # search results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels(['ID', 'Singers', 'Songname', 'Filesize', 'Duration', 'Album', 'Source'])
        self.results_table.horizontalHeader().setStyleSheet("QHeaderView::section{background:skyblue;color:black;}")
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # mouse click menu
        self.context_menu = QMenu(self)
        self.action_download = self.context_menu.addAction('Download')
        # progress bar
        self.bar_download = QProgressBar(self)
        self.label_download = QLabel('Download progress:')
        # grid
        grid = QGridLayout()
        grid.addWidget(self.label_src, 0, 0, 1, 1)
        for idx, cb in enumerate(self.check_boxes): grid.addWidget(cb, 0, idx+1, 1, 1)
        grid.addWidget(self.label_keyword, 1, 0, 1, 1)
        grid.addWidget(self.lineedit_keyword, 1, 1, 1, len(self.src_names)-1)
        grid.addWidget(self.button_keyword, 1, len(self.src_names), 1, 1)
        grid.addWidget(self.label_download, 2, 0, 1, 1)
        grid.addWidget(self.bar_download, 2, 1, 1, len(self.src_names))
        grid.addWidget(self.results_table, 3, 0, len(self.src_names), len(self.src_names)+1)
        self.grid = grid
        self.setLayout(grid)
        # connect
        self.button_keyword.clicked.connect(self.search)
        self.results_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.mouseclick)
        self.action_download.triggered.connect(self.download)
    '''initialize'''
    def initialize(self):
        self.search_results = {}
        self.music_records = {}
        self.selected_music_idx = -10000
        self.music_client = None
    '''mouseclick'''
    def mouseclick(self):
        self.context_menu.move(QCursor().pos())
        self.context_menu.show()
    '''download'''
    def download(self):
        self.selected_music_idx = str(self.results_table.selectedItems()[0].row())
        song_info = self.music_records.get(self.selected_music_idx)
        with requests.get(song_info['download_url'], headers=self.music_client.music_clients[song_info['source']].default_download_headers, stream=True, verify=False) as resp:
            if resp.status_code == 200:
                total_size, chunk_size, download_size = int(resp.headers['content-length']), 1024, 0
                touchdir(song_info['work_dir'])
                download_music_file_path = sanitize_filepath(os.path.join(song_info['work_dir'], song_info['song_name']+'.'+song_info['ext']))
                with open(download_music_file_path, 'wb') as fp:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if not chunk: continue
                        fp.write(chunk)
                        download_size += len(chunk)
                        self.bar_download.setValue(int(download_size / total_size * 100))
        QMessageBox().information(self, 'Successful Downloads', f"Finish downloading {song_info['song_name']} by {song_info['singers']}, see {download_music_file_path}")
        self.bar_download.setValue(0)
    '''search'''
    def search(self):
        self.initialize()
        # selected music sources
        music_sources = []
        for cb in self.check_boxes:
            if cb.isChecked():
                music_sources.append(cb.text())
        # keyword
        keyword = self.lineedit_keyword.text()
        # search
        self.music_client = musicdl.MusicClient(music_sources=music_sources)
        self.search_results = self.music_client.search(keyword=keyword)
        # showing
        count, row = 0, 0
        for per_source_search_results in self.search_results.values():
            count += len(per_source_search_results)
        self.results_table.setRowCount(count)
        for _, (_, per_source_search_results) in enumerate(self.search_results.items()):
            for _, per_source_search_result in enumerate(per_source_search_results):
                for column, item in enumerate([str(row), per_source_search_result['singers'], per_source_search_result['song_name'], per_source_search_result['file_size'], per_source_search_result['duration'], per_source_search_result['album'], per_source_search_result['source']]):
                    self.results_table.setItem(row, column, QTableWidgetItem(item))
                    self.results_table.item(row, column).setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.music_records.update({str(row): per_source_search_result})
                row += 1
        # return
        return self.search_results


'''tests'''
if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = MusicdlGUI()
    gui.show()
    sys.exit(app.exec_())