'''
Function:
    下载器类
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import click
import warnings
import requests
from .misc import *
from contextlib import closing
warnings.filterwarnings('ignore')


'''下载器类'''
class Downloader():
    def __init__(self, songinfo, session=None, **kwargs):
        self.songinfo = songinfo
        self.session = requests.Session() if session is None else session
        self.__setheaders(songinfo['source'])
    '''外部调用'''
    def start(self):
        songinfo, session, headers = self.songinfo, self.session, self.headers
        checkDir(songinfo['savedir'])
        try:
            is_success = False
            with closing(session.get(songinfo['download_url'], headers=headers, stream=True, verify=False)) as response:
                total_size = int(response.headers['content-length'])
                chunk_size = 1024
                if response.status_code == 200:
                    label = '[FileSize]: %0.2fMB' % (total_size / 1024 / 1024)
                    with click.progressbar(length=total_size, label=label) as progressbar:
                        with open(os.path.join(songinfo['savedir'], songinfo['savename']+'.'+songinfo['ext']), 'wb') as fp:
                            for chunk in response.iter_content(chunk_size=chunk_size):
                                if chunk:
                                    fp.write(chunk)
                                    progressbar.update(chunk_size)
                    is_success = True
        except:
            is_success = False
        return is_success
    '''设置请求头'''
    def __setheaders(self, source):
        assert source in ['baiduFlac', 'kugou', 'kuwo', 'qq', 'qianqian', 'netease', 'migu', 'xiami', 'joox'], 'unsupport set headers of source %s...' % source
        self.qq_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
            'Referer': 'http://y.qq.com'
        }
        self.migu_headers = {
            'Referer': 'https://m.music.migu.cn/', 
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.75 Mobile Safari/537.36'
        }
        self.kuwo_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
        }
        self.joox_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/605.1.15 (KHTML, like Gecko)'
        }
        self.xiami_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36'
        }
        self.kugou_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
            'Host': 'webfs.yun.kugou.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive'
        }
        self.netease_headers = {}
        self.qianqian_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
            'Referer': 'http://music.baidu.com/'
        }
        self.baiduFlac_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
            'Referer': 'http://music.baidu.com/'
        }
        self.headers = {
            'qq': self.qq_headers,
            'migu': self.migu_headers,
            'kuwo': self.kuwo_headers,
            'joox': self.joox_headers,
            'xiami': self.xiami_headers,
            'kugou': self.kugou_headers,
            'netease': self.netease_headers,
            'qianqian': self.qianqian_headers,
            'baiduFlac': self.baiduFlac_headers,
        }[source]