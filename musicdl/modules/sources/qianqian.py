'''
Function:
	千千音乐下载: http://music.taihe.com/
Author:
	Charles
微信公众号:
	Charles的皮卡丘
'''
import requests
from ..utils.misc import *
from ..utils.downloader import Downloader


'''千千音乐下载类'''
class qianqian():
	def __init__(self, config, logger_handle, **kwargs):
		self.source = 'qianqian'
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
					'query': keyword,
					'method': 'baidu.ting.search.common',
					'format': 'json',
					'page_no': '1',
					'page_size': cfg['search_size_per_source']
				}
		response = self.session.get(self.search_url, headers=self.headers, params=params)
		all_items = response.json()['song_list']
		songinfos = []
		for item in all_items:
			params = {
						'songIds': item['song_id']
					}
			response = self.session.get(self.player_url, headers=self.headers, params=params)
			response_json = response.json()
			if response_json.get('errorCode') != 22000: continue
			song_list = response_json['data']['songList']
			if not song_list: continue
			download_url = song_list[0]['songLink']
			if not download_url: continue
			filesize = str(round(int(song_list[0]['size'])/1024/1024, 2)) + 'MB'
			ext = song_list[0]['format']
			duration = int(song_list[0].get('time', 0))
			songinfo = {
						'source': self.source,
						'songid': str(item['song_id']),
						'singers': filterBadCharacter(item.get('author', '-')),
						'album': filterBadCharacter(item.get('album_title', '-')),
						'songname': filterBadCharacter(item.get('title', '-')).split('–')[0].strip(),
						'savedir': cfg['savedir'],
						'savename': '_'.join([self.source, filterBadCharacter(item.get('title', '-')).split('–')[0].strip()]),
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
						'Referer': 'http://music.baidu.com/'
					}
		self.search_url = 'http://musicapi.qianqian.com/v1/restserver/ting'
		self.player_url = 'http://music.baidu.com/data/music/links'