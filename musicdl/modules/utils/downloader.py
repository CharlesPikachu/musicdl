'''
Function:
	下载器类
Author:
	Charles
微信公众号:
	Charles的皮卡丘
'''
import click
import warnings
import requests
from .misc import *
from contextlib import closing
warnings.filterwarnings('ignore')


'''下载器类'''
class Downloader():
	def __init__(self, songinfo, session=None, **kwargs):
		self.songinfo = songinfo
		self.session = requests.Session() if session is None else session
		self.__initialize(songinfo['source'])
	'''外部调用'''
	def start(self):
		songinfo, session, headers = self.songinfo, self.session, self.headers
		checkDir(songinfo['savedir'])
		try:
			is_success = False
			with closing(session.get(songinfo['download_url'], headers=headers, stream=True, verify=False)) as response:
				total_size = int(response.headers['content-length'])
				chunk_size = 1024
				if response.status_code == 200:
					label = '[FileSize]: %0.2fMB' % (total_size/1024/1024)
					with click.progressbar(length=total_size, label=label) as progressbar:
						with open(os.path.join(songinfo['savedir'], songinfo['savename']+'.'+songinfo['ext']), "wb") as fp:
							for chunk in response.iter_content(chunk_size=chunk_size):
								if chunk:
									fp.write(chunk)
									progressbar.update(chunk_size)
					is_success = True
		except:
			is_success = False
		return is_success
	'''初始化'''
	def __initialize(self, source):
		if source == 'baiduFlac':
			self.headers = {
							'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
							'Referer': 'http://music.baidu.com/'
						}
		elif source == 'kugou':
			self.headers = {
							'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.146 Safari/537.36',
							'Host': 'webfs.yun.kugou.com',
							'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
							'Accept-Encoding': 'gzip, deflate, br',
							'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
							'Cache-Control': 'max-age=0',
							'Connection': 'keep-alive'
						}
		elif source == 'kuwo':
			self.headers = {
							'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
						}
		elif source == 'netease':
			self.headers = {}
		elif source == 'qianqian':
			self.headers = {
							'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
							'Referer': 'http://music.baidu.com/'
						}
		elif source == 'qq':
			self.headers = {
							'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.146 Safari/537.36',
							'Referer': 'http://y.qq.com'
						}
		elif source == 'migu':
			self.headers = {
							'Referer': 'https://m.music.migu.cn/', 
							'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.75 Mobile Safari/537.36'
						}
		elif source == 'xiami':
			self.headers = {
							'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36'
						}
		elif source == 'joox':
			self.headers = {
							'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/605.1.15 (KHTML, like Gecko)'
						}
		else:
			raise ValueError('Unsupport download music from source <%s>...' % source)