'''
Function:
	qq音乐下载: https://y.qq.com/
Author:
	Charles
微信公众号:
	Charles的皮卡丘
声明:
	代码仅供学习交流, 不得用于商业/非法使用.
'''
import os
import click
import random
import requests
from contextlib import closing


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
class qq():
	def __init__(self):
		self.headers = {
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.146 Safari/537.36',
					'referer': 'http://y.qq.com'
					}
		self.ios_headers = {
							'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
							'referer': 'http://y.qq.com'
							}
		self.search_url = 'https://c.y.qq.com/soso/fcgi-bin/client_search_cp'
		self.mobile_fcg_url = 'https://c.y.qq.com/base/fcgi-bin/fcg_music_express_mobile3.fcg'
		self.download_url_format = 'http://dl.stream.qqmusic.qq.com/{}?vkey={}&guid={}&uin=3051522991&fromtag=64'
		self.fcg_url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?data=%7B%22req%22%3A%7B%22module%22%3A%22CDN.SrfCdnDispatchServer%22%2C%22method%22%3A%22GetCdnDispatch%22%2C%22param%22%3A%7B%7D%7D%2C%22req_0%22%3A%7B%22module%22%3A%22vkey.GetVkeyServer%22%2C%22method%22%3A%22CgiGetVkey%22%2C%22param%22%3A%7B%22guid%22%3A%2200%22%2C%22songmid%22%3A%5B%22{}%22%5D%2C%22songtype%22%3A%5B0%5D%2C%22uin%22%3A%2200%22%7D%7D%7D'
		self.search_results = {}
	'''外部调用'''
	def get(self, mode='search', **kwargs):
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
					songmid, media_mid = self.search_results.get(download_name)
					guid = str(random.randrange(1000000000, 10000000000))
					params = {"guid": guid,
							  "loginUin": "3051522991",
							  "format": "json",
							  "platform": "yqq",
							  "cid": "205361747",
							  "uin": "3051522991",
							  "songmid": songmid,
							  "needNewCode": 0}
					qualities = [("A000", "ape", 800), ("F000", "flac", 800), ("M800", "mp3", 320), ("C400", "m4a", 128), ("M500", "mp3", 128)]
					for quality in qualities:
						params['filename'] = '%s%s.%s' % (quality[0], songmid, quality[1])
						res = requests.get(self.mobile_fcg_url, params=params, headers=self.ios_headers)
						try:
							vkey = res.json().get('data', {}).get('items', [{}])[0].get('vkey', '')
						except:
							vkey = ''
						if vkey:
							download_url = self.download_url_format.format('%s%s.%s' % (quality[0], songmid, quality[1]), vkey, guid)
							res = self.__download(download_name, download_url, savepath, '.'+quality[1])
						else:
							res = False
						if res:
							break
						print('[qq-INFO]: %s-%s下载失败, 将尝试降低歌曲音质重新下载...' % (download_name, quality[0]+quality[1]+str(quality[2])))
					if not res:
						fcg_res = requests.get(self.fcg_url.format(songmid), headers=self.headers)
						fcg_res_json = fcg_res.json()
						download_url = str(fcg_res_json["req"]["data"]["freeflowsip"][0]) + str(fcg_res_json["req_0"]["data"]["midurlinfo"][0]["purl"])
						res = self.__download(download_name, download_url, savepath, '.m4a')
					if res:
						downed_list.append(download_name)
			return downed_list
		else:
			raise ValueError('mode in qq().get must be <search> or <download>...')
	'''下载'''
	def __download(self, download_name, download_url, savepath, extension='.m4a'):
		if not os.path.exists(savepath):
			os.mkdir(savepath)
		download_name = download_name.replace('<', '').replace('>', '').replace('\\', '').replace('/', '') \
									 .replace('?', '').replace(':', '').replace('"', '').replace('：', '') \
									 .replace('|', '').replace('？', '').replace('*', '')
		savename = 'qq_{}'.format(download_name)
		count = 0
		while os.path.isfile(os.path.join(savepath, savename+extension)):
			count += 1
			savename = 'qq_{}_{}'.format(download_name, count)
		savename += extension
		try:
			print('[qq-INFO]: 正在下载 --> %s' % savename.split('.')[0])
			with closing(requests.get(download_url, headers=self.headers, stream=True, verify=False)) as res:
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
	def __searchBySongname(self, songname):
		params = {
					'w': songname,
					'format': 'json',
					'p': 1,
					'n': 15
				}
		res = requests.get(self.search_url, params=params, headers=self.headers)
		results = {}
		for song in res.json()['data']['song']['list']:
			media_mid = song.get('media_mid')
			songmid = song.get('songmid')
			singers = [s.get('name') for s in song.get('singer')]
			singers = ','.join(singers)
			album = song.get('albumname')
			download_name = '%s--%s--%s' % (song.get('songname'), singers, album)
			count = 0
			while download_name in results:
				count += 1
				download_name = '%s(%d)--%s--%s' % (song.get('songname'), count, singers, album)
			results[download_name] = [songmid, media_mid]		
		return results


'''测试用'''
if __name__ == '__main__':
	qq_downloader = qq()
	res = qq_downloader.get(mode='search', songname='那些年')
	qq_downloader.get(mode='download', need_down_list=list(res.keys())[:9])