'''
Function:
	网易云音乐下载: https://music.163.com/
Author:
	Charles
微信公众号:
	Charles的皮卡丘
声明:
	代码仅供学习交流, 不得用于商业/非法使用.
'''
import os
import json
import time
import click
import random
import base64
import codecs
import requests
from Crypto.Cipher import AES
from contextlib import closing


'''
Function:
	用于算post的两个参数, 具体原理详见知乎：
	https://www.zhihu.com/question/36081767
'''
class Cracker():
	def __init__(self):
		self.modulus = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'
		self.nonce = '0CoJUm6Qyw8W8jud'
		self.pubKey = '010001'
	def get(self, text):
		text = json.dumps(text)
		secKey = self._createSecretKey(16)
		encText = self._aesEncrypt(self._aesEncrypt(text, self.nonce), secKey)
		encSecKey = self._rsaEncrypt(secKey, self.pubKey, self.modulus)
		post_data = {
					'params': encText,
					'encSecKey': encSecKey
					}
		return post_data
	def _aesEncrypt(self, text, secKey):
		pad = 16 - len(text) % 16
		if isinstance(text, bytes):
			text = text.decode('utf-8')
		text = text + str(pad * chr(pad))
		secKey = secKey.encode('utf-8')
		encryptor = AES.new(secKey, 2, b'0102030405060708')
		text = text.encode('utf-8')
		ciphertext = encryptor.encrypt(text)
		ciphertext = base64.b64encode(ciphertext)
		return ciphertext
	def _rsaEncrypt(self, text, pubKey, modulus):
		text = text[::-1]
		rs = int(codecs.encode(text.encode('utf-8'), 'hex_codec'), 16) ** int(pubKey, 16) % int(modulus, 16)
		return format(rs, 'x').zfill(256)
	def _createSecretKey(self, size):
		return (''.join(map(lambda xx: (hex(ord(xx))[2:]), str(os.urandom(size)))))[0:16]


'''
Input:
	-mode: search(搜索模式)/download(下载模式)
		--search模式:
			----songname: 搜索的歌名
		--download模式:
			----need_down_list: 需要下载的歌曲名列表
			----savepath: 下载歌曲保存路径
Return:
	-search模式:
		--search_results: 搜索结果
	-download模式:
		--downed_list: 成功下载的歌曲名列表
'''
class wangyiyun():
	def __init__(self):
		self.headers = {
						'Accept': '*/*',
						'Accept-Encoding': 'gzip,deflate,sdch',
						'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
						'Connection': 'keep-alive',
						'Content-Type': 'application/x-www-form-urlencoded',
						'Host': 'music.163.com',
						'cookie': '_iuqxldmzr_=32; _ntes_nnid=0e6e1606eb78758c48c3fc823c6c57dd,1527314455632; '
								'_ntes_nuid=0e6e1606eb78758c48c3fc823c6c57dd; __utmc=94650624; __utmz=94650624.1527314456.1.1.'
								'utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); WM_TID=blBrSVohtue8%2B6VgDkxOkJ2G0VyAgyOY;'
								' JSESSIONID-WYYY=Du06y%5Csx0ddxxx8n6G6Dwk97Dhy2vuMzYDhQY8D%2BmW3vlbshKsMRxS%2BJYEnvCCh%5CKY'
								'x2hJ5xhmAy8W%5CT%2BKqwjWnTDaOzhlQj19AuJwMttOIh5T%5C05uByqO%2FWM%2F1ZS9sqjslE2AC8YD7h7Tt0Shufi'
								'2d077U9tlBepCx048eEImRkXDkr%3A1527321477141; __utma=94650624.1687343966.1527314456.1527314456'
								'.1527319890.2; __utmb=94650624.3.10.1527319890',
						'Origin': 'https://music.163.com',
						'Referer': 'https://music.163.com/',
						'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.32 Safari/537.36'
						}
		self.search_url = 'http://music.163.com/weapi/cloudsearch/get/web?csrf_token='
		self.player_url = 'http://music.163.com/weapi/song/enhance/player/url?csrf_token='
		self.cracker = Cracker()
		self.session = requests.Session()
		self.session.headers.update(self.headers)
		self.search_results = {}
	'''外部调用'''
	def get(self, mode='search', bit_rate=320000, csrf='', timeout=600, **kwargs):
		if mode == 'search':
			songname = kwargs.get('songname')
			self.search_results = self.__searchBySongname(songname)
			return self.search_results
		elif mode == 'download':
			need_down_list = kwargs.get('need_down_list')
			downed_list = []
			savepath = kwargs.get('savepath') if kwargs.get('savepath') is not None else './results'
			if need_down_list is not None:
				for download_name in need_down_list:
					songid = self.search_results.get(download_name)
					params2 = {
								'ids': [songid],
								'br': bit_rate,
								'csrf_token': csrf
							}
					res = self.__postRequests(self.player_url, params2, timeout)
					try:
						download_url = res['data'][0]['url']
					except:
						download_url = self.song_url.format(songid)
					res = self.__download(download_name, download_url, savepath)
					if res:
						downed_list.append(download_name)
						time.sleep(random.random())
			return downed_list
		else:
			raise ValueError('mode in wangyiyun().get must be <search> or <download>...')
	'''下载'''
	def __download(self, download_name, download_url, savepath):
		if not os.path.exists(savepath):
			os.mkdir(savepath)
		download_name = download_name.replace('<', '').replace('>', '').replace('\\', '').replace('/', '') \
									 .replace('?', '').replace(':', '').replace('"', '').replace('：', '') \
									 .replace('|', '').replace('？', '').replace('*', '')
		savename = 'wangyiyun_{}'.format(download_name)
		count = 0
		while os.path.isfile(os.path.join(savepath, savename+'.mp3')):
			count += 1
			savename = 'wangyiyun_{}_{}'.format(download_name, count)
		savename += '.mp3'
		try:
			print('[wangyiyun-INFO]: 正在下载 --> %s' % savename.split('.')[0])
			with closing(requests.get(download_url, stream=True, verify=False)) as res:
				total_size = int(res.headers['content-length'])
				if res.status_code == 200:
					label = '[FileSize]:%0.2f MB' % (total_size/(1024*1024))
					with click.progressbar(length=total_size, label=label) as progressbar:
						with open(os.path.join(savepath, savename), "wb") as f:
							for chunk in res.iter_content(chunk_size=1024):
								if chunk:
									f.write(chunk)
									progressbar.update(1024)
				else:
					raise RuntimeError('Connect error...')
			return True
		except:
			return False
	'''根据歌名搜索'''
	def __searchBySongname(self, songname, search_type=1, limit=9, timeout=600):
		params1 = {
					's': songname,
					'type': search_type,
					'offset': 0,
					'sub': 'false',
					'limit': limit
				}
		res = self.__postRequests(self.search_url, params1, timeout)
		results = {}
		if res is not None:
			if res['result']['songCount'] >= 1:
				songs = res['result']['songs']
				for song in songs:
					songid = song.get('id')
					singers = [each.get('name') for each in song.get('ar')]
					singers = ','.join(singers)
					album = song.get('al').get('name')
					download_name = '%s--%s--%s' % (song.get('name'), singers, album)
					count = 0
					while download_name in results:
						count += 1
						download_name = '%s(%d)--%s--%s' % (song.get('name'), count, singers, album)
					results[download_name] = songid
		return results
	'''post请求函数'''
	def __postRequests(self, url, params, timeout):
		post_data = self.cracker.get(params)
		res = self.session.post(url, data=post_data, timeout=timeout, headers=self.headers)
		if res.json()['code'] != 200:
			return None
		else:
			return res.json()


'''测试用'''
if __name__ == '__main__':
	wangyiyun_downloader = wangyiyun()
	res = wangyiyun_downloader.get(mode='search', songname='尾戒')
	wangyiyun_downloader.get(mode='download', need_down_list=list(res.keys())[:2])