# 作者： Charles
# 公众号： Charles的皮卡丘
# qq音乐
import os
import re
import time
import urllib
import random
import requests


'''
输入:
	-songname: 歌名
	-downnum: 歌曲下载数量
	-savepath: 歌曲保存路径
返回值:
	-downednum: 歌曲实际下载数量
'''
class qq():
	def __init__(self):
		self.headers = {
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.146 Safari/537.36'
					}
		self.search_url = 'https://c.y.qq.com/soso/fcgi-bin/client_search_cp?ct=24&qqmusic_ver=1298&new_json=1&remoteplace=txt.yqq.top&searchid=34725291680541638&t=0&aggr=1&cr=1&catZhida=1&lossless=0&flag_qc=0&p=1&n=20&w={}&g_tk=5381&jsonpCallback=MusicJsonCallback703296236531272&loginUin=0&hostUin=0&format=jsonp&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0'
		self.fcg_url = 'https://c.y.qq.com/base/fcgi-bin/fcg_music_express_mobile3.fcg?g_tk=5381&jsonpCallback=MusicJsonCallback9239412173137234&loginUin=0&hostUin=0&format=json&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0&cid=205361747&callback=MusicJsonCallback9239412173137234&uin=0&songmid={}&filename={}.m4a&guid=8208467632'
		self.download_format_url = 'http://dl.stream.qqmusic.qq.com/{}.m4a?vkey={}&guid=8208467632&uin=0&fromtag=66'
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
			savename = 'qq_{}_{}.m4a'.format(str(i), download_name)
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
			time.sleep(random.random())
		return min(downed_count, len(download_urls))
	# 根据歌名搜索
	def _search_by_songname(self, songname, downnum):
		res = requests.get(self.search_url.format(songname), headers=self.headers).text
		media_mid_temp = re.findall('"media_mid":"(.*?)"', res)
		media_mids = []
		for i in range(len(media_mid_temp)):
			media_mids.append('C400'+media_mid_temp[i])
		songmids = re.findall('"lyric_hilight":".*?","mid":"(.*?)","mv"', res)
		temp_names = re.findall('},"name":"(.*?)","newStatus"', res)
		download_names = []
		download_urls = []
		for i in range(len(media_mids)):
			if len(download_urls) == downnum:
				break
			try:
				fcg_res = requests.get(self.fcg_url.format(songmids[i], media_mids[i]), headers=self.headers)
				vkey = re.findall('"vkey":"(.*?)"', fcg_res.text)[0]
				download_names.append(temp_names[i].replace("\\", "").replace("/", "").replace(" ", "").replace('.', ''))
				download_urls.append(self.download_format_url.format(media_mids[i], vkey))
			except:
				pass
			time.sleep(random.random())
		return download_names, download_urls


# 测试用
if __name__ == '__main__':
	qq().get(songname='尾戒', downnum=1, savepath='./results')