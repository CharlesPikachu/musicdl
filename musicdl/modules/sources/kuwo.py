'''
Function:
    酷我音乐下载: http://www.kuwo.cn/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import time
import requests
from .base import Base
from ..utils.misc import *


'''酷我音乐下载类'''
class kuwo(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(kuwo, self).__init__(config, logger_handle, **kwargs)
        self.source = 'kuwo'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword):
        self.logger_handle.info('正在%s中搜索 ——> %s...' % (self.source, keyword))
        response = self.session.get('http://kuwo.cn/search/list?key=hello', headers=self.headers)
        cookies, token = response.cookies, response.cookies.get('kw_token')
        self.headers['csrf'] = token
        cfg = self.config.copy()
        params = {
            'key': keyword,
            'pn': '1',
            'rn': cfg['search_size_per_source'],
        }
        response = self.session.get(self.search_url, headers=self.headers, params=params, cookies=cookies)
        all_items = response.json()['data']['list']
        songinfos = []
        for item in all_items:
            params = {
                'format': 'mp3',
                'rid': str(item['rid']),
                'response': 'url',
                'type': 'convert_url3',
                'br': '128kmp3',
                'from': 'web',
                't': str(int(time.time()*1000)),
                'reqId': 'de97aac1-73c3-11ea-a715-7de8a8cc7b68'
            }
            response = self.session.get(self.player_url, headers=self.headers, params=params)
            response_json = response.json()
            if response_json.get('code') != 200: continue
            download_url = response_json['url']
            if not download_url: continue
            params = {
                'musicId': str(item['rid'])
            }
            self.lyric_headers.update({'Referer': f'http://m.kuwo.cn/yinyue/{str(item["rid"])}'})
            response = self.session.get(self.lyric_url, headers=self.lyric_headers, params=params)
            lyric = response.json().get('data', {}).get('lrclist', '')
            filesize = '-MB'
            ext = download_url.split('.')[-1]
            duration = int(item.get('duration', 0))
            songinfo = {
                'source': self.source,
                'songid': str(item['rid']),
                'singers': filterBadCharacter(item.get('artist', '-')),
                'album': filterBadCharacter(item.get('album', '-')),
                'songname': filterBadCharacter(item.get('name', '-')),
                'savedir': cfg['savedir'],
                'savename': '_'.join([self.source, filterBadCharacter(item.get('name', '-'))]),
                'download_url': download_url,
                'lyric': lyric,
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
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip,deflate',
            'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
            'Host': 'kuwo.cn',
            'Referer': 'http://kuwo.cn',
        }
        self.lyric_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
            'Referer': 'http://m.kuwo.cn/yinyue/'
        }
        self.search_url = 'http://www.kuwo.cn/api/www/search/searchMusicBykeyWord'
        self.player_url = 'http://www.kuwo.cn/url'
        self.lyric_url = 'http://m.kuwo.cn/newh5/singles/songinfoandlrc'