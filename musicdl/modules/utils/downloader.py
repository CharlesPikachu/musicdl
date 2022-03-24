'''
Function:
    下载器类
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import os
import requests
from .misc import touchdir
from .logger import colorize
from alive_progress import alive_bar


'''下载器类'''
class Downloader():
    def __init__(self, songinfo, session=None, **kwargs):
        self.songinfo = songinfo
        self.session = requests.Session() if session is None else session
        self.__setheaders(songinfo['source'])
    '''外部调用'''
    def start(self):
        songinfo, session, headers = self.songinfo, self.session, self.headers
        touchdir(songinfo['savedir'])
        with session.get(songinfo['download_url'], headers=headers, stream=True) as response:
            if response.status_code not in [200]: return False
            total_size, chunk_size, downloaded_size = int(response.headers['content-length']), songinfo.get('chunk_size', 1024), 0
            savepath = os.path.join(songinfo['savedir'], f"{songinfo['savename']}.{songinfo['ext']}")
            text, fp = colorize('[FileSize]: %0.2fMB/%0.2fMB', 'pink'), open(savepath, 'wb')
            with alive_bar(manual=True) as bar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not chunk: continue
                    fp.write(chunk)
                    downloaded_size += chunk_size
                    bar.text(text % (downloaded_size / 1024 / 1024, total_size / 1024 / 1024))
                    bar(min(downloaded_size / total_size, 1))
        return True
    '''设置请求头'''
    def __setheaders(self, source):
        self.netease_headers = {}
        self.qqmusic_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
            'Referer': 'http://y.qq.com',
        }
        self.migu_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.75 Mobile Safari/537.36',
            'Referer': 'https://m.music.migu.cn/', 
        }
        self.baiduFlac_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
            'Referer': 'http://music.baidu.com/',
        }
        if hasattr(self, f'{source}_headers'):
            self.headers = getattr(self, f'{source}_headers')
        else:
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36'
            }