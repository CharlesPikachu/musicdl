'''
Function:
    一些终端打印工具
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import logging
from prettytable import PrettyTable


'''定义终端颜色'''
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


'''打印日志类'''
class Logger():
    def __init__(self, logfilepath, **kwargs):
        setattr(self, 'logfilepath', logfilepath)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[logging.FileHandler(logfilepath, encoding='utf-8'), logging.StreamHandler()],
        )
    '''log'''
    @staticmethod
    def log(level, message):
        logging.log(level, message)
    '''debug'''
    def debug(self, message, disable_print=False):
        if disable_print:
            fp = open(self.logfilepath, 'a', encoding='utf-8')
            fp.write(message + '\n')
        else:
            Logger.log(logging.DEBUG, message)
    '''info'''
    def info(self, message, disable_print=False):
        if disable_print:
            fp = open(self.logfilepath, 'a', encoding='utf-8')
            fp.write(message + '\n')
        else:
            Logger.log(logging.INFO, message)
    '''warning'''
    def warning(self, message, disable_print=False):
        if disable_print:
            fp = open(self.logfilepath, 'a', encoding='utf-8')
            fp.write(message + '\n')
        else:
            if '\033[31m' not in message:
                message = colorize(message, 'red')
            Logger.log(logging.WARNING, message)
    '''error'''
    def error(self, message, disable_print=False):
        if disable_print:
            fp = open(self.logfilepath, 'a', encoding='utf-8')
            fp.write(message + '\n')
        else:
            if '\033[31m' not in message:
                message = colorize(message, 'red')
            Logger.log(logging.ERROR, message)


'''打印表格'''
def printTable(title, items):
    assert isinstance(title, list) and isinstance(items, list), 'title and items should be list'
    table = PrettyTable(title)
    for item in items: table.add_row(item)
    print(table)
    return table


'''给终端文字上色'''
def colorize(string, color):
    string = str(string)
    if color not in COLORS: return string
    return COLORS[color] + string + '\033[0m'