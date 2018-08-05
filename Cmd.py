# 代码仅供学习交流，不得用于商业/非法使用
# 作者：Charles
# 公众号：Charles的皮卡丘
# 音乐下载器-Cmd版
# 目前支持的平台:
# 	网易云: wangyiyun.wangyiyun()
# 	QQ: qq.qq()
# 	酷狗: kugou.kugou()
# 	千千: qianqian.qianqian()
# 	酷我: kuwo.kuwo()
# 	虾米: xiami.xiami()
from platforms import *


def Cmd(options, savepath='./results'):
	print('-'*36 + '<Welcome>' + '-'*36)
	print('[简介]:音乐下载器V1.3')
	print('[Author]:Charles')
	print('[公众号]: Charles的皮卡丘')
	print('[退出方式]: 输入q或者按Ctrl+C键退出')
	print('[目前支持的平台]:')
	for option in options:
		print('*' + option)
	print('-'*81)
	# 平台选择
	choice = input('请输入平台号(1-%d):' % len(options))
	if choice == 'q' or choice == 'Q':
		print('Bye...')
		exit(-1)
	choice_range = [str(i) for i in range(1, len(options)+1)]
	if choice not in choice_range:
		print('[Error]: 平台号输入错误，必须在(1-%d)之间...' % len(options))
		return
	# 歌曲名
	songname = input('请输入歌曲名:')
	if songname == 'q' or songname == 'Q':
		print('Bye...')
		exit(-1)
	# 下载数量
	downnum = input('请输入歌曲下载数量:')
	if downnum == 'q' or downnum == 'Q':
		print('Bye...')
		exit(-1)
	try:
		downnum = int(downnum)
	except:
		print('[Warning]:下载数量输入错误，自动切换为1')
		downnum = 1
	# 开始下载
	if choice == '1':
		try:
			downednum = wangyiyun.wangyiyun().get(songname, downnum=downnum, savepath=savepath, app='cmd')
			print('[INFO]: 歌曲下载完成，共<{}>首，保存在{}...'.format(downednum, savepath))
			return True
		except:
			print('[Error]: 下载失败...')
			return False
	elif choice == '2':
		try:
			downednum = qq.qq().get(songname, downnum=downnum, savepath=savepath, app='cmd')
			print('[INFO]: 歌曲下载完成，共<{}>首，保存在{}...'.format(downednum, savepath))
			return True
		except:
			print('[Error]: 下载失败...')
			return False
	elif choice == '3':
		try:
			downednum = kugou.kugou().get(songname, downnum=downnum, savepath=savepath, app='cmd')
			print('[INFO]: 歌曲下载完成，共<{}>首，保存在{}...'.format(downednum, savepath))
			return True
		except:
			print('[Error]: 下载失败...')
			return False
	elif choice == '4':
		try:
			downednum = qianqian.qianqian().get(songname, downnum=downnum, savepath=savepath, app='cmd')
			print('[INFO]: 歌曲下载完成，共<{}>首，保存在{}...'.format(downednum, savepath))
			return True
		except:
			print('[Error]: 下载失败...')
			return False
	elif choice == '5':
		try:
			downednum = kuwo.kuwo().get(songname, downnum=downnum, savepath=savepath, app='cmd')
			print('[INFO]: 歌曲下载完成，共<{}>首，保存在{}...'.format(downednum, savepath))
			return True
		except:
			print('[Error]: 下载失败...')
			return False
	elif choice == '6':
		try:
			downednum = xiami.xiami().get(songname, downnum=downnum, savepath=savepath, app='cmd')
			print('[INFO]: 歌曲下载完成，共<{}>首，保存在{}...'.format(downednum, savepath))
			return True
		except:
			print('[Error]: 下载失败...')
			return False


if __name__ == '__main__':
	options = ["1.网易云音乐", "2.QQ音乐", "3.酷狗音乐", "4.千千音乐", "5.酷我音乐", "6.虾米音乐"]
	while True:
		try:
			Cmd(options)
		except KeyboardInterrupt:
			print('Bye...')
			exit(-1)