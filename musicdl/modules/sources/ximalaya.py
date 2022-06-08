'''
Function:
    喜马拉雅下载: https://www.ximalaya.com/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import time
import requests
from .base import Base
from ..utils import seconds2hms, filterBadCharacter


'''喜马拉雅下载类'''
class Ximalaya(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(Ximalaya, self).__init__(config, logger_handle, **kwargs)
        self.source = 'ximalaya'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword, disable_print=True):
        if not disable_print: self.logger_handle.info('正在%s中搜索 >>>> %s' % (self.source, keyword))
        cfg = self.config.copy()
        params = {
            'core': 'all',
            'kw': keyword,
            'spellchecker': 'true',
            'device': 'iPhone',
            'live': 'true',
        }
        response = self.session.get(self.search_url, params=params, headers=self.headers)
        all_items = response.json()['data']['track']['docs']
        songinfos = []
        for item in all_items:
            headers = self.headers.copy()
            headers['Referer'] = f'https://www.ximalaya.com/sound/{item["id"]}'
            response = self.session.get(self.songinfo_url.format(str(item['id'])), headers=headers)
            if response.json()['ret'] not in [200]: continue
            download_url = response.json()['data'].get('src', '')
            if not download_url: continue
            songinfo = {
                'source': self.source,
                'songid': str(item['id']),
                'singers': filterBadCharacter(item.get('nickname', '-')),
                'album': filterBadCharacter(item.get('albumTitle', '-')),
                'songname': filterBadCharacter(item.get('title', '-')),
                'savedir': cfg['savedir'],
                'savename': filterBadCharacter(item.get('title', f'{keyword}_{int(time.time())}')),
                'download_url': download_url,
                'lyric': '',
                'filesize': '-',
                'ext': download_url.split('.')[-1],
                'duration': seconds2hms(item.get('duration'))
            }
            songinfos.append(songinfo)
            if len(songinfos) == cfg['search_size_per_source']: break
        return songinfos
    '''初始化'''
    def __initialize(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36',
            'Referer': 'https://www.ximalaya.com/search/'
        }
        self.search_url = 'https://www.ximalaya.com/revision/search/main'
        self.songinfo_url = 'https://www.ximalaya.com/revision/play/v1/audio?id={}&ptype=1'