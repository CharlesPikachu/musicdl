# 作者： Charles
# 公众号： Charles的皮卡丘
# 酷我音乐:
# 	-http://yinyue.kuwo.cn/
import re
import os
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
class kuwo():
	def __init__(self):
		self.headers = {
						'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36' 
						}
		self.search_url = 'http://sou.kuwo.cn/ws/NSearch?type=all&catalog=yueku2016&key={}'
		self.player_url = 'http://player.kuwo.cn/webmusic/st/getNewMuiseByRid?rid=MUSIC_{}'
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
			download_name = download_names[i].replace("<\\/em>", "").replace("<em>", "").replace('\\', '').replace('/', '').replace(" ", "").replace('.', '')
			download_url = download_urls[i]
			savename = 'kuwo_{}_{}.mp3'.format(str(i), download_name)
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
		return min(downed_count, len(download_urls))
	# 根据歌名搜索
	def _search_by_songname(self, songname, downnum):
		res = requests.get(self.search_url.format(songname), headers=self.headers)
		songinfos = re.findall(r'<a href="http://www\.kuwo\.cn/yinyue/(.*?)/" title="(.*?)" target="_blank">', res.text)
		download_names = []
		download_urls = []
		for songinfo in songinfos:
			if len(download_urls) == downnum:
				break
			download_name = songinfo[1].replace('&nbsp;', '').replace('\\', '').replace('/', '').replace(" ", "").replace('.', '')
			songid = songinfo[0]
			res = requests.get(self.player_url.format(songid), headers=self.headers)
			mp3dl = re.findall(r'<mp3dl>(.*?)</mp3dl>', res.text)[0]
			mp3path = re.findall(r'<mp3path>(.*?)</mp3path>', res.text)[0]
			download_url = 'http://' + mp3dl + '/resource/' + mp3path
			download_names.append(download_name)
			download_urls.append(download_url)
		return download_names, download_urls


# 测试用
if __name__ == '__main__':
	kuwo().get('尾戒', downnum=1, savepath='./results')