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
import collections.abc
from wcwidth import wcswidth
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
def printtable(titles, items, terminal_right_space_len=4):
    assert isinstance(titles, collections.abc.Sequence) and isinstance(items, collections.abc.Sequence), 'title and items should be iterable'
    table = PrettyTable(titles)
    for item in items: table.add_row(item)
    max_width = shutil.get_terminal_size().columns - terminal_right_space_len
    assert max_width > 0, f'"terminal_right_space_len" should smaller than {shutil.get_terminal_size()}'
    table.max_table_width = max_width
    print(table)
    return table


'''displen'''
def displen(s: str) -> int:
    if s is None:
        return 0
    return max(wcswidth(str(s)), 0)


'''tablewidth'''
def tablewidth(table_str: str) -> int:
    lines = table_str.splitlines()
    if not lines:
        return 0
    return max(displen(line) for line in lines)


'''truncatebydispwidth'''
def truncatebydispwidth(text: str, max_width: int) -> str:
    text, cur_w = str(text), displen(text)
    if cur_w <= max_width: return text
    if max_width <= 0: return ""
    if max_width <= 3:
        acc, out = 0, []
        for ch in text:
            w = displen(ch)
            if acc + w > max_width: break
            out.append(ch)
            acc += w
        return "".join(out)
    target, acc, out_chars = max_width - 3, 0, []
    for ch in text:
        w = displen(ch)
        if acc + w > target: break
        out_chars.append(ch)
        acc += w
    return "".join(out_chars) + "..."


'''smarttrunctable'''
def smarttrunctable(headers, rows, max_col_width=40, terminal_right_space_len=10, no_trunc_cols=None, min_col_width=4, max_iterations=2000):
    headers = [str(h) for h in headers]
    rows = [[str(c) for c in row] for row in rows]
    ncols = len(headers)
    assert all(len(r) == ncols for r in rows), "all rows must have same length as headers"
    term_width = shutil.get_terminal_size().columns
    target_width = term_width - terminal_right_space_len
    if target_width <= 0: target_width = term_width
    protected_idx = set()
    if no_trunc_cols:
        for spec in no_trunc_cols:
            if isinstance(spec, int):
                if 0 <= spec < ncols: protected_idx.add(spec)
            else:
                for j, h in enumerate(headers):
                    if h == str(spec): protected_idx.add(j)
    col_max = []
    for j in range(ncols):
        w = displen(headers[j])
        for row in rows: w = max(w, displen(row[j]))
        col_max.append(w)
    col_limits = []
    for j in range(ncols):
        if j in protected_idx: col_limits.append(None)
        else:
            limit = col_max[j]
            if max_col_width: limit = min(limit, max_col_width)
            limit = max(limit, min_col_width)
            col_limits.append(limit)
    last_table = ""
    for _ in range(max_iterations):
        truncated_headers = []
        for j, h in enumerate(headers):
            if col_limits[j] is None: truncated_headers.append(h)
            else: truncated_headers.append(truncatebydispwidth(h, col_limits[j]))
        truncated_rows = []
        for row in rows:
            new_row = []
            for j, cell in enumerate(row):
                if col_limits[j] is None: new_row.append(cell)
                else: new_row.append(truncatebydispwidth(cell, col_limits[j]))
            truncated_rows.append(new_row)
        table_str = tabulate(truncated_rows, headers=truncated_headers, tablefmt="fancy_grid")
        last_table = table_str
        w = tablewidth(table_str)
        if w <= target_width: return table_str
        col_cur = [displen(h) for h in truncated_headers]
        for row in truncated_rows:
            for j, cell in enumerate(row): col_cur[j] = max(col_cur[j], displen(cell))
        candidates = [j for j in range(ncols) if col_limits[j] is not None and col_limits[j] > min_col_width]
        if not candidates: return last_table
        j_longest = max(candidates, key=lambda k: col_cur[k])
        col_limits[j_longest] -= 1
    return last_table


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