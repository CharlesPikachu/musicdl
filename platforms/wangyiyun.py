# 作者： Charles
# 公众号： Charles的皮卡丘
# 网易云音乐
from Crypto.Cipher import AES
import requests
import os
# import click
import re
import json
import base64
import codecs
import time
import random


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


# 歌曲对象
# songid：音乐ID
# songname：音乐名
# songnum：歌曲编号
# songurl：歌曲下载地址
class Song():
	def __init__(self, songid, songname, songnum, songurl=None):
		self.songid = songid
		self.songname =songname
		self.songnum = songnum
		self.songurl = '' if songurl is None else songurl


# 音乐爬取类
class WYYSpider():
	def __init__(self, timeout=60, cookies_path=None):
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
		self.session = requests.Session()
		self.session.headers.update(self.headers)
		if cookies_path:
			self.session.cookies = self.get_cookies(cookies_path)
		self.download_session = requests.Session()
		self.timeout = timeout
		self.cracker = Cracker()
		self.search_url = 'http://music.163.com/weapi/cloudsearch/get/web?csrf_token='
		self.url = 'http://music.163.com/weapi/song/enhance/player/url?csrf_token='
	# 歌曲搜索
	# keyword：关键词
	# search_type：搜索类型
	# limit：返回结果数量
	def search(self, keyword, search_type, limit=9):
		params = {
				's': keyword,
				'type': search_type,
				'offset': 0,
				'sub': 'false',
				'limit': limit
				}
		res = self.post_request(self.search_url, params)
		try:
			res = self.post_request(self.search_url, params)
			return res
		except:
			return None
	# 根据歌名搜索
	def search_by_songname(self, songname, limit=9):
		result = self.search(songname, search_type=1, limit=limit)
		if result['result']['songCount'] < 1:
			return None
		else:
			songs = result['result']['songs']
			songs_class = []
			songnum = 1
			for s in songs:
				songid, songname = s['id'], s['name']
				song_class = Song(songid=songid, songname=songname, songnum=songnum)
				songnum += 1
				songs_class.append(song_class)
			return songs_class
	# 获得歌曲下载地址
	def get_download_url(self, songid, bit_rate=320000):
		csrf = ''
		params = {
				'ids': [songid],
				'br': bit_rate,
				'csrf_token': csrf
				}
		result = self.post_request(self.url, params)
		songurl = result['data'][0]['url']
		if songurl:
			return songurl
		else:
			return None
	# 根据歌曲下载地址下载歌曲
	def download(self, songurl, songname, songnum, save_file='./results'):
		if not os.path.exists(save_file):
			os.makedirs(save_file)
		try:
			fpath = os.path.join(save_file, str(songnum)+'_'+str(songname)+'.mp3')
		except:
			valid_name = re.sub(r'[<>:"/\\|?*]', '', songname)
			fpath = os.path.join(save_file, str(valid_name), '.mp3')
		res = self.download_session.get(songurl, timeout=self.timeout, stream=True)
		with open(fpath, 'wb') as f:
			f.write(res.content)
		# length = int(res.headers.get('content-length'))
		# label = 'Downloading {}_{} {}kb'.format(songnum, songname, int(length/1024))
		# with click.progressbar(length=length, label=label) as progressbar:
		# 	with open(fpath, 'wb') as f:
		# 		for chunk in res.iter_content(chunk_size=1024):
		# 			if chunk:
		# 				f.write(chunk)
		# 				progressbar.update(1024)
	# 请求函数
	def post_request(self, url, params):
		post_data = self.cracker.get(params)
		res = self.session.post(url, data=post_data, timeout=self.timeout)
		if res.json()['code'] != 200:
			pass
		else:
			return res.json()
	# 获得cookies
	def get_cookies(self, cookies_path):
		f=open(cookies_path, 'r')
		cookies={}
		for line in f.read().split(';'):
			name, value = line.strip().split('=', 1)
			cookies[name]=value
		return cookies


# 下载器类
class wangyiyun():
	def __init__(self, timeout=60, cookies_path=None, save_file='./results'):
		self.spider = WYYSpider(timeout, cookies_path)
		self.save_file = save_file
		self.timeout = timeout
	def get(self, songname, num=1):
		self._download_song(songname, num)
	def _download_song(self, songname, num):
		songs = None
		songs = self.spider.search_by_songname(songname)

		try:
			songs = self.spider.search_by_songname(songname)
		except:
			pass
		if songs != None:
			i = 0
			for song in songs:
				if i == num:
					break
				self._download_by_id(song.songid, song.songname, song.songnum, self.save_file)
				time.sleep(random.random() * 2)
				i += 1
	def _download_by_id(self, songid, songname, songnum, save_file):
		try:
			url = self.spider.get_download_url(songid)
			songname = songname.replace('/', '')
			songname = songname.replace('.', '')
			self.spider.download(url, songname, songnum, save_file)
		except:
			pass