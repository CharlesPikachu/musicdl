# 作者： Charles
# 公众号： Charles的皮卡丘
# 酷我音乐
import re
import os
import requests


class kuwo():
	def __init__(self):
		self.headers = {
						'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36' 
						}
		self.search_url = ''
		self.download_url = ''
	def get(self, songname, num=1):
		pass
	def _search(self, songname):
		pass
	def _download(self, savepath='./results'):
		if not os.path.exists(savepath):
			os.mkdir(savepath)
