'''
Function:
    酷狗音乐下载: http://www.kugou.com/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import time
import requests
from .base import Base
from ..utils import seconds2hms, filterBadCharacter


'''酷狗音乐下载类'''
class Kugou(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(Kugou, self).__init__(config, logger_handle, **kwargs)
        self.source = 'kugou'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword, disable_print=True):
        if not disable_print: self.logger_handle.info('正在%s中搜索 >>>> %s' % (self.source, keyword))
        cfg = self.config.copy()
        params = {
            'keyword': keyword,
            'page': str(cfg.get('page', 1)),
            'pagesize': cfg['search_size_per_source'],
            'userid': '-1',
            'clientver': '',
            'platform': 'WebFilter',
            'tag': 'em',
            'filter': '',
            'iscorrection': '1',
            'privilege_filter': '0',
            '_': str(int(time.time() * 1000))
        }
        response = self.session.get(self.search_url, headers=self.search_headers, params=params)
        all_items = response.json()['data']['lists']
        songinfos = []
        for item in all_items:
            params = {
                'r': 'play/getdata',
                'hash': str(item['FileHash']),
                'album_id': str(item['AlbumID']),
                'dfid': '1aAcF31Utj2l0ZzFPO0Yjss0',
                'mid': 'ccbb9592c3177be2f3977ff292e0f145',
                'platid': '4',
                '_': str(int(time.time() * 1000))
            }
            response = self.session.get(self.hash_url, headers=self.hash_headers, params=params)
            response_json = response.json()
            if response_json.get('err_code') != 0: continue
            download_url = response_json['data']['play_url'].replace('\\', '')
            if not download_url: continue
            params = {
                'cmd': '100',
                'timelength': '999999',
                'hash': item.get('FileHash', '')
            }
            self.lyric_headers.update({'Referer': f'http://m.kugou.com/play/info/{str(item["ID"])}'})
            response = self.session.get(self.lyric_url, headers=self.lyric_headers, params=params)
            response.encoding = 'utf-8'
            lyric = response.text
            filesize = str(round(int(response_json['data']['filesize'])/1024/1024, 2)) + 'MB'
            ext = download_url.split('.')[-1]
            duration = int(item.get('Duration', 0))
            songinfo = {
                'source': self.source,
                'songid': str(item['ID']),
                'singers': filterBadCharacter(item.get('SingerName', '-')),
                'album': filterBadCharacter(item.get('AlbumName', '-')),
                'songname': filterBadCharacter(item.get('SongName', '-')),
                'savedir': cfg['savedir'],
                'savename': filterBadCharacter(item.get('SongName', f'{keyword}_{int(time.time())}')),
                'download_url': download_url,
                'filesize': filesize,
                'lyric': lyric,
                'ext': ext,
                'duration': seconds2hms(duration)
            }
            if not songinfo['album']: songinfo['album'] = '-'
            songinfos.append(songinfo)
        return songinfos
    '''初始化'''
    def __initialize(self):
        self.search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
            'Referer': 'https://www.kugou.com/yy/html/search.html'
        }
        self.hash_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
            'Referer':'https://www.kugou.com/song/'
        }
        self.lyric_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X] AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
            'Referer': 'http://m.kugou.com/play/info/'
        }
        self.search_url = 'http://songsearch.kugou.com/song_search_v2'
        self.hash_url = 'https://wwwapi.kugou.com/yy/index.php'
        self.lyric_url = 'http://m.kugou.com/app/i/krc.php'