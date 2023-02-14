'''
Function:
    音乐下载器GUI界面
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import os
import sys
import requests
from PyQt5 import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from musicdl import musicdl
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets, QtGui, QtCore
from musicdl.modules.utils import Downloader, touchdir


'''音乐下载器GUI界面'''
class MusicdlGUI(QWidget):
    def __init__(self, parent=None):
        super(MusicdlGUI, self).__init__()
        # 初始化
        config = {'logfilepath': 'musicdl.log', 'savedir': 'downloaded', 'search_size_per_source': 2, 'proxies': {}}
        self.music_api = musicdl.musicdl(config=config)
        self.setWindowTitle('音乐下载器GUI界面 —— Charles的皮卡丘')
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icon.ico')))
        self.setFixedSize(900, 480)
        self.initialize()
        # 搜索源
        self.src_names = ['QQ音乐', '酷我音乐', '咪咕音乐', '千千音乐', '酷狗音乐', '网易云音乐']
        self.label_src = QLabel('搜索源:')
        self.check_boxes = []
        for src in self.src_names:
            cb = QCheckBox(src, self)
            cb.setCheckState(QtCore.Qt.Checked)
            self.check_boxes.append(cb)
        # 输入框
        self.label_keyword = QLabel('搜索关键字:')
        self.lineedit_keyword = QLineEdit('微信公众号: Charles的皮卡丘')
        self.button_keyword = QPushButton('搜索')
        # 搜索结果表格
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels(['序号', '歌手', '歌名', '大小', '时长', '专辑', '来源'])
        self.results_table.horizontalHeader().setStyleSheet("QHeaderView::section{background:skyblue;color:black;}")
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 鼠标右键点击的菜单
        self.context_menu = QMenu(self)
        self.action_download = self.context_menu.addAction('下载')
        # 进度条
        self.bar_download = QProgressBar(self)
        self.label_download = QLabel('歌曲下载进度:')
        # 布局
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
        # 绑定事件
        self.button_keyword.clicked.connect(self.search)
        self.results_table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.mouseclick)
        self.action_download.triggered.connect(self.download)
    '''初始化'''
    def initialize(self):
        self.search_results = {}
        self.music_records = {}
        self.selected_music_idx = -10000
    '''鼠标右键点击事件'''
    def mouseclick(self):
        self.context_menu.move(QCursor().pos())
        self.context_menu.show()
    '''下载'''
    def download(self):
        self.selected_music_idx = str(self.results_table.selectedItems()[0].row())
        songinfo = self.music_records.get(self.selected_music_idx)
        headers = Downloader(songinfo).headers
        touchdir(songinfo['savedir'])
        with requests.get(songinfo['download_url'], headers=headers, stream=True, verify=False) as response:
            if response.status_code == 200:
                total_size, chunk_size, download_size = int(response.headers['content-length']), 1024, 0
                with open(os.path.join(songinfo['savedir'], songinfo['savename']+'.'+songinfo['ext']), 'wb') as fp:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            fp.write(chunk)
                            download_size += len(chunk)
                            self.bar_download.setValue(int(download_size / total_size * 100))
        QMessageBox().information(self, '下载完成', '歌曲%s已经下载完成, 保存在当前路径的%s文件夹下' % (songinfo['savename'], songinfo['savedir']))
        self.bar_download.setValue(0)
    '''搜索'''
    def search(self):
        self.initialize()
        target_srcs_dict = {
            'QQ音乐': 'qqmusic', 
            '酷我音乐': 'kuwo', 
            '咪咕音乐': 'migu', 
            '千千音乐': 'qianqian', 
            '酷狗音乐': 'kugou', 
            '网易云音乐': 'netease',
        }
        selected_src_names = []
        for cb in self.check_boxes:
            if cb.isChecked():
                selected_src_names.append(cb.text())
        target_srcs = [target_srcs_dict.get(name) for name in selected_src_names]
        keyword = self.lineedit_keyword.text()
        self.search_results = self.music_api.search(keyword, target_srcs)
        count, row = 0, 0
        for value in self.search_results.values():
            count += len(value)
        self.results_table.setRowCount(count)
        for _, (key, values) in enumerate(self.search_results.items()):
            for _, value in enumerate(values):
                for column, item in enumerate([str(row), value['singers'], value['songname'], value['filesize'], value['duration'], value['album'], value['source']]):
                    self.results_table.setItem(row, column, QTableWidgetItem(item))
                    self.results_table.item(row, column).setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.music_records.update({str(row): value})
                row += 1
        return self.search_results


'''run'''
if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = MusicdlGUI()
    gui.show()
    sys.exit(app.exec_())