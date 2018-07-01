# 作者： Charles
# 公众号： Charles的皮卡丘
# 酷狗音乐
import re
import os
import urllib
import requests


'''
输入参数:
	-songname: 歌名
	-downnum: 歌曲下载数量
	-savepath: 歌曲保存路径
返回值:
	-downednum: 歌曲实际下载数量
'''
class kugou():
	def __init__(self):
		self.headers = {
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.146 Safari/537.36'
					}
		self.search_url = 'http://songsearch.kugou.com/song_search_v2?keyword={}&page=1&pagesize=30'
		self.hash_url = 'http://www.kugou.com/yy/index.php?r=play/getdata&hash={}'
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
			savename = 'kugou_{}_{}.mp3'.format(str(i), download_name)
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
		filehashs = re.findall('"FileHash":"(.*?)"', res.text)
		download_names = re.findall('"SongName":"(.*?)"', res.text)
		download_urls = []
		for filehash in filehashs:
			if len(download_urls) == downnum:
				break
			res = requests.get(self.hash_url.format(filehash))
			paly_url = re.findall('"play_url":"(.*?)"', res.text)[0]
			download_url = paly_url.replace("\\", "")
			download_urls.append(download_url)
		return download_names, download_urls


# 测试用
if __name__ == '__main__':
	kugou().get(songname='尾戒', downnum=1, savepath='./results')