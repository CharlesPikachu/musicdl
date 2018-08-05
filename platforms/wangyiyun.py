# 作者： Charles
# 公众号： Charles的皮卡丘
# 网易云音乐:
# 	-https://music.163.com/
import os
import re
import json
import time
import click
import urllib
import random
import base64
import codecs
import requests
from Crypto.Cipher import AES
from contextlib import closing


# 用于算post的两个参数
# 具体原理详见知乎：
# https://www.zhihu.com/question/36081767
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
输入:
	-songname: 歌名
	-downnum: 歌曲下载数量
	-savepath: 歌曲保存路径
	-app: Cmd/Demo中使用
返回值:
	-downednum: 歌曲实际下载数量
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
						'Referer': 'http://music.163.com/search/',
						'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.32 Safari/537.36'
						}
		self.search_url = 'http://music.163.com/weapi/cloudsearch/get/web?csrf_token='
		self.player_url = 'http://music.163.com/weapi/song/enhance/player/url?csrf_token='
		self.cracker = Cracker()
		self.search_session = requests.Session()
		self.search_session.headers.update(self.headers)
	# 外部调用
	def get(self, songname, downnum=1, savepath='./results', app='demo'):
		download_names, download_urls = self._search_by_songname(songname, downnum)
		if app == 'demo':
			downednum = self._download_demo(download_names, download_urls, savepath)
		elif app == 'cmd':
			downednum = self._download_cmd(download_names, download_urls, savepath)
		else:
			raise ValueError('app parameter error...')
		return downednum
	# 下载-demo版
	def _download_demo(self, download_names, download_urls, savepath):
		if not os.path.exists(savepath):
			os.mkdir(savepath)
		downed_count = 0
		for i in range(len(download_urls)):
			download_name = download_names[i].replace('/', '').replace('.', '').replace('\\', '').replace(' ', '')
			download_url = download_urls[i]
			savename = 'wangyiyun_{}_{}.mp3'.format(str(i), download_name)
			try:
				# way1:
				urllib.request.urlretrieve(download_url, os.path.join(savepath, savename))
				downed_count += 1
			except:
				try:
					# way2
					with open(os.path.join(savepath, savename), 'wb') as f:
						f.write(requests.get(download_url).content)
					downed_count += 1
				except:
					pass
			time.sleep(random.random())
		return downed_count
	# 下载-cmd版
	def _download_cmd(self, download_names, download_urls, savepath):
		if not os.path.exists(savepath):
			os.mkdir(savepath)
		downed_count = 0
		for i in range(len(download_urls)):
			download_name = download_names[i].replace('/', '').replace('.', '').replace('\\', '').replace(' ', '')
			download_url = download_urls[i]
			savename = 'wangyiyun_{}_{}.mp3'.format(str(i), download_name)
			try:
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
				downed_count += 1
			except:
				pass
			time.sleep(random.random())
		return downed_count
	# 根据歌名搜索
	def _search_by_songname(self, songname, downnum, search_type=1, limit=9, bit_rate=320000, csrf='', timeout=600):
		params1 = {
					's': songname,
					'type': search_type,
					'offset': 0,
					'sub': 'false',
					'limit': limit
				}
		res = self._post_requests(self.search_url, params1, timeout)
		if res is not None:
			if res['result']['songCount'] < 1:
				return None
			else:
				download_names = []
				download_urls = []
				songs = res['result']['songs']
				for song in songs:
					if len(download_urls) == downnum:
						break
					songid, download_name = song['id'], song['name']
					params2 = {
								'ids': [songid],
								'br': bit_rate,
								'csrf_token': csrf
							}
					res = self._post_requests(self.player_url, params2, timeout)
					download_url = res['data'][0]['url']
					if download_url:
						download_names.append(download_name)
						download_urls.append(download_url)
				return download_names, download_urls
		else:
			return None
	# post请求函数
	def _post_requests(self, url, params, timeout):
		post_data = self.cracker.get(params)
		res = self.search_session.post(url, data=post_data, timeout=timeout)
		if res.json()['code'] != 200:
			return None
		else:
			return res.json()


# 测试用
if __name__ == '__main__':
	wangyiyun().get(songname='尾戒', downnum=1, savepath='./results')