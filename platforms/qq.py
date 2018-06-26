# 作者： Charles
# 公众号： Charles的皮卡丘
# qq音乐
import requests
import os
import time
import re
import urllib


class qq():
	def __init__(self):
		self.headers = {
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.146 Safari/537.36'
					}
		self.search_url = 'https://c.y.qq.com/soso/fcgi-bin/client_search_cp?ct=24&qqmusic_ver=1298&new_json=1&remoteplace=txt.yqq.top&searchid=34725291680541638&t=0&aggr=1&cr=1&catZhida=1&lossless=0&flag_qc=0&p=1&n=20&w={}&g_tk=5381&jsonpCallback=MusicJsonCallback703296236531272&loginUin=0&hostUin=0&format=jsonp&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0'
		self.fcg_url = 'https://c.y.qq.com/base/fcgi-bin/fcg_music_express_mobile3.fcg?g_tk=5381&jsonpCallback=MusicJsonCallback9239412173137234&loginUin=0&hostUin=0&format=json&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq&needNewCode=0&cid=205361747&callback=MusicJsonCallback9239412173137234&uin=0&songmid={}&filename={}.m4a&guid=8208467632'
		self.downloader_url = 'http://dl.stream.qqmusic.qq.com/{}.m4a?vkey={}&guid=8208467632&uin=0&fromtag=66'
	def get(self, songname, savepath='./results', num=1):
		# Step1
		# 根据歌名搜索，获取所需的信息
		res = requests.get(self.search_url.format(songname), headers=self.headers).text
		media_mid_temp = re.findall('"media_mid":"(.*?)"', res)
		media_mid = []
		for i in range(len(media_mid_temp)):
			media_mid.append('C400'+media_mid_temp[i])
		songmid = re.findall('"lyric_hilight":".*?","mid":"(.*?)","mv"', res)
		singer_temp = re.findall('"singer":\[.*?\]', res)
		singer = []
		for s in singer_temp:
			singer.append(re.findall('"name":"(.*?)"', s)[0])
		songname = re.findall('},"name":"(.*?)","newStatus"', res)
		# Step2
		# 获取下载地址
		urls = []
		del_idex = []
		songname_keep = []
		singer_keep = []
		for m in range(len(media_mid)):
			try:
				fcg_res = requests.get(self.fcg_url.format(songmid[m], media_mid[m]), headers=self.headers)
				vkey = re.findall('"vkey":"(.*?)"', fcg_res.text)[0]
				urls.append(self.downloader_url.format(media_mid[m], vkey))
				songname_keep.append(songname[m])
				singer_keep.append(singer[m])
			except:
				pass
			time.sleep(0.5)
		# Step3
		# 下载歌曲
		if num > len(urls):
			num = len(urls)
		if not os.path.exists(savepath):
			os.mkdir(savepath)
		for n in range(num):
			filepath = './{}/{}'.format(savepath, songname_keep[n].replace("\\", "").replace("/", "").replace(" ", "")+'_'+singer_keep[n].replace("\\", "").replace("/", "").replace(" ", "")+'.mp3')
			urllib.request.urlretrieve(urls[n], filepath)