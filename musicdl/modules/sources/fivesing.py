'''
Function:
    5SING音乐下载: http://5sing.kugou.com/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import requests
from .base import Base
from ..utils.misc import *


'''5SING音乐下载类'''
class fivesing(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(fivesing, self).__init__(config, logger_handle, **kwargs)
        self.source = 'fivesing'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword):
        self.logger_handle.info('正在%s中搜索 ——> %s...' % (self.source, keyword))
        cfg = self.config.copy()
        params = {
            'k': keyword,
            't': '0',
            'filterType': '1',
            'ps': cfg['search_size_per_source'],
            'pn': '1',
        }
        response = self.session.get(self.search_url, headers=self.headers, params=params)
        all_items = response.json()['data']['songArray']        
        songinfos = []
        for item in all_items:
            params = {
                'songid': str(item['songId']),
                'songtype': 'yc'
            }
            response = self.session.get(self.songinfo_url, headers=self.headers, params=params)
            response_json = response.json()
            if response_json.get('code') != 1000: continue
            for quality in ['sq', 'hq', 'lq']:
                download_url = response_json.get('data', {}).get(f'{quality}url', '')
                if download_url: break
            if not download_url: continue
            filesize = str(round(int(response_json['data'][f'{quality}size'])/1024/1024, 2)) + 'MB'
            ext = response_json['data'][f'{quality}ext']
            params = {
                'songtype': 'yc',
                'songid': str(item['songId']),
                'songfields': '',
                'userfields': '',
            }
            response = self.session.get(self.lyric_url, headers=self.headers, params=params)
            response_json = response.json()
            lyric = response_json.get('data', {}).get('dynamicWords', '')
            duration = '-:-:-'
            songinfo = {
                'source': self.source,
                'songid': str(item['songId']),
                'singers': filterBadCharacter(item.get('singer', '-')),
                'album': filterBadCharacter(response_json['data'].get('albumName', '-')),
                'songname': filterBadCharacter(item.get('songName', '-')),
                'savedir': cfg['savedir'],
                'savename': '_'.join([self.source, filterBadCharacter(item.get('songName', '-'))]),
                'download_url': download_url,
                'lyric': lyric,
                'filesize': filesize,
                'ext': ext,
                'duration': duration
            }
            if not songinfo['album']: songinfo['album'] = '-'
            songinfos.append(songinfo)
        return songinfos
    '''初始化'''
    def __initialize(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
        }
        self.search_url = 'http://goapi.5sing.kugou.com/search/search'
        self.songinfo_url = 'http://mobileapi.5sing.kugou.com/song/getSongUrl'
        self.lyric_url = 'http://mobileapi.5sing.kugou.com/song/newget'