'''
Function:
	咪咕音乐下载: http://www.migu.cn/
Author:
	Charles
微信公众号:
	Charles的皮卡丘
声明:
	代码仅供学习交流, 不得用于商业/非法使用.
'''
import re
import os
import click
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
class migu():
	def __init__(self):
		self.ios_headers = {
							'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
							"referer": "http://music.migu.cn/"
							}
		self.search_url = 'http://pd.musicapp.migu.cn/MIGUM2.0/v1.0/content/search_all.do'
		self.download_url_format = 'http://app.pd.nf.migu.cn/MIGUM2.0/v1.0/content/sub/listenSong.do?toneFlag={}&netType=00&userId=15548614588710179085069&ua=Android_migu&version=5.1&copyrightId=0&contentId={}&resourceType={}&channel=0'
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
					qualities = self.search_results.get(download_name)[2]
					for quality in qualities:
						download_url = self.download_url_format.format(quality.get('formatType', 'SQ'), self.search_results.get(download_name)[0], quality.get('resourceType', 'E'))
						res = self.__download(download_name, download_url, savepath, extension='.flac' if quality.get('formatType', '') == 'SQ' else '.mp3')
						if res:
							break
						print('[migu-INFO]: %s-%s下载失败, 将尝试降低歌曲音质重新下载...' % (download_name, quality.get('formatType', '')))
					if res:
						downed_list.append(download_name)
			return downed_list
		else:
			raise ValueError('mode in migu().get must be <search> or <download>...')
	'''下载'''
	def __download(self, download_name, download_url, savepath, extension='.mp3'):
		if not os.path.exists(savepath):
			os.mkdir(savepath)
		download_name = download_name.replace('<', '').replace('>', '').replace('\\', '').replace('/', '') \
									 .replace('?', '').replace(':', '').replace('"', '').replace('：', '') \
									 .replace('|', '').replace('？', '').replace('*', '')
		savename = 'migu_{}'.format(download_name)
		count = 0
		while os.path.isfile(os.path.join(savepath, savename+extension)):
			count += 1
			savename = 'migu_{}_{}'.format(download_name, count)
		savename += extension
		try:
			print('[migu-INFO]: 正在下载 --> %s' % savename.split('.')[0])
			with closing(requests.get(download_url, headers=self.ios_headers, stream=True, verify=False)) as res:
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
					'ua': "Android_migu",
					"version": "5.0.1",
					"text": songname,
					"pageNo": 1,
					"pageSize": 15,
					"searchSwitch": '{"song":1,"album":0,"singer":0,"tagSong":0,"mvSong":0,"songlist":0,"bestShow":1}'
				}
		res = requests.get(self.search_url, params=params, headers=self.ios_headers)
		results = {}
		for item in res.json().get('songResultData').get('result'):
			songid = item.get('id', '')
			songname = item.get('name', '')
			singers = [singer.get("name", "") for singer in item.get("singers", [])]
			singers = ','.join(singers)
			album = item.get("albums", [{}])[0].get("name", "")
			content_id = item.get('contentId', '')
			qualities = sorted(item.get('rateFormats', []), key=lambda x: int(x["size"]), reverse=True)
			download_name = '%s--%s--%s' % (songname, singers, album)
			count = 0
			while download_name in results:
				count += 1
				download_name = '%s(%d)--%s--%s' % (infos[i][1], count, singers, album)
			results[download_name] = [content_id, songid, qualities]
		return results


'''测试用'''
if __name__ == '__main__':
	mg = migu()
	res = mg.get(mode='search', songname='尾戒')
	mg.get(mode='download', need_down_list=list(res.keys())[:2])