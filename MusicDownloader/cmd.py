'''
Function:
	音乐下载器-Cmd版,目前支持的平台:
		--网易云: wangyiyun.wangyiyun()
		--QQ: qq.qq()
		--酷狗: kugou.kugou()
		--千千: qianqian.qianqian()
		--酷我: kuwo.kuwo()
		--虾米: xiami.xiami()
Author:
	Charles
微信公众号:
	Charles的皮卡丘
声明:
	代码仅供学习交流, 不得用于商业/非法使用.
'''
import sys
try:
	from platforms import *
except:
	from .platforms import *


'''音乐下载器类'''
class MusicDownloader():
	def __init__(self, **kwargs):
		self.INFO = '''************************************************************
Author: Charles
微信公众号: Charles的皮卡丘
Function: 音乐下载器 V2.0.2
操作帮助:
	输入r: 返回主菜单(即重新选择平台号)
	输入q: 退出程序
	其他: 选择想要下载的歌曲时,输入{1,2,5}可同时下载第1,2,5首歌
歌曲保存路径:
	当前路径下的results文件夹内
************************************************************
'''
		self.RESOURCES = ['网易云音乐', 'QQ音乐', '酷狗音乐', '虾米音乐', '酷我音乐', '千千音乐']
		self.platform_now = None
		self.platform_now_name = None
		self.is_select_platform = False
	'''外部调用'''
	def run(self):
		self.platform_now, self.platform_now_name = self.__selectPlatform()
		self.is_select_platform = True
		while True:
			print(self.INFO)
			self.__userSearch()
	'''选择平台'''
	def __selectPlatform(self):
		while True:
			print(self.INFO)
			print('目前支持的平台:')
			for idx, resource in enumerate(self.RESOURCES):
				print('--%d. %s' % ((idx+1), resource))
			platform_idx = self.__input('请选择平台号(1-%d):' % len(self.RESOURCES))
			if platform_idx == '1':
				return wangyiyun.wangyiyun(), 'wangyiyun'
			elif platform_idx == '2':
				return qq.qq(), 'qq'
			elif platform_idx == '3':
				return kugou.kugou(), 'kugou'
			elif platform_idx == '4':
				return xiami.xiami(), 'xiami'
			elif platform_idx == '5':
				return kuwo.kuwo(), 'kuwo'
			elif platform_idx == '6':
				return qianqian.qianqian(), 'qianqian'
			else:
				print('<ERROR>--平台号输入有误, 请重新输入--<ERROR>')
	'''用户搜索操作'''
	def __userSearch(self):
		songname = self.__input('[%s-INFO]: 请输入歌曲名 --> ' % self.platform_now_name)
		if songname is None:
			return
		results = self.platform_now.get(mode='search', songname=songname)
		if len(results) == 0:
			print('<Warning>--未检索到歌曲%s的相关信息, 请重新输入--<Warning>' % songname)
			return
		while True:
			print('[%s-INFO]: 搜索结果如下 -->' % self.platform_now_name)
			for idx, result in enumerate(sorted(results.keys())):
				print('[%d]. %s' % (idx+1, result))
			need_down_numbers = self.__input('[%s-INFO]: 请输入需要下载的歌曲编号(1-%d) --> ' % (self.platform_now_name, len(results.keys())))
			if need_down_numbers is None:
				return
			need_down_numbers = need_down_numbers.split(',')
			numbers_legal = [str(i) for i in range(1, len(results.keys())+1)]
			error_flag = False
			for number in need_down_numbers:
				if number not in numbers_legal:
					print('<ERROR>--歌曲号输入有误, 请重新输入--<ERROR>')
					error_flag = True
					break
			if error_flag:
				continue
			need_down_list = []
			for number in need_down_numbers:
				need_down_list.append(sorted(results.keys())[int(number)-1])
			break
		return self.__download(need_down_list)
	'''下载用户选择的歌曲'''
	def __download(self, need_down_list):
		return self.platform_now.get(mode='download', need_down_list=need_down_list)
	'''处理用户输入'''
	def __input(self, tip=None):
		if tip is None:
			user_input = input()
		else:
			user_input = input(tip)
		if user_input.lower() == 'q':
			print('Bye...')
			sys.exit(-1)
		elif user_input.lower() == 'r':
			self.is_select_platform = False
			if not self.is_select_platform:
				self.platform_now, self.platform_now_name = self.__selectPlatform()
				self.is_select_platform = True
			return None
		else:
			return user_input


if __name__ == '__main__':
	try:
		MusicDownloader().run()
	except KeyboardInterrupt:
		print('Bye...')
		sys.exit(-1)