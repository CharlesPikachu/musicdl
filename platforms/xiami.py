# 作者： Charles
# 公众号： Charles的皮卡丘
# 虾米音乐:
# 	-https://www.xiami.com/
import re
import os
import json
import click
import urllib
import requests
from contextlib import closing
try:
	from urllib.parse import unquote
except ImportError:
	from urllib import unquote


# 破解虾米URL加密
class ParseURL():
	def __init__(self):
		pass
	def parse(self, location):
		rows, encryptUrl = int(location[:1]), location[1:]
		encryptUrlLen = len(encryptUrl)
		cols_base = encryptUrlLen // rows
		rows_ex = encryptUrlLen % rows
		matrix = []
		for row in range(rows):
			length = cols_base + 1 if row < rows_ex else cols_base
			matrix.append(encryptUrl[:length])
			encryptUrl = encryptUrl[length:]
		decryptUrl = ''
		for i in range(encryptUrlLen):
			decryptUrl += matrix[i % rows][i // rows]
		decryptUrl = unquote(decryptUrl).replace('^', '0')
		return 'https:' + decryptUrl


'''
输入:
	-songname: 歌名
	-downnum: 歌曲下载数量
	-savepath: 歌曲保存路径
	-app: Cmd/Demo中使用
返回值:
	-downednum: 歌曲实际下载数量
'''
class xiami():
	def __init__(self):
		self.headers = {
						'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
						'Referer': 'http://www.xiami.com/song/play'
						}
		self.search_url = 'https://www.xiami.com/search?key={}'
		self.playlist_url = 'http://www.xiami.com/song/playlist/id/{}/object_name/default/object_id/0/cat/json'
		self.parser = ParseURL()
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
			download_name = download_names[i].replace("<\\/em>", "").replace("<em>", "").replace('\\', '').replace('/', '').replace(" ", "").replace('.', '')
			download_url = download_urls[i]
			savename = 'xiami_{}_{}.mp3'.format(str(i), download_name)
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
		return downed_count
	# 下载-cmd版
	def _download_cmd(self, download_names, download_urls, savepath):
		if not os.path.exists(savepath):
			os.mkdir(savepath)
		downed_count = 0
		for i in range(len(download_urls)):
			download_name = download_names[i].replace("<\\/em>", "").replace("<em>", "").replace('\\', '').replace('/', '').replace(" ", "").replace('.', '')
			download_url = download_urls[i]
			savename = 'xiami_{}_{}.mp3'.format(str(i), download_name)
			try:
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
				downed_count += 1
			except:
				pass
		return downed_count
	# 根据歌名搜索
	def _search_by_songname(self, songname, downnum):
		res = requests.get(self.search_url.format(songname), headers=self.headers)
		songids = re.findall(r'onclick="play\(\'(.*?)\',', res.text)
		download_names = []
		download_urls = []
		for songid in songids:
			if len(download_urls) == downnum:
				break
			res = requests.get(self.playlist_url.format(songid), headers=self.headers)
			songinfos = json.loads(res.text)
			download_name = songinfos['data']['trackList'][0]['songName']
			location = songinfos['data']['trackList'][0]['location']
			download_url = self.parser.parse(location)
			download_names.append(download_name)
			download_urls.append(download_url)
		return download_names, download_urls


# 测试用
if __name__ == '__main__':
	xiami().get('尾戒', downnum=1, savepath='./results')