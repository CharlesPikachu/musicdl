# 作者： Charles
# 公众号： Charles的皮卡丘
# 千千音乐
import requests
import json
import re
import os


class qianqian():
	def __init__(self):
		self.headers = {
						'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36' 
						}
		self.search_url = 'http://music.baidu.com/search'
		self.download_url = 'http://musicapi.qianqian.com/v1/restserver/ting?method=baidu.ting.song.play&format=jsonp&callback=jQuery17208098337996053833_1513859108469&songid={}&_=1513859109906'
	def get(self, songname, num=1):
		# 获得sids
		data = {
				'key': songname
				}
		res = requests.get(self.search_url, params=data, headers=self.headers)
		sids = re.findall(r'sid&quot;:(\d+),', res.text)
		i = 0
		for sid in sids:
			if i == num:
				break
			self._download(sid)
			i += 1
	def _download(self, sid, savepath='./results'):
		if not os.path.exists(savepath):
			os.mkdir(savepath)
		res = requests.get(self.download_url.format(sid), headers=self.headers)
		temp = re.findall(r'\((.*)\)', res.text)[0]
		data = json.loads(temp)
		mp3_name = data['songinfo']['title'].replace("\\", "").replace("/", "").replace(" ", "")
		mp3_url = data['bitrate']['file_link']
		res = requests.get(mp3_url, headers=self.headers)
		filename = '{}.mp3'.format(mp3_name+'_'+sid)
		with open(os.path.join(savepath, filename), 'wb') as f:
			f.write(res.content)