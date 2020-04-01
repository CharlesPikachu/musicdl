'''
Function:
	虾米音乐下载: https://www.xiami.com/
Author:
	Charles
微信公众号:
	Charles的皮卡丘
'''
import requests
from ..utils.misc import *
from ..utils.downloader import Downloader


'''虾米音乐下载类'''
class xiami():
	def __init__(self, config, logger_handle, **kwargs):
		self.source = 'xiami'
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
						'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) XIAMI-MUSIC/3.1.1 Chrome/56.0.2924.87 Electron/1.6.11 Safari/537.36',
						'Cookie': '_m_h5_tk=15d3402511a022796d88b249f83fb968_1511163656929; _m_h5_tk_enc=b6b3e64d81dae577fc314b5c5692df3c'
					}
		self.search_url = 'https://acs.m.xiami.com/h5/mtop.alimusic.search.searchservice.searchsongs/1.0/'