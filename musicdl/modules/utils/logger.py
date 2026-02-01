'''
Function:
    Implementation of Logging Related Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
from __future__ import annotations
import re
import os
import shutil
import logging
import collections.abc
import tabulate as tabmod
from wcwidth import wcswidth
from tabulate import tabulate
from prettytable import PrettyTable
from platformdirs import user_log_dir
from prompt_toolkit.layout import Layout
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.application.current import get_app_or_none
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import ANSI, to_formatted_text
from typing import Any, List, Optional, Sequence, Set, Tuple, Union, Dict
from prompt_toolkit.formatted_text.utils import fragment_list_width, split_lines, get_cwidth


'''settings'''
tabmod.WIDE_CHARS_MODE = True
NoTruncSpec = Optional[Sequence[Union[int, str]]]
ANSI_CSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
AMBIGUOUS_MAP: Dict[str, str] = {
    "·": ".", "•": "*", "…": "...", "“": '"', "”": '"', "„": '"', "‟": '"', "‘": "'", "’": "'", "‚": "'", "‛": "'", "—": "-", "–": "-", "−": "-", "　": " ",
}
COLORS = {
    'red': '\033[31m', 'green': '\033[32m', 'yellow': '\033[33m', 'blue': '\033[34m', 'pink': '\033[35m', 'cyan': '\033[36m', 'highlight': '\033[93m', 
    'number': '\033[96m', 'singer': '\033[93m', 'flac': '\033[95m', 'songname': '\033[91m'
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


'''ptsizefallback'''
def ptsizefallback() -> Tuple[int, int]:
    app = get_app_or_none()
    if app is not None and getattr(app, "output", None) is not None:
        try:
            sz = app.output.get_size()
            cols, rows = int(sz.columns), int(sz.rows)
            if cols > 0 and rows > 0: return cols, rows
        except Exception:
            pass
    s = shutil.get_terminal_size(fallback=(80, 24))
    return int(s.columns), int(s.lines)


'''stripansi'''
def stripansi(s: str) -> str:
    return ANSI_CSI_RE.sub("", s)


'''dispwidth'''
def dispwidth(s: Any) -> int:
    if s is None: return 0
    w = wcswidth(stripansi(str(s)))
    return max(0, w)


'''normalizeforconsole'''
def normalizeforconsole(text: Any, *, enable: bool) -> str:
    s = "" if text is None else str(text)
    if not s: return s
    s = s.replace("\r", "")
    s = s.replace("\n", " ").replace("\t", " ")
    if enable: s = "".join(AMBIGUOUS_MAP.get(ch, ch) for ch in s)
    return s


'''truncatebydispwidth'''
def truncatebydispwidth(text: Any, max_width: int, ellipsis: str = "...") -> str:
    s = "" if text is None else str(text)
    if max_width <= 0: return ""
    if dispwidth(s) <= max_width: return s
    ell_w = dispwidth(ellipsis)
    target = max_width if max_width <= ell_w else (max_width - ell_w)
    out, used, i, emitted_ansi = [], 0, 0, False
    while i < len(s) and used < target:
        if s[i] == "\x1b":
            m = ANSI_CSI_RE.match(s, i)
            if m: out.append(m.group(0)); emitted_ansi = True; i = m.end(); continue
            i += 1; continue
        ch = s[i]; ch_w = max(wcswidth(ch), 0)
        if used + ch_w > target: break
        out.append(ch); used += ch_w; i += 1
    if emitted_ansi and (not out or not str(out[-1]).endswith("\x1b[0m")): out.append("\x1b[0m")
    core = "".join(out)
    return core if max_width <= ell_w else (core + ellipsis)


'''truncatefragmentstocols'''
def truncatefragmentstocols(fragments: Sequence[Tuple], cols: int) -> List[Tuple]:
    if cols <= 0: return []
    out, used = [], 0
    for style, text, *rest in fragments:
        if not text: continue
        buf: List[str] = []
        for ch in text:
            cw = get_cwidth(ch)
            if used + cw > cols: break
            buf.append(ch); used += cw
        if buf: out.append((style, "".join(buf), *rest))
        if used >= cols: break
    return out


'''truncateandpadline'''
def truncateandpadline(fragments: Sequence[Tuple], cols: int) -> List[Tuple]:
    line = truncatefragmentstocols(fragments, cols)
    pad = cols - fragment_list_width(line)
    if pad > 0: return list(line) + [("", " " * pad)]
    return truncatefragmentstocols(line, cols)


'''smarttrunctable'''
def smarttrunctable(headers: Sequence[Any], rows: Sequence[Sequence[Any]], *, max_col_width: int = 40, min_col_width: int = 4, terminal_right_space_len: int = 2, no_trunc_cols: NoTruncSpec = None, term_width: Optional[int] = None, tablefmt: str = "grid", max_iterations: int = 2000) -> str:
    headers_s = ["" if h is None else str(h) for h in headers]
    rows_s, ncols = [[("" if c is None else str(c)) for c in r] for r in rows], len(headers_s)
    if any(len(r) != ncols for r in rows_s): raise ValueError("All rows must have the same number of columns as headers")
    if term_width is None: term_width = ptsizefallback()[0]
    target_width = max(1, term_width - max(0, terminal_right_space_len))
    protected: Set[int] = set()
    if no_trunc_cols:
        header_to_idx = {h: i for i, h in enumerate(headers_s)}
        for spec in no_trunc_cols:
            if isinstance(spec, int) and 0 <= spec < ncols: protected.add(spec)
            elif not isinstance(spec, int):
                idx = header_to_idx.get(str(spec))
                if idx is not None: protected.add(idx)
    col_natural = [dispwidth(h) for h in headers_s]
    col_natural = [max(col_natural[j], *(dispwidth(r[j]) for r in rows_s)) for j in range(len(col_natural))]
    col_limit: List[Optional[int]] = []
    for j in range(ncols):
        if j in protected: col_limit.append(None)
        else: cap = col_natural[j]; cap = min(cap, max_col_width) if max_col_width else cap; col_limit.append(max(min_col_width, cap))
    def rendercurrent() -> str:
        th = [h if col_limit[j] is None else truncatebydispwidth(h, col_limit[j]) for j, h in enumerate(headers_s)]
        tr = [[cell if col_limit[j] is None else truncatebydispwidth(cell, col_limit[j]) for j, cell in enumerate(r)] for r in rows_s]
        return tabulate(tr, headers=th, tablefmt=tablefmt)
    def tablewidth(table_str: str) -> int:
        return max((dispwidth(line) for line in table_str.splitlines()), default=0)
    last = ""
    for _ in range(max_iterations):
        table_str = rendercurrent()
        last = table_str
        if tablewidth(table_str) <= target_width: return table_str
        cur_w = [dispwidth(h if col_limit[j] is None else truncatebydispwidth(h, col_limit[j])) for j, h in enumerate(headers_s)]
        any(cur_w.__setitem__(j, max(cur_w[j], dispwidth(cell if col_limit[j] is None else truncatebydispwidth(cell, col_limit[j])))) or False for r in rows_s for j, cell in enumerate(r))
        shrinkable = [j for j in range(ncols) if col_limit[j] is not None and col_limit[j] > min_col_width]
        if not shrinkable: return last
        j_widest = max(shrinkable, key=lambda j: cur_w[j])
        col_limit[j_widest] = max(min_col_width, int(col_limit[j_widest]) - 1)
    return last


'''cursorpickintable'''
def cursorpickintable(headers: Sequence[Any], rows: Sequence[Sequence[Any]], row_ids: Sequence[Any], *, no_trunc_cols: NoTruncSpec = None, terminal_right_space_len: int = 2, normalize_ambiguous: Optional[bool] = None, tablefmt: Optional[str] = None) -> List[Any]:
    if len(rows) != len(row_ids): raise ValueError("rows and row_ids length mismatch")
    ncols = len(headers)
    if any(len(r) != ncols for r in rows): raise ValueError("All rows must have same number of columns as headers")
    if normalize_ambiguous is None: normalize_ambiguous = (os.name == "nt")
    if tablefmt is None: tablefmt = "grid" if os.name == "nt" else "fancy_grid"
    headers_s = [normalizeforconsole(h, enable=normalize_ambiguous) for h in headers]
    rows_s = [[normalizeforconsole(c, enable=normalize_ambiguous) for c in r] for r in rows]
    kb, current, picked, view_start = KeyBindings(), 0, set(), 0
    FIRST_DATA_LINE, LINES_PER_ROW = 3, 2
    def termsize() -> Tuple[int, int]: return ptsizefallback()
    def maxvisiblerows(term_lines: int) -> int:
        overhead = 10; usable = max(2, term_lines - overhead)
        return max(1, usable // LINES_PER_ROW)
    def computeview() -> Tuple[int, int]:
        nonlocal view_start; _, term_lines = termsize()
        page = maxvisiblerows(term_lines)
        start = max(0, min(current - page // 2, len(rows_s) - page))
        end, view_start = min(len(rows_s), start + page), start
        return start, end
    def buildtable() -> str:
        cols, _ = termsize()
        start, end = computeview()
        def marker(i: int) -> str:
            at, sel = (i == current), (row_ids[i] in picked)
            if at and sel: return ">*"
            if at: return "> "
            if sel: return "* "
            return "  "
        view_rows: List[List[str]] = []
        for i in range(start, end): row = list(rows_s[i]); row[0] = marker(i) + row[0]; view_rows.append(row)
        view_headers = list(headers_s)
        view_headers[0] = f"{view_headers[0]}  ({start+1}-{end}/{len(rows_s)})"
        return smarttrunctable(headers=view_headers, rows=view_rows, no_trunc_cols=no_trunc_cols, terminal_right_space_len=terminal_right_space_len, term_width=cols, tablefmt=tablefmt)
    def render() -> List[Tuple]:
        cols, term_lines = termsize()
        frags = to_formatted_text(ANSI(buildtable()))
        highlight_line = FIRST_DATA_LINE + (current - view_start) * LINES_PER_ROW
        out, line_count = [], 0
        for li, line_frags in enumerate(split_lines(frags)):
            if li == highlight_line: line_frags = [(((style + " reverse").strip() if style else "reverse"), text, *rest) for style, text, *rest in line_frags]
            out.extend(truncateandpadline(line_frags, cols)); out.append(("", "\n")); line_count += 1
        help_text = ("\nUse ↑/↓ to move, PgUp/PgDn to jump, <space> toggle, a: all, i: invert, <enter> confirm, q/Esc cancel.\n")
        help_frags = to_formatted_text(ANSI(help_text))
        for line_frags in split_lines(help_frags): out.extend(truncateandpadline(line_frags, cols)); out.append(("", "\n")); line_count += 1
        while line_count < term_lines: out.append(("", " " * cols)); out.append(("", "\n")); line_count += 1
        return out
    def invalidate(event) -> None: event.app.invalidate()
    @kb.add("up")
    def _(event):
        nonlocal current; current = max(0, current - 1)
        invalidate(event)
    @kb.add("down")
    def _(event):
        nonlocal current; current = min(len(rows_s) - 1, current + 1)
        invalidate(event)
    @kb.add("pageup")
    def _(event):
        nonlocal current; _, term_lines = termsize()
        current = max(0, current - maxvisiblerows(term_lines))
        invalidate(event)
    @kb.add("pagedown")
    def _(event):
        nonlocal current; _, term_lines = termsize()
        current = min(len(rows_s) - 1, current + maxvisiblerows(term_lines))
        invalidate(event)
    @kb.add(" ")
    def _(event): rid = row_ids[current]; (picked.remove(rid) if rid in picked else picked.add(rid)); invalidate(event)
    @kb.add("a")
    @kb.add("A")
    def _(event): picked.clear(); picked.update(row_ids); invalidate(event)
    @kb.add("i")
    @kb.add("I")
    def _(event): picked.symmetric_difference_update(row_ids); invalidate(event)
    @kb.add("enter")
    def _(event): event.app.exit(result=[rid for rid in row_ids if rid in picked])
    @kb.add("escape")
    @kb.add("q")
    def _(event): event.app.exit(result=[])
    app = Application(layout=Layout(HSplit([Window(FormattedTextControl(render), wrap_lines=False)])), key_bindings=kb, full_screen=True)
    return app.run()