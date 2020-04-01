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


'''打印日志类'''
class Logger():
	def __init__(self, logfilepath, **kwargs):
		logging.basicConfig(level=logging.INFO,
							format='%(asctime)s %(levelname)-8s %(message)s',
							datefmt='%Y-%m-%d %H:%M:%S',
							handlers=[logging.FileHandler(logfilepath),
									  logging.StreamHandler()])
	@staticmethod
	def log(level, message):
		logging.log(level, message)
	@staticmethod
	def debug(message):
		Logger.log(logging.DEBUG, message)
	@staticmethod
	def info(message):
		Logger.log(logging.INFO, message)
	@staticmethod
	def warning(message):
		Logger.log(logging.WARNING, message)
	@staticmethod
	def error(message):
		Logger.log(logging.ERROR, message)


'''打印表格'''
def printTable(title, items):
	assert isinstance(title, list) and isinstance(items, list), '<title> and <items> should be list in printTable...'
	table = PrettyTable(title)
	for item in items: table.add_row(item)
	print(table)
	return table