'''
Function:
	酷我音乐下载: http://www.kuwo.cn/
Author:
	Charles
微信公众号:
	Charles的皮卡丘
'''
import time
import requests
from ..utils.misc import *
from ..utils.downloader import Downloader


'''酷我音乐下载类'''
class kuwo():
	def __init__(self, config, logger_handle, **kwargs):
		self.source = 'kuwo'
		self.session = requests.Session()
		self.session.proxies.update(config['proxies'])
		self.config = config
		self.logger_handle = logger_handle
		self.__initialize()
	'''歌曲搜索'''
	def search(self, keyword):
		self.logger_handle.info('正在%s中搜索 ——> %s...' % (self.source, keyword))
		cfg = self.config.copy()
		params = {
					'key': keyword,
					'pn': '1',
					'rn': cfg['search_size_per_source'],
					'reqId': 'ffa3dc80-73c2-11ea-a715-7de8a8cc7b68'
				}
		response = self.session.get(self.search_url, headers=self.headers, params=params)
		all_items = response.json()['data']['list']
		songinfos = []
		for item in all_items:
			params = {
						'format': 'mp3',
						'rid': str(item['rid']),
						'response': 'url',
						'type': 'convert_url3',
						'br': '128kmp3',
						'from': 'web',
						't': str(int(time.time()*1000)),
						'reqId': 'de97aac1-73c3-11ea-a715-7de8a8cc7b68'
					}
			response = self.session.get(self.player_url, headers=self.headers, params=params)
			response_json = response.json()
			if response_json.get('code') != 200: continue
			download_url = response_json['url']
			if not download_url: continue
			filesize = '-MB'
			ext = download_url.split('.')[-1]
			duration = int(item.get('duration', 0))
			songinfo = {
						'source': self.source,
						'songid': str(item['rid']),
						'singers': filterBadCharacter(item.get('artist', '-')),
						'album': filterBadCharacter(item.get('album', '-')),
						'songname': filterBadCharacter(item.get('name', '-')),
						'savedir': cfg['savedir'],
						'savename': '_'.join([self.source, filterBadCharacter(item.get('name', '-'))]),
						'download_url': download_url,
						'filesize': filesize,
						'ext': ext,
						'duration': seconds2hms(duration)
					}
			songinfos.append(songinfo)
		return songinfos
	'''歌曲下载'''
	def download(self, songinfos):
		for songinfo in songinfos:
			self.logger_handle.info('正在从%s下载 ——> %s...' % (self.source, songinfo['savename']))
			task = Downloader(songinfo, self.session)
			if task.start():
				self.logger_handle.info('成功从%s下载到了 ——> %s...' % (self.source, songinfo['savename']))
			else:
				self.logger_handle.info('无法从%s下载 ——> %s...' % (self.source, songinfo['savename']))
	'''初始化'''
	def __initialize(self):
		self.headers = {
						'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
						'csrf': '0HQ0UGKNAKR',
						'Host': 'www.kuwo.cn',
						'Referer': 'http://www.kuwo.cn/search/list',
						'Cookie': 'kw_token=0HQ0UGKNAKR;'
					}
		self.search_url = 'http://www.kuwo.cn/api/www/search/searchMusicBykeyWord'
		self.player_url = 'http://www.kuwo.cn/url'