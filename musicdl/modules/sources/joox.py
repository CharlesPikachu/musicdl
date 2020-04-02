'''
Function:
	JOOX音乐下载: https://www.joox.com/cn/login
Author:
	Charles
微信公众号:
	Charles的皮卡丘
'''
import json
import base64
import requests
from ..utils.misc import *
from ..utils.downloader import Downloader


'''JOOX音乐下载类'''
class joox():
	def __init__(self, config, logger_handle, **kwargs):
		self.source = 'joox'
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
					'country': 'hk',
					'lang': 'zh_TW',
					'search_input': keyword,
					'sin': '0',
					'ein': cfg['search_size_per_source']
				}
		response = self.session.get(self.search_url, headers=self.headers, params=params)
		all_items = response.json()['itemlist']
		songinfos = []
		for item in all_items:
			params = {
						'songid': item['songid']
					}
			response = self.session.get(self.songinfo_url, headers=self.headers, params=params)
			response_json = response.json()
			if response_json.get('code') != 0: continue
			for q_key in [('r320Url', '320'), ('r192Url', '192'), ('mp3Url', '128')]:
				download_url = response_json.get(q_key[0], '')
				if not download_url: continue
				filesize = str(round(int(json.loads(response_json['kbps_map'])[q_key[1]])/1024/1024, 2)) + 'MB'
				ext = 'mp3' if q_key[0] in ['r320Url', 'mp3Url'] else 'm4a'
			if not download_url: continue
			duration = int(item.get('playtime', 0))
			songinfo = {
						'source': self.source,
						'songid': str(item['songid']),
						'singers': filterBadCharacter(','.join([base64.b64decode(s['name']).decode('utf-8') for s in item.get('singer_list', [])])),
						'album': filterBadCharacter(response_json.get('malbum', '-')),
						'songname': filterBadCharacter(response_json.get('msong', '-')),
						'savedir': cfg['savedir'],
						'savename': '_'.join([self.source, filterBadCharacter(response_json.get('msong', '-'))]),
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
						'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/605.1.15 (KHTML, like Gecko)'
					}
		self.search_url = 'https://api-jooxtt.sanook.com/web-fcgi-bin/web_search'
		self.songinfo_url = 'https://api-jooxtt.sanook.com/web-fcgi-bin/web_get_songinfo'