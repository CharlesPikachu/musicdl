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
def printtable(titles, items):
    assert isinstance(titles, collections.abc.Sequence) and isinstance(items, collections.abc.Sequence), 'title and items should be iterable'
    table = PrettyTable(titles)
    for item in items: table.add_row(item)
    print(table)
    return table


'''colorize'''
def colorize(string, color):
    string = str(string)
    if color not in COLORS: return string
    return COLORS[color] + string + '\033[0m'


'''printfullline'''
def printfullline(ch: str = "*", end: str = '\n'):
    cols = shutil.get_terminal_size().columns
    print(ch * cols, end=end)