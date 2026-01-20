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
from prompt_toolkit.layout import Layout
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import ANSI, to_formatted_text


'''settings'''
COLORS = {
    'red': '\033[31m', 'green': '\033[32m', 'yellow': '\033[33m', 'blue': '\033[34m', 'pink': '\033[35m', 'cyan': '\033[36m',
    'highlight': '\033[93m', 'number': '\033[96m', 'singer': '\033[93m', 'flac': '\033[95m', 'songname': '\033[91m'
}


'''LoggerHandle'''
class LoggerHandle():
    appname, appauthor = 'musicdl', 'zcjin'
    def __init__(self):
        # set up log dir
        log_dir = user_log_dir(appname=self.appname, appauthor=self.appauthor)
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, "musicdl.log")
        self.log_file_path = log_file_path
        # config logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.FileHandler(log_file_path, encoding="utf-8"), logging.StreamHandler()])
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
            if '\033[31m' not in message: message = colorize(message, 'red')
            LoggerHandle.log(logging.WARNING, message)
    '''error'''
    def error(self, message, disable_print=False):
        message = str(message)
        if disable_print:
            fp = open(self.log_file_path, 'a', encoding='utf-8')
            fp.write(message + '\n')
        else:
            if '\033[31m' not in message: message = colorize(message, 'red')
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
    if s is None: return 0
    return max(wcswidth(str(s)), 0)


'''tablewidth'''
def tablewidth(table_str: str) -> int:
    lines = table_str.splitlines()
    if not lines: return 0
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


'''cursorpickintable'''
def cursorpickintable(headers, rows, row_ids, no_trunc_cols=None, terminal_right_space_len=10):
    assert len(rows) == len(row_ids)
    cur, picked, view_start, kb = [0], set(), [0], KeyBindings()
    def calcview():
        term_lines = shutil.get_terminal_size().lines
        overhead = 8; usable = max(2, term_lines - overhead); max_vis = max(1, usable // 2)
        start = cur[0] - max_vis // 2; start = max(0, min(start, len(rows) - max_vis))
        end = min(len(rows), start + max_vis)
        return start, end
    def buildtablestr():
        start, end = calcview(); view_start[0] = start; view_rows = []
        for i in range(start, end):
            r = rows[i]; rr = list(r); prefix = "▶ " if i == cur[0] else "  "
            if row_ids[i] in picked: prefix = "✓ " if i != cur[0] else "▶✓"
            rr[0] = prefix + rr[0]; view_rows.append(rr)
        view_headers = list(headers)
        view_headers[0] = f"{view_headers[0]}  ({start+1}-{end}/{len(rows)})"
        return smarttrunctable(headers=view_headers, rows=view_rows, no_trunc_cols=no_trunc_cols, terminal_right_space_len=terminal_right_space_len)
    def render():
        table = buildtablestr()
        lines = table.splitlines(True)
        highlight_line, out = 3 + (cur[0] - view_start[0]) * 2, []
        for li, line in enumerate(lines):
            frags = to_formatted_text(ANSI(line))
            if li == highlight_line: frags = [((s + " reverse") if s else "reverse", t) for (s, t) in frags]
            out.extend(frags)
        out.extend(to_formatted_text(ANSI("\nUse ↑/↓ to move, <space> to toggle, a: select all, i: invert, <enter> to confirm, q/Esc to cancel.\n")))
        return out
    @kb.add("up")
    def _(_event):
        if cur[0] > 0: cur[0] -= 1
    @kb.add("down")
    def _(_event):
        if cur[0] < len(rows) - 1: cur[0] += 1
    @kb.add(" ")
    def _(_event):
        rid = row_ids[cur[0]]
        if rid in picked: picked.remove(rid)
        else: picked.add(rid)
    @kb.add("a")
    @kb.add("A")
    def _(_event): picked.clear(); picked.update(row_ids)
    @kb.add("i")
    @kb.add("I")
    def _(_event): picked_sym = set(row_ids); picked_sym.difference_update(picked); picked.clear(); picked.update(picked_sym)
    @kb.add("enter")
    def _(_event): ordered = [rid for rid in row_ids if rid in picked]; _event.app.exit(result=ordered)
    @kb.add("escape")
    @kb.add("q")
    def _(_event): _event.app.exit(result=[])
    app = Application(layout=Layout(HSplit([Window(FormattedTextControl(render))])), key_bindings=kb, full_screen=True)
    return app.run()