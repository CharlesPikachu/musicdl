# 代码仅供学习交流，不得用于商业/非法使用
# 作者: Charles
# 公众号: Charles的皮卡丘
# 音乐下载器
# 目前支持的平台:
# 	网易云: wangyiyun.wangyiyun()
# 	QQ: qq.qq()
# 	酷狗: kugou.kugou()
# 	千千: qianqian.qianqian()
# 	酷我: kuwo.kuwo()
# 	虾米: xiami.xiami()
import os
import ctypes
import inspect
import threading
from platforms import *
from tkinter import *
from tkinter import messagebox
from PIL import Image, ImageTk


# 尝试解决线程残留问题
def _async_raise(tid, exctype):
	tid = ctypes.c_long(tid)
	if not inspect.isclass(exctype):
		exctype = type(exctype)
	res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
	if res == 0:
		raise ValueError("invalid thread id")
	elif res != 1:
		ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
		raise SystemError("PyThreadState_SetAsyncExc failed")
def stop_thread(thread):
	_async_raise(thread.ident, SystemExit)


# 下载器类
class Download_Thread(threading.Thread):
	def __init__(self, *args, **kwargs):
		super(Download_Thread, self).__init__(*args, **kwargs)
		self.__pause = threading.Event()
		self.__pause.clear()
		self.__running = threading.Event()
		self.__running.set()
		self.flag = False
		# 对应关系:
		# 	网易云音乐 -> '1'
		# 	QQ音乐 -> '2'
		# 	酷狗音乐 -> '3'
		# 	千千音乐 -> '4'
		# 	酷我音乐 -> '5'
		# 	虾米音乐 -> '6'
		self.engine = None
		self.songname = None
		self.downnum = 1
		self.savepath = './results'
	def run(self):
		while self.__running.isSet():
			self.__pause.wait()
			self.flag = True
			if self.engine == '1':
				self.show_start_info()
				try:
					downednum = wangyiyun.wangyiyun().get(self.songname, downnum=self.downnum)
					self.show_end_info(downednum)
				except:
					title = '资源不存在'
					msg = '所要下载的资源不存在！'
					messagebox.showerror(title, msg)
			elif self.engine == '2':
				self.show_start_info()
				try:
					downednum = qq.qq().get(self.songname, downnum=self.downnum)
					self.show_end_info(downednum)
				except:
					title = '资源不存在'
					msg = '所要下载的资源不存在！'
					messagebox.showerror(title, msg)
			elif self.engine == '3':
				self.show_start_info()
				try:
					downednum = kugou.kugou().get(self.songname, downnum=self.downnum)
					self.show_end_info(downednum)
				except:
					title = '资源不存在'
					msg = '所要下载的资源不存在！'
					messagebox.showerror(title, msg)
			elif self.engine == '4':
				self.show_start_info()
				try:
					downednum = qianqian.qianqian().get(self.songname, downnum=self.downnum)
					self.show_end_info(downednum)
				except:
					title = '资源不存在'
					msg = '所要下载的资源不存在！'
					messagebox.showerror(title, msg)
			elif self.engine == '5':
				self.show_start_info()
				try:
					downednum = kuwo.kuwo().get(self.songname, downnum=self.downnum)
					self.show_end_info(downednum)
				except:
					title = '资源不存在'
					msg = '所要下载的资源不存在！'
					messagebox.showerror(title, msg)
			elif self.engine == '6':
				self.show_start_info()
				try:
					downednum = xiami.xiami().get(self.songname, downnum=self.downnum)
					self.show_end_info(downednum)
				except:
					title = '资源不存在'
					msg = '所要下载的资源不存在！'
					messagebox.showerror(title, msg)
			else:
				title = '解析失败'
				msg = '平台选项参数解析失败！'
				messagebox.showerror(title, msg)
			self.pause()
	def pause(self):
		self.__pause.clear()
	def resume(self):
		self.__pause.set()
	def stop(self):
		self.__running.clear()
	def show_start_info(self):
		title = '开始下载'
		msg = '搜索平台: {}\n已开始下载{}，请耐心等待。'.format(self.engine, self.songname)
		messagebox.showinfo(title, msg)
	def show_end_info(self, downednum, savepath='./results'):
		title = '下载成功'
		msg = '{}下载成功, 共{}歌曲被下载。\n歌曲保存在{}。'.format(self.songname, downednum, savepath)
		messagebox.showinfo(title, msg)
t_download = Download_Thread()


# 下载器
def downloader(options, op_engine_var, en_songname_var, en_num_var):
	if t_download.flag is False:
		t_download.start()
	try:
		engine = str(options.index(str(op_engine_var.get())) + 1)
		songname = str(en_songname_var.get())
		downnum = int(en_num_var.get())
	except:
		title = '输入错误'
		msg = '歌曲名或歌曲下载数量输入错误！'
		messagebox.showerror(title, msg)
		return None
	t_download.engine = engine
	t_download.songname = songname
	t_download.downnum = downnum
	t_download.resume()


# 关于作者
def ShowAuthor():
	title = '关于作者'
	msg = '作者: Charles\n公众号: Charles的皮卡丘\nGithub: https://github.com/CharlesPikachu/Music-Downloader'
	messagebox.showinfo(title, msg)


# 退出程序
def stopDemo(root):
	t_download.stop()
	root.quit()
	root.destroy()


# 主界面
def Demo(options):
	assert len(options) > 0
	# 初始化
	root = Tk()
	root.title('音乐下载器V1.2——公众号:Charles的皮卡丘')
	root.resizable(False, False)
	root.geometry('480x368+400+120')
	image_path = './bgimgs/bg1_demo.jpg'
	bgimg = Image.open(image_path)
	bgimg = ImageTk.PhotoImage(bgimg)
	lb_bgimg = Label(root, image=bgimg)
	lb_bgimg.grid()
	# Menu
	menubar = Menu(root)
	filemenu = Menu(menubar, tearoff=False)
	filemenu.add_command(label='退出', command=lambda: stopDemo(root), font=('楷体', 10))
	menubar.add_cascade(label='文件', menu=filemenu)
	filemenu = Menu(menubar, tearoff=False)
	filemenu.add_command(label='关于作者', command=ShowAuthor, font=('楷体', 10))
	menubar.add_cascade(label='更多', menu=filemenu)
	root.config(menu=menubar)
	# Label+Entry组件
	# 	歌名
	lb_songname = Label(root, text='歌名:   ', font=('楷体', 10), bg='white')
	lb_songname.place(relx=0.1, rely=0.05, anchor=CENTER)
	en_songname_var = StringVar()
	en_songname = Entry(root, textvariable=en_songname_var, width=15, fg='gray', relief=GROOVE, bd=3)
	en_songname.insert(0, '尾戒')
	en_songname.place(relx=0.3, rely=0.05, anchor=CENTER)
	# 	下载数量
	lb_num = Label(root, text='下载数量:', font=('楷体', 10), bg='white')
	lb_num.place(relx=0.1, rely=0.15, anchor=CENTER)
	en_num_var = StringVar()
	en_num = Entry(root, textvariable=en_num_var, width=15, fg='gray', relief=GROOVE, bd=3)
	en_num.insert(0, '1')
	en_num.place(relx=0.3, rely=0.15, anchor=CENTER)
	# Label+OptionMenu组件
	lb_engine = Label(root, text='搜索平台:', font=('楷体', 10), bg='white')
	lb_engine.place(relx=0.1, rely=0.25, anchor=CENTER)
	op_engine_var = StringVar()
	op_engine_var.set(options[0])
	op_engine = OptionMenu(root, op_engine_var, *options)
	op_engine.place(relx=0.3, rely=0.25, anchor=CENTER)
	# Button组件
	bt_download = Button(root, text='搜索并下载', bd=2, width=15, height=2, command=lambda: downloader(options, op_engine_var, en_songname_var, en_num_var), font=('楷体', 10))
	bt_download.place(relx=0.3, rely=0.40, anchor=CENTER)
	bt_quit = Button(root, text='退出程序', bd=2, width=15, height=2, command=lambda: stopDemo(root), font=('楷体', 10))
	bt_quit.place(relx=0.3, rely=0.55, anchor=CENTER)
	root.mainloop()



if __name__ == '__main__':
	options = ["1.网易云音乐", "2.QQ音乐", "3.酷狗音乐", "4.千千音乐", "5.酷我音乐", "6.虾米音乐"]
	Demo(options)