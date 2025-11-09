'''
Function:
    千千音乐下载: http://music.taihe.com/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import time
import hashlib
import requests
from .base import Base
from ..utils import seconds2hms, filterBadCharacter


'''千千音乐下载类'''
class Qianqian(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(Qianqian, self).__init__(config, logger_handle, **kwargs)
        self.source = 'qianqian'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword, disable_print=True):
        if not disable_print: self.logger_handle.info('正在%s中搜索 >>>> %s' % (self.source, keyword))
        cfg = self.config.copy()
        params = {
            'sign': self.__calcSign(keyword, '16073360'),
            'word': keyword,
            'timestamp': str(int(time.time())),
            'appid': '16073360',
        }
        response = self.session.get(self.search_url, headers=self.headers, params=params)
        all_items = response.json()['data']['typeTrack']
        songinfos = []
        for item in all_items:
            params = {
                'sign': self.__calcSign(keyword, '16073360', item['TSID']),
                'TSID': item['TSID'],
                'timestamp': str(int(time.time())),
                'appid': '16073360',
            }
            response = self.session.get(self.tracklink_url, headers=self.headers, params=params)
            response_json = response.json()
            if response_json.get('errno') != 22000: continue
            if 'path' in response_json['data']:
                download_url = response_json['data']['path']
            else:
                download_url = response_json['data']['trail_audio_info']['path']
            if not download_url: continue
            lyric_url, lyric = response_json['data'].get('lyric', ''), ''
            if lyric_url:
                response = self.session.get(lyric_url, headers=self.headers)
                response.encoding = 'utf-8'
                lyric = response.text
            filesize = str(round(int(response_json['data']['size'])/1024/1024, 2)) + 'MB'
            ext = response_json['data']['format']
            duration = int(response_json['data']['duration'])
            songinfo = {
                'source': self.source,
                'songid': str(item['id']),
                'singers': filterBadCharacter(item['artist'][0].get('name', '-')),
                'album': filterBadCharacter(item.get('albumTitle', '-')),
                'songname': filterBadCharacter(item.get('title', '-')).split('–')[0].strip(),
                'savedir': cfg['savedir'],
                'savename': filterBadCharacter(item.get('title', f'{keyword}_{int(time.time())}')).split('–')[0].strip(),
                'download_url': download_url,
                'lyric': lyric,
                'filesize': filesize,
                'ext': ext,
                'duration': seconds2hms(duration)
            }
            if not songinfo['album']: songinfo['album'] = '-'
            songinfos.append(songinfo)
            if len(songinfos) == cfg['search_size_per_source']: break
        return songinfos
    '''计算sign值'''
    def __calcSign(self, keyword, appid, TSID=None):
        secret = '0b50b02fd0d73a9c4c8c3a781c30845f'
        if TSID is None:
            e = {
                'word': keyword,
                'appid': appid,
                'timestamp': str(int(time.time()))
            }
            n = list(e.keys())
            n.sort()
            i = f'{n[0]}={e[n[0]]}'
            for r in range(1, len(n)):
                o = n[r]
                i += f'&{o}={e[o]}'
            sign = hashlib.md5((i + secret).encode('utf-8')).hexdigest()
        else:
            sign = hashlib.md5((f'TSID={TSID}&appid={appid}&timestamp={str(int(time.time()))}{secret}').encode('utf-8')).hexdigest()
        return sign
    '''初始化'''
    def __initialize(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
            'Referer': 'https://music.taihe.com/'
        }
        self.search_url = 'https://music.taihe.com/v1/search'
        self.tracklink_url = 'https://music.taihe.com/v1/song/tracklink'