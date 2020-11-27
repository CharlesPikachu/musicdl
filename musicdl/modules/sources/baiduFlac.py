'''
Function:
    百度无损音乐下载: http://music.baidu.com/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import requests
from .base import Base
from ..utils.misc import *


'''百度无损音乐下载类'''
class baiduFlac(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(baiduFlac, self).__init__(config, logger_handle, **kwargs)
        self.source = 'baiduFlac'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword):
        self.logger_handle.info('正在%s中搜索 ——> %s...' % (self.source, keyword))
        cfg = self.config.copy()
        params = {
            'query': keyword,
            'method': 'baidu.ting.search.common',
            'format': 'json',
            'page_no': '1',
            'page_size': cfg['search_size_per_source']
        }
        response = self.session.get(self.search_url, headers=self.headers, params=params)
        all_items = response.json()['song_list']
        songinfos = []
        for item in all_items:
            params = {
                'songIds': str(item['song_id']),
                'type': 'flac'
            }
            response = self.session.get(self.fmlink_url, headers=self.headers, params=params)
            response_json = response.json()
            if response_json.get('errorCode') != 22000: continue
            download_url = response_json['data']['songList'][0]['songLink']
            if not download_url: continue
            filesize = str(round(int(response_json['data']['songList'][0]['size'])/1024/1024, 2)) + 'MB'
            ext = response_json['data']['songList'][0]['format']
            duration = int(response_json['data']['songList'][0]['time'])
            songinfo = {
                'source': self.source,
                'songid': str(item['song_id']),
                'singers': filterBadCharacter(item.get('author', '-')),
                'album': filterBadCharacter(item.get('album_title', '-')),
                'songname': filterBadCharacter(item.get('title', '-')).split('–')[0].strip(),
                'savedir': cfg['savedir'],
                'savename': '_'.join([self.source, filterBadCharacter(item.get('title', '-')).split('–')[0].strip()]),
                'download_url': download_url,
                'filesize': filesize,
                'ext': ext,
                'duration': seconds2hms(duration)
            }
            if not songinfo['album']: songinfo['album'] = '-'
            songinfos.append(songinfo)
        return songinfos
    '''初始化'''
    def __initialize(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
            'Referer': 'http://music.baidu.com/'
        }
        self.search_url = 'http://musicapi.qianqian.com/v1/restserver/ting'
        self.fmlink_url = 'http://music.qianqian.com/data/music/fmlink'