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
from itertools import accumulate, takewhile
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.application.current import get_app_or_none
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import ANSI, to_formatted_text
from typing import Any, List, Optional, Sequence, Set, Tuple, Union, Dict, Iterable
from prompt_toolkit.formatted_text.utils import fragment_list_width, split_lines, get_cwidth


'''settings'''
tabmod.WIDE_CHARS_MODE = True
NoTruncSpec = Optional[Sequence[Union[int, str]]]
ANSI_CSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
AMBIGUOUS_MAP: Dict[str, str] = {"·": ".", "•": "*", "…": "...", "“": '"', "”": '"', "„": '"', "‟": '"', "‘": "'", "’": "'", "‚": "'", "‛": "'", "—": "-", "–": "-", "−": "-", "　": " "}
COLORS = {'red': '\033[31m', 'green': '\033[32m', 'yellow': '\033[33m', 'blue': '\033[34m', 'pink': '\033[35m', 'cyan': '\033[36m', 'highlight': '\033[93m', 'number': '\033[96m', 'singer': '\033[93m', 'flac': '\033[95m', 'songname': '\033[91m'}


'''LoggerHandle'''
class LoggerHandle():
    appname, appauthor = 'musicdl', 'zcjin'
    os.makedirs((log_dir := user_log_dir(appname=appname, appauthor=appauthor)), exist_ok=True)
    log_file_path = os.path.join(log_dir, "musicdl.log")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.FileHandler(log_file_path, encoding="utf-8"), logging.StreamHandler()])
    '''log'''
    @staticmethod
    def log(level, message): logging.getLogger(LoggerHandle.appname).log(level, str(message))
    '''debug'''
    @staticmethod
    def debug(message: str, disable_print: bool = False): message = str(message); open(LoggerHandle.log_file_path, 'a', encoding='utf-8').write(message + '\n') if disable_print else LoggerHandle.log(logging.DEBUG, message)
    '''info'''
    @staticmethod
    def info(message: str, disable_print: bool = False): message = str(message); open(LoggerHandle.log_file_path, 'a', encoding='utf-8').write(message + '\n') if disable_print else LoggerHandle.log(logging.INFO, message)
    '''warning'''
    @staticmethod
    def warning(message: str, disable_print: bool = False): message = str(message); open(LoggerHandle.log_file_path, 'a', encoding='utf-8').write(message + '\n') if disable_print else LoggerHandle.log(logging.WARNING, message if '\033[31m' in message else colorize(message, 'red'))
    '''error'''
    @staticmethod
    def error(message: str, disable_print: bool = False): message = str(message); open(LoggerHandle.log_file_path, 'a', encoding='utf-8').write(message + '\n') if disable_print else LoggerHandle.log(logging.ERROR, message if '\033[31m' in message else colorize(message, 'red'))


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
    table = PrettyTable(titles); tuple(table.add_row(item) for item in items)
    max_width = shutil.get_terminal_size().columns - terminal_right_space_len
    assert max_width > 0, f'"terminal_right_space_len" should smaller than {shutil.get_terminal_size()}'
    table.max_table_width = max_width; print(table)
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
    return 0 if s is None else max(0, wcswidth(stripansi(str(s))))


'''normalizeforconsole'''
def normalizeforconsole(text: Any, *, enable: bool) -> str:
    if not (s := "" if text is None else str(text)): return s
    s = s.replace("\r", "").replace("\n", " ").replace("\t", " ")
    return ("".join(AMBIGUOUS_MAP.get(ch, ch) for ch in s) if enable else s)


'''truncatebydispwidth'''
def truncatebydispwidth(text: Any, max_width: int, ellipsis: str = "...") -> str:
    s = "" if text is None else str(text)
    if max_width <= 0 or dispwidth(s) <= max_width: return "" if max_width <= 0 else s
    ell_w = dispwidth(ellipsis); out, used, i, emitted_ansi, target = [], 0, 0, False, max_width - ell_w if max_width > ell_w else max_width
    while i < len(s) and used < target:
        if s[i] == "\x1b": m = ANSI_CSI_RE.match(s, i); out.append(m.group(0)) if m else None; emitted_ansi = True if m else emitted_ansi; i = m.end() if m else i + 1; continue
        if used + (ch_w := max(wcswidth((ch := s[i])), 0)) > target: break
        out.append(ch); used += ch_w; i += 1
    if emitted_ansi and (not out or not str(out[-1]).endswith("\x1b[0m")): out.append("\x1b[0m")
    return ("".join(out) if max_width <= ell_w else "".join(out) + ellipsis)


'''truncatefragmentstocols'''
def truncatefragmentstocols(fragments: Sequence[Tuple], cols: int) -> List[Tuple]:
    if (not cols) or (not isinstance(cols, (int, float))) or (cols <= 0): return []
    output_list, used_rows_in_command_line = [], 0
    for style, text, *rest in fragments:
        if (not text) or (not isinstance(text, Iterable)): continue
        buf: List[str] = []; prefix = list(takewhile(lambda t: used_rows_in_command_line + t[1] <= cols, zip(text, accumulate(map(get_cwidth, text))))); buf.extend(ch for ch, _ in prefix); used_rows_in_command_line += prefix[-1][1] if prefix else 0
        if buf: output_list.append((style, "".join(buf), *rest))
        if used_rows_in_command_line >= cols: break
    return output_list


'''truncateandpadline'''
def truncateandpadline(fragments: Sequence[Tuple], cols: int) -> List[Tuple]:
    line = truncatefragmentstocols(fragments, cols)
    pad = cols - fragment_list_width(line)
    if pad > 0: return list(line) + [("", " " * pad)]
    return truncatefragmentstocols(line, cols)


'''smarttrunctable'''
def smarttrunctable(headers: Sequence[Any], rows: Sequence[Sequence[Any]], *, max_col_width: int = 40, min_col_width: int = 4, terminal_right_space_len: int = 2, no_trunc_cols: NoTruncSpec = None, term_width: Optional[int] = None, tablefmt: str = "grid", max_iterations: int = 2000) -> str:
    headers_s = ["" if h is None else str(h) for h in headers]; rows_s, ncols = [[("" if c is None else str(c)) for c in r] for r in rows], len(headers_s)
    if any(len(r) != ncols for r in rows_s): raise ValueError("All rows must have the same number of columns as headers")
    if term_width is None: term_width = ptsizefallback()[0]
    target_width = max(1, term_width - max(0, terminal_right_space_len)); protected: Set[int] = set()
    if no_trunc_cols: header_to_idx = {h: i for i, h in enumerate(headers_s)}; protected |= {spec if isinstance(spec, int) else idx for spec in no_trunc_cols if (isinstance(spec, int) and 0 <= spec < ncols) or (not isinstance(spec, int) and (idx := header_to_idx.get(str(spec))) is not None)}
    col_natural = [dispwidth(h) for h in headers_s]; col_limit: List[Optional[int]] = []
    col_natural = [max(col_natural[j], *(dispwidth(r[j]) for r in rows_s)) for j in range(len(col_natural))]
    col_limit = [None if j in protected else max(min_col_width, min(col_natural[j], max_col_width) if max_col_width else col_natural[j]) for j in range(ncols)]
    render_current_func = lambda: tabulate([[cell if col_limit[j] is None else truncatebydispwidth(cell, col_limit[j]) for j, cell in enumerate(r)] for r in rows_s], headers=[h if col_limit[j] is None else truncatebydispwidth(h, col_limit[j]) for j, h in enumerate(headers_s)], tablefmt=tablefmt)
    table_width_func, last = lambda table_str: max((dispwidth(line) for line in str(table_str).splitlines()), default=0), ""
    for _ in range(max_iterations):
        table_str = render_current_func(); last = table_str
        if table_width_func(table_str) <= target_width: return table_str
        cur_w = [dispwidth(h if col_limit[j] is None else truncatebydispwidth(h, col_limit[j])) for j, h in enumerate(headers_s)]
        any(cur_w.__setitem__(j, max(cur_w[j], dispwidth(cell if col_limit[j] is None else truncatebydispwidth(cell, col_limit[j])))) or False for r in rows_s for j, cell in enumerate(r))
        if not (shrinkable := [j for j in range(ncols) if col_limit[j] is not None and col_limit[j] > min_col_width]): return last
        j_widest = max(shrinkable, key=lambda j: cur_w[j]); col_limit[j_widest] = max(min_col_width, int(col_limit[j_widest]) - 1)
    return last


'''cursorpickintable'''
def cursorpickintable(headers: Sequence[Any], rows: Sequence[Sequence[Any]], row_ids: Sequence[Any], *, no_trunc_cols: NoTruncSpec = None, terminal_right_space_len: int = 2, normalize_ambiguous: Optional[bool] = None, tablefmt: Optional[str] = None) -> List[Any]:
    if len(rows) != len(row_ids): raise ValueError("rows and row_ids length mismatch")
    if any(len(r) != len(headers) for r in rows): raise ValueError("All rows must have same number of columns as headers")
    if normalize_ambiguous is None: normalize_ambiguous = (os.name == "nt")
    if tablefmt is None: tablefmt = "grid" if os.name == "nt" else "fancy_grid"
    headers_s = [normalizeforconsole(h, enable=normalize_ambiguous) for h in headers]
    rows_s = [[normalizeforconsole(c, enable=normalize_ambiguous) for c in r] for r in rows]
    kb, current, picked, view_start, FIRST_DATA_LINE, LINES_PER_ROW = KeyBindings(), 0, set(), 0, 3, 2
    max_visible_rows_func = lambda term_lines: max(1, max(2, term_lines - 10) // LINES_PER_ROW)
    def computeview() -> Tuple[int, int]:
        nonlocal view_start; _, term_lines = ptsizefallback()
        page = max_visible_rows_func(term_lines)
        start = max(0, min(current - page // 2, len(rows_s) - page))
        end, view_start = min(len(rows_s), start + page), start
        return start, end
    marker_func = lambda i: (">*" if i == current and row_ids[i] in picked else "> " if i == current else "* " if row_ids[i] in picked else "  ")
    build_row_func = lambda i: ((lambda row: [marker_func(i) + row[0], *row[1:]])(list(rows_s[i])))
    build_rows_func = lambda start, end: [build_row_func(i) for i in range(start, end)]
    build_headers_func = lambda start, end: ((lambda hs: [f"{hs[0]}  ({start+1}-{end}/{len(rows_s)})", *hs[1:]])(list(headers_s)))
    build_table_func = lambda: ((lambda cols, start, end: smarttrunctable(headers=build_headers_func(start, end), rows=build_rows_func(start, end), no_trunc_cols=no_trunc_cols, terminal_right_space_len=terminal_right_space_len, term_width=cols, tablefmt=tablefmt))(ptsizefallback()[0], *computeview()))
    reverse_line_func = lambda line_frags: [(((style + " reverse").strip() if style else "reverse"), text, *rest) for style, text, *rest in line_frags]
    render_block_func = lambda lines, cols, highlight_line=None: [frag for li, line_frags in enumerate(lines) for frag in (truncateandpadline(reverse_line_func(line_frags) if li == highlight_line else line_frags, cols) + [("", "\n")])]
    render_padding_func = lambda n, cols: [frag for _ in range(max(0, n)) for frag in [("", " " * cols), ("", "\n")]]
    render_func = lambda: ((lambda cols, term_lines, frags, help_text: (lambda highlight_line, main_lines, help_lines: render_block_func(main_lines, cols, highlight_line) + render_block_func(help_lines, cols) + render_padding_func(term_lines - len(main_lines) - len(help_lines), cols))(FIRST_DATA_LINE + (current - view_start) * LINES_PER_ROW, list(split_lines(frags)), list(split_lines(to_formatted_text(ANSI(help_text))))))(*ptsizefallback(), to_formatted_text(ANSI(build_table_func())), "\nUse ↑/↓ to move, PgUp/PgDn to jump, <space> toggle, a: all, i: invert, <enter> confirm, q/Esc cancel.\n"))
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
        nonlocal current; _, term_lines = ptsizefallback()
        current = max(0, current - max_visible_rows_func(term_lines))
        invalidate(event)
    @kb.add("pagedown")
    def _(event):
        nonlocal current; _, term_lines = ptsizefallback()
        current = min(len(rows_s) - 1, current + max_visible_rows_func(term_lines))
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
    app = Application(layout=Layout(HSplit([Window(FormattedTextControl(render_func), wrap_lines=False)])), key_bindings=kb, full_screen=True)
    return app.run()