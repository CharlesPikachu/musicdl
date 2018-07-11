# 作者： Charles
# 公众号： Charles的皮卡丘
# 千千音乐:
# 	http://music.taihe.com/
import re
import os
import json
import urllib
import requests


'''
输入:
	-songname: 歌名
	-downnum: 歌曲下载数量
	-savepath: 歌曲保存路径
返回值:
	-downednum: 歌曲实际下载数量
'''
class qianqian():
	def __init__(self):
		self.headers = {
						'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36' 
						}
		self.search_url = 'http://music.baidu.com/search'
		self.sid_url = 'http://musicapi.qianqian.com/v1/restserver/ting?method=baidu.ting.song.play&format=jsonp&callback=jQuery17208098337996053833_1513859108469&songid={}&_=1513859109906'
	# 外部调用
	def get(self, songname, downnum=1, savepath='./results'):
		download_names, download_urls = self._search_by_songname(songname, downnum)
		downednum = self._download(download_names, download_urls, savepath)
		return downednum
	# 下载
	def _download(self, download_names, download_urls, savepath):
		if not os.path.exists(savepath):
			os.mkdir(savepath)
		downed_count = 0
		for i in range(len(download_urls)):
			download_name = download_names[i]
			download_url = download_urls[i]
			savename = 'qianqian_{}_{}.mp3'.format(str(i), download_name)
			try:
				# way1:
				urllib.request.urlretrieve(download_url, os.path.join(savepath, savename))
				downed_count += 1
			except:
				try:
					# way2
					with open(os.path.join(savepath, savename), 'wb') as f:
						f.write(requests.get(download_url, headers=self.headers).content)
					downed_count += 1
				except:
					pass
		return min(downed_count, len(download_urls))
	# 根据歌名搜索
	def _search_by_songname(self, songname, downnum):
		data = {
				'key': songname
				}
		res = requests.get(self.search_url, params=data, headers=self.headers)
		sids = re.findall(r'sid&quot;:(\d+),', res.text)
		download_names = []
		download_urls = []
		for sid in sids:
			if len(download_urls) == downnum:
				break
			res = requests.get(self.sid_url.format(sid), headers=self.headers)
			temp = re.findall(r'\((.*)\)', res.text)[0]
			data = json.loads(temp)
			download_name = data['songinfo']['title'].replace("\\", "").replace("/", "").replace(" ", "").replace('.', '')
			download_url = data['bitrate']['file_link']
			download_names.append(download_name)
			download_urls.append(download_url)
		return download_names, download_urls


# 测试用
if __name__ == '__main__':
	qianqian().get(songname='尾戒', downnum=1, savepath='./results')