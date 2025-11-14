'''
Function:
    Implementation of logging related utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import shutil
import logging
import textwrap
import collections.abc
from tabulate import tabulate
from prettytable import PrettyTable
from platformdirs import user_log_dir


'''predefined colors in terminal'''
COLORS = {
    'red': '\033[31m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'pink': '\033[35m',
    'cyan': '\033[36m',
    'highlight': '\033[93m',
    'number': '\033[96m',
    'singer': '\033[93m',
    'flac': '\033[95m',
    'songname': '\033[91m'
}


'''LoggerHandle'''
class LoggerHandle():
    appname = 'musicdl'
    appauthor = 'zcjin'
    def __init__(self):
        # set up log dir
        log_dir = user_log_dir(appname=self.appname, appauthor=self.appauthor)
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, "musicdl.log")
        self.log_file_path = log_file_path
        # config logging
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file_path, encoding="utf-8"), logging.StreamHandler()]
        )
    '''log'''
    @staticmethod
    def log(level, message):
        message = str(message)
        logger = logging.getLogger(LoggerHandle.appname)
        logger.log(level, message)
    '''debug'''
    def debug(self, message, disable_print=False):
        message = str(message)
        if disable_print:
            fp = open(self.log_file_path, 'a', encoding='utf-8')
            fp.write(message + '\n')
        else:
            LoggerHandle.log(logging.DEBUG, message)
    '''info'''
    def info(self, message, disable_print=False):
        message = str(message)
        if disable_print:
            fp = open(self.log_file_path, 'a', encoding='utf-8')
            fp.write(message + '\n')
        else:
            LoggerHandle.log(logging.INFO, message)
    '''warning'''
    def warning(self, message, disable_print=False):
        message = str(message)
        if disable_print:
            fp = open(self.log_file_path, 'a', encoding='utf-8')
            fp.write(message + '\n')
        else:
            if '\033[31m' not in message:
                message = colorize(message, 'red')
            LoggerHandle.log(logging.WARNING, message)
    '''error'''
    def error(self, message, disable_print=False):
        message = str(message)
        if disable_print:
            fp = open(self.log_file_path, 'a', encoding='utf-8')
            fp.write(message + '\n')
        else:
            if '\033[31m' not in message:
                message = colorize(message, 'red')
            LoggerHandle.log(logging.ERROR, message)


'''printtable'''
def printtable(titles, items, terminal_right_space_len=10):
    assert isinstance(titles, collections.abc.Sequence) and isinstance(items, collections.abc.Sequence), 'title and items should be iterable'
    table = PrettyTable(titles)
    for item in items: table.add_row(item)
    max_width = shutil.get_terminal_size().columns - terminal_right_space_len
    assert max_width > 0, f'"terminal_right_space_len" should smaller than {shutil.get_terminal_size()}'
    table.max_table_width = max_width
    print(table)
    return table


'''smarttrunctable'''
def smarttrunctable(headers, rows, max_col_width=40, padding=3, terminal_right_space_len=10):
    term_width = shutil.get_terminal_size().columns - terminal_right_space_len
    assert term_width > 0, f'"terminal_right_space_len" should smaller than {shutil.get_terminal_size()}'
    # max len for each row
    col_lens = {col: len(col) for col in headers}
    for row in rows:
        for i, cell in enumerate(row):
            cell_str = str(cell)
            col = headers[i]
            col_lens[col] = max(col_lens[col], len(cell_str))
    # estimate total len
    est_total_width = sum(min(col_lens[col], max_col_width) for col in headers) + len(headers) * padding
    # text shorten
    need_trunc = est_total_width > term_width
    trunc_cols = set()
    if need_trunc:
        sorted_cols = sorted(col_lens.items(), key=lambda x: -x[1])
        cumulative = 0
        for col, length in sorted_cols:
            if length <= max_col_width: continue
            trunc_cols.add(col)
            cumulative += (length - max_col_width)
            est_total_width -= (length - max_col_width)
            if est_total_width <= term_width: break
    # new table after text shorten
    truncated_rows = []
    for row in rows:
        new_row = []
        for i, cell in enumerate(row):
            cell_str = str(cell)
            col = headers[i]
            if col in trunc_cols and len(cell_str) > max_col_width:
                short = textwrap.shorten(cell_str, width=max_col_width, placeholder="...")
            else:
                short = cell_str
            new_row.append(short)
        truncated_rows.append(new_row)
    # return
    return tabulate(truncated_rows, headers=headers, tablefmt="fancy_grid")


'''colorize'''
def colorize(string, color):
    string = str(string)
    if color not in COLORS: return string
    return COLORS[color] + string + '\033[0m'


'''printfullline'''
def printfullline(ch: str = "*", end: str = '\n', terminal_right_space_len: int = 1):
    cols = shutil.get_terminal_size().columns - terminal_right_space_len
    assert cols > 0, f'"terminal_right_space_len" should smaller than {shutil.get_terminal_size()}'
    print(ch * cols, end=end)