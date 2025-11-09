'''
Function:
    音乐下载器
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import os
import sys
import copy
import json
import click
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
        assert configpath or config, 'configpath or config should be given'
        self.config = loadConfig(configpath) if config is None else config
        self.logger_handle = Logger(self.config['logfilepath'])
        self.initializeAllSources()
    '''非开发人员外部调用-手动输入版'''
    def run(self, target_srcs=None):
        while True:
            print(BASICINFO % (__version__, self.config.get('savedir')))
            # 音乐搜索
            user_input = self.dealInput('请输入歌曲搜索的关键词: ')
            target_srcs = [
                'kugou', 'kuwo', 'qqmusic', 'qianqian', 'fivesing',
                'netease', 'migu', 'joox', 'yiting',
            ] if target_srcs is None else target_srcs
            search_results = self.search(user_input, target_srcs)
            # 打印搜索结果
            title = ['序号', '歌手', '歌名', '大小', '时长', '专辑', '来源']
            items, records, idx = [], {}, 0
            for key, values in search_results.items():
                for value in values:
                    items.append([
                        colorize(str(idx), 'number'), 
                        colorize(value['singers'], 'singer'), 
                        value['songname'], 
                        value['filesize'] if value['ext'] != 'flac' else colorize(value['filesize'], 'flac'), 
                        value['duration'], 
                        value['album'], 
                        colorize(value['source'].upper(), 'highlight'),
                    ])
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
    '''非开发人员外部调用-语音版'''
    def runbyspeech(self, target_srcs=None, baiduspeech_params=None):
        if baiduspeech_params is None:
            baiduspeech_params = dict(
                app_id='25419425', 
                api_key='fct6UMiQMLsp53MqXzp7AbKQ', 
                secret_key='p3wU9nPnfR7iBz2kM25sikN2ms0y84T3'
            )
        sr_api = SpeechRecognition(**baiduspeech_params)
        while True:
            print(BASICINFO % (__version__, self.config.get('savedir')))
            # 音乐搜索
            sr_api.synthesisspeak('请问您想听的歌曲名是什么呢?')
            target_srcs = ['migu'] if target_srcs is None else target_srcs
            sr_api.record()
            user_input = sr_api.recognition()
            search_results = self.search(user_input, target_srcs)
            # 音乐下载
            songinfos, songpaths = [], []
            for key, values in search_results.items():
                for value in values:
                    songinfos.append(value)
                    songpaths.append(os.path.join(value['savedir'], value['savename']+'.'+value['ext']))
            sr_api.synthesisspeak(f'共搜索到{len(songinfos)}首和{user_input}相关的歌曲, 将依次为您下载播放.')
            self.download(songinfos)
            # 音乐播放
            for songpath in songpaths:
                sr_api.synthesisspeak(audiopath=songpath)
    '''音乐搜索'''
    def search(self, keyword, target_srcs):
        self.logger_handle.info(f'正在搜索 {colorize(keyword, "highlight")} 来自 {colorize("|".join([c.upper() for c in target_srcs]), "highlight")}')
        def threadSearch(search_api, keyword, target_src, search_results):
            try:
                search_results.update({target_src: search_api(keyword)})
            except Exception as err:
                self.logger_handle.error(str(err), True)
                self.logger_handle.warning('无法在%s中搜索 >>>> %s' % (target_src, keyword))
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
            'kuwo': Kuwo, 'joox': Joox, 'migu': Migu, 'kugou': Kugou,
            'lizhi': Lizhi, 'yiting': YiTing, 'netease': Netease, 'qqmusic': QQMusic,
            'qianqian': Qianqian, 'fivesing': FiveSing, 'ximalaya': Ximalaya,
        }
        for key, value in supported_sources.items():
            setattr(self, key, value(copy.deepcopy(self.config), self.logger_handle))
        return supported_sources
    '''处理用户输入'''
    def dealInput(self, tip=''):
        user_input = input(tip)
        if user_input.lower() == 'q':
            self.logger_handle.info('ByeBye')
            sys.exit()
        elif user_input.lower() == 'r':
            self.initializeAllSources()
            self.run()
        else:
            return user_input
    '''str'''
    def __str__(self):
        return 'Welcome to use musicdl!\nYou can visit https://github.com/CharlesPikachu/musicdl for more details.'


'''cmd直接运行'''
@click.command()
@click.version_option()
@click.option('-k', '--keyword', default=None, help='搜索的歌曲关键字, 若不指定, 则进入musicdl终端版')
@click.option('-l', '--logfilepath', default='musicdl.log', help='日志文件保存的路径')
@click.option('-p', '--proxies', default='{}', help='设置的代理')
@click.option('-s', '--savedir', default='music', help='下载的音乐保存路径')
@click.option('-c', '--count', default='5', help='在各个平台搜索时的歌曲搜索数量')
@click.option('-t', '--targets', default=None, help='指定音乐搜索的平台, 例如"migu,joox"')
def musicdlcmd(keyword, logfilepath, proxies, savedir, count, targets):
    config = {
        'logfilepath': logfilepath,
        'proxies': json.loads(proxies),
        'savedir': savedir,
        'search_size_per_source': int(count),
    }
    target_srcs = [
        'kugou', 'kuwo', 'qqmusic', 'qianqian', 'fivesing',
        'netease', 'migu', 'joox', 'yiting',
    ] if targets is None else [src.strip() for src in targets.split(',')]
    dl_client = musicdl(config=config)
    if keyword is None:
        dl_client.run(target_srcs=target_srcs)
    else:
        print(dl_client)
        search_results = dl_client.search(keyword, target_srcs)
        # 打印搜索结果
        title = ['序号', '歌手', '歌名', '大小', '时长', '专辑', '来源']
        items, records, idx = [], {}, 0
        for key, values in search_results.items():
            for value in values:
                items.append([
                    colorize(str(idx), 'number'), 
                    colorize(value['singers'], 'singer'), 
                    value['songname'], 
                    value['filesize'] if value['ext'] != 'flac' else colorize(value['filesize'], 'flac'), 
                    value['duration'], 
                    value['album'], 
                    colorize(value['source'].upper(), 'highlight'),
                ])
                records.update({str(idx): value})
                idx += 1
        printTable(title, items)
        # 音乐下载
        user_input = dl_client.dealInput('请输入想要下载的音乐编号: ')
        need_download_numbers = user_input.replace(' ', '').split(',')
        songinfos = []
        for item in need_download_numbers:
            songinfo = records.get(item, '')
            if songinfo: songinfos.append(songinfo)
        dl_client.download(songinfos)


'''run'''
if __name__ == '__main__':
    import os
    rootdir = os.path.split(os.path.abspath(__file__))[0]
    dl_client = musicdl(os.path.join(rootdir, 'config.json'))
    dl_client.run()