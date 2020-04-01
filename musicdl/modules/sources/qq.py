'''
Function:
	qq音乐下载: https://y.qq.com/
Author:
	Charles
微信公众号:
	Charles的皮卡丘
'''
import random
import requests
from ..utils.misc import *
from ..utils.downloader import Downloader


'''QQ音乐下载类'''
class qq():
	def __init__(self, config, logger_handle, **kwargs):
		self.source = 'qq'
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
					'w': keyword,
					'format': 'json',
					'p': '1',
					'n': cfg['search_size_per_source']
				}
		response = self.session.get(self.search_url, headers=self.headers, params=params)
		all_items = response.json()['data']['song']['list']
		songinfos = []
		for item in all_items:
			params = {
						'guid': str(random.randrange(1000000000, 10000000000)),
						'loginUin': '3051522991',
						'format': 'json',
						'platform': 'yqq',
						'cid': '205361747',
						'uin': '3051522991',
						'songmid': item['songmid'],
						'needNewCode': '0'
					}
			ext = ''
			download_url = ''
			filesize = '-MB'
			for quality in [("A000", "ape", 800), ("F000", "flac", 800), ("M800", "mp3", 320), ("C400", "m4a", 128), ("M500", "mp3", 128)]:
				params['filename'] = '%s%s.%s' % (quality[0], item['songmid'], quality[1])
				response = self.session.get(self.mobile_fcg_url, headers=self.ios_headers, params=params)
				response_json = response.json()
				if response_json['code'] != 0: continue
				vkey = response_json.get('data', {}).get('items', [{}])[0].get('vkey', '')
				if vkey:
					ext = quality[1]
					download_url = 'http://dl.stream.qqmusic.qq.com/{}?vkey={}&guid={}&uin=3051522991&fromtag=64'.format('%s%s.%s' % (quality[0], item['songmid'], quality[1]), vkey, params['guid'])
					if ext in ['ape', 'flac']:
						filesize = item['size%s' % ext]
					elif ext in ['mp3', 'm4a']:
						filesize = item['size%s' % quality[-1]]
					break
			if not download_url:
				response = self.session.get(self.fcg_url.format(item['songmid']))
				response_json = response.json()
				if response_json['code'] == 0:
					ext = '.m4a'
					download_url = str(response_json["req"]["data"]["freeflowsip"][0]) + str(response_json["req_0"]["data"]["midurlinfo"][0]["purl"])
					filesize = item['size128']
			if (not download_url) or (filesize == '-MB') or (filesize == 0): continue
			filesize = str(round(filesize/1024/1024, 2)) + 'MB'
			duration = int(item.get('interval', 0))
			songinfo = {
						'source': self.source,
						'songid': str(item['songmid']),
						'singers': filterBadCharacter(','.join([s.get('name', '') for s in item.get('singer', [])])),
						'album': filterBadCharacter(item.get('albumname', '-')),
						'songname': filterBadCharacter(item.get('songname', '-')),
						'savedir': cfg['savedir'],
						'savename': '_'.join([self.source, filterBadCharacter(item.get('songname', '-'))]),
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
		self.ios_headers = {
							'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
							'Referer': 'http://y.qq.com'
						}
		self.headers = {
						'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.146 Safari/537.36',
						'Referer': 'http://y.qq.com'
					}
		self.search_url = 'https://c.y.qq.com/soso/fcgi-bin/client_search_cp'
		self.mobile_fcg_url = 'https://c.y.qq.com/base/fcgi-bin/fcg_music_express_mobile3.fcg'
		self.fcg_url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?data=%7B%22req%22%3A%7B%22module \
						%22%3A%22CDN.SrfCdnDispatchServer%22%2C%22method%22%3A%22GetCdnDispatch \
						%22%2C%22param%22%3A%7B%7D%7D%2C%22req_0%22%3A%7B%22module%22%3A%22vkey. \
						GetVkeyServer%22%2C%22method%22%3A%22CgiGetVkey%22%2C%22param%22%3A%7B%22 \
						guid%22%3A%2200%22%2C%22songmid%22%3A%5B%22{}%22%5D%2C%22songtype%22%3A%5 \
						B0%5D%2C%22uin%22%3A%2200%22%7D%7D%7D'