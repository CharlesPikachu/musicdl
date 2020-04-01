'''
Function:
	酷狗音乐下载: http://www.kugou.com/
Author:
	Charles
微信公众号:
	Charles的皮卡丘
'''
import requests
from ..utils.misc import *
from ..utils.downloader import Downloader


'''酷狗音乐下载类'''
class kugou():
	def __init__(self, config, logger_handle, **kwargs):
		self.source = 'kugou'
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
					'keyword': keyword,
					'page': '1',
					'pagesize': cfg['search_size_per_source']
				}
		response = self.session.get(self.search_url, headers=self.headers, params=params)
		all_items = response.json()['data']['lists']
		songinfos = []
		for item in all_items:
			params = {
						'r': 'play/getdata',
						'hash': str(item['FileHash']),
						'album_id': str(item['AlbumID']),
						'dfid': '',
						'mid': 'ccbb9592c3177be2f3977ff292e0f145',
						'platid': '4'
					}
			response = self.session.get(self.hash_url, headers=self.headers, params=params)
			response_json = response.json()
			if response_json.get('err_code') != 0: continue
			download_url = response_json['data']['play_url'].replace('\\', '')
			if not download_url: continue
			filesize = str(round(int(response_json['data']['filesize'])/1024/1024, 2)) + 'MB'
			ext = download_url.split('.')[-1]
			duration = int(item.get('Duration', 0))
			songinfo = {
						'source': self.source,
						'songid': str(item['ID']),
						'singers': filterBadCharacter(item.get('SingerName', '-')),
						'album': filterBadCharacter(item.get('AlbumName', '-')),
						'songname': filterBadCharacter(item.get('SongName', '-')),
						'savedir': cfg['savedir'],
						'savename': '_'.join([self.source, filterBadCharacter(item.get('SongName', '-'))]),
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
						'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
					}
		self.search_url = 'http://songsearch.kugou.com/song_search_v2'
		self.hash_url = 'https://wwwapi.kugou.com/yy/index.php'