'''
Function:
    音乐下载器
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import sys
import copy
import threading
if __name__ == '__main__':
    from modules import *
    from __init__ import __version__
else:
    from .modules import *
    from .__init__ import __version__


'''basic info'''
BASICINFO = '''************************************************************
Function: 音乐下载器 V%s
Author: Charles
微信公众号: Charles的皮卡丘
操作帮助:
    输入r: 重新初始化程序(即返回主菜单)
    输入q: 退出程序
    下载多首歌曲: 选择想要下载的歌曲时,输入{1,2,5}可同时下载第1,2,5首歌
歌曲保存路径:
    当前路径下的%s文件夹内
************************************************************'''


'''音乐下载器'''
class musicdl():
    def __init__(self, configpath=None, config=None, **kwargs):
        self.config = loadConfig('config.json') if config is None else config
        self.logger_handle = Logger(self.config['logfilepath'])
        self.initializeAllSources()
    '''非开发人员外部调用'''
    def run(self, target_srcs=None):
        while True:
            print(BASICINFO % (__version__, self.config.get('savedir')))
            # 音乐搜索
            user_input = self.dealInput('请输入歌曲搜索的关键词: ')
            target_srcs = [
                'baiduFlac', 'kugou', 'kuwo', 'qq', 'qianqian', 
                'netease', 'migu', 'xiami', 'joox', 'yiting',
            ] if target_srcs is None else target_srcs
            search_results = self.search(user_input, target_srcs)
            # 打印搜索结果
            title = ['序号', '歌手', '歌名', '大小', '时长', '专辑', '来源']
            items = []
            records = {}
            idx = 0
            for key, values in search_results.items():
                for value in values:
                    items.append([str(idx), value['singers'], value['songname'], value['filesize'], value['duration'], value['album'], value['source']])
                    records.update({str(idx): value})
                    idx += 1
            printTable(title, items)
            # 音乐下载
            user_input = self.dealInput('请输入想要下载的音乐编号: ')
            need_download_numbers = user_input.replace(' ', '').split(',')
            songinfos = []
            for item in need_download_numbers:
                songinfo = records.get(item, '')
                if songinfo: songinfos.append(songinfo)
            self.download(songinfos)
    '''音乐搜索'''
    def search(self, keyword, target_srcs):
        def threadSearch(search_api, keyword, target_src, search_results):
            try:
                search_results.update({target_src: search_api(keyword)})
            except Exception as err:
                self.logger_handle.error(str(err), True)
                self.logger_handle.warning('无法在%s中搜索 ——> %s...' % (target_src, keyword))
        task_pool, search_results = [], {}
        for target_src in target_srcs:
            task = threading.Thread(
                target=threadSearch,
                args=(getattr(self, target_src).search, keyword, target_src, search_results)
            )
            task_pool.append(task)
            task.start()
        for task in task_pool:
            task.join()
        return search_results
    '''音乐下载'''
    def download(self, songinfos):
        for songinfo in songinfos:
            getattr(self, songinfo['source']).download([songinfo])
    '''初始化所有支持的搜索/下载源'''
    def initializeAllSources(self):
        supported_sources = {
            'qq': qq,
            'kuwo': kuwo,
            'joox': joox,
            'migu': migu,
            'kugou': kugou,
            'lizhi': lizhi,
            'xiami': xiami,
            'yiting': yiting,
            'netease': netease,
            'qianqian': qianqian,
            'fivesing': fivesing,
            'baiduFlac': baiduFlac,
        }
        for key, value in supported_sources.items():
            setattr(self, key, value(copy.deepcopy(self.config), self.logger_handle))
    '''处理用户输入'''
    def dealInput(self, tip=''):
        user_input = input(tip)
        if user_input.lower() == 'q':
            self.logger_handle.info('ByeBye...')
            sys.exit()
        elif user_input.lower() == 'r':
            self.initializeAllSources()
            self.run()
        else:
            return user_input


'''run'''
if __name__ == '__main__':
    dl_client = musicdl('config.json')
    dl_client.run()