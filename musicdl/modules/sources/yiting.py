'''
Function:
    一听音乐下载: https://h5.1ting.com/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import time
import requests
from .base import Base
from ..utils import seconds2hms, filterBadCharacter


'''一听音乐下载类'''
class YiTing(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(YiTing, self).__init__(config, logger_handle, **kwargs)
        self.source = 'yiting'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword, disable_print=True):
        if not disable_print: self.logger_handle.info('正在%s中搜索 >>>> %s' % (self.source, keyword))
        cfg = self.config.copy()
        params = {
            'q': keyword,
            'page': str(cfg.get('page', 1)),
            'size': cfg['search_size_per_source'],
        }
        response = self.session.get(self.search_url, headers=self.headers, params=params)
        all_items = response.json()['results']
        songinfos = []
        for item in all_items:
            params = {
                'ids': item['song_id']
            }
            self.headers.update({'Referer': f'http://h5.1ting.com/{item["song_id"]}/song/'})
            response = self.session.get(self.songinfo_url, headers=self.headers, params=params)
            response_json = response.json()[0]
            if 'song_filepath' not in response_json: continue
            download_url = 'http://h5.1ting.com/file?url=' + response_json['song_filepath'].replace('.wma', '.mp3')
            self.headers.update({'Referer': f'http://www.1ting.com/geci{item["song_id"]}.html'})
            response = self.session.get(self.lyric_url+str(item['song_id']), headers=self.headers)
            response.encoding = 'utf-8'
            lyric = response.text
            filesize = '-MB'
            ext = download_url.split('.')[-1]
            duration = '-:-:-'
            songinfo = {
                'source': self.source,
                'songid': str(item['song_id']),
                'singers': filterBadCharacter(item.get('singer_name', '-')),
                'album': filterBadCharacter(item.get('album_name', '-')),
                'songname': filterBadCharacter(item.get('song_name', '-')),
                'savedir': cfg['savedir'],
                'savename': filterBadCharacter(item.get('song_name', f'{keyword}_{int(time.time())}')),
                'download_url': download_url,
                'lyric': lyric,
                'filesize': filesize,
                'ext': ext,
                'duration': duration
            }
            if not songinfo['album']: songinfo['album'] = '-'
            songinfos.append(songinfo)
            if len(songinfos) == cfg['search_size_per_source']: break
        return songinfos
    '''初始化'''
    def __initialize(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36'
        }
        self.search_url = 'http://so.1ting.com/song/json'
        self.songinfo_url = 'http://h5.1ting.com/touch/api/song'
        self.lyric_url = 'http://www.1ting.com/api/geci/lrc/'