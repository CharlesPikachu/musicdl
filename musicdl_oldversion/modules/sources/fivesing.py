'''
Function:
    5SING音乐下载: http://5sing.kugou.com/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import re
import time
import requests
from .base import Base
from ..utils import seconds2hms, filterBadCharacter


'''5SING音乐下载类'''
class FiveSing(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(FiveSing, self).__init__(config, logger_handle, **kwargs)
        self.source = 'fivesing'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword, disable_print=True):
        if not disable_print: self.logger_handle.info('正在%s中搜索 >>>> %s' % (self.source, keyword))
        cfg = self.config.copy()
        response = self.session.get(self.search_url+keyword, headers=self.headers)
        response.encoding = 'uft-8'
        all_items = re.findall(r"dataList = '(.*?)';", response.text)[0]
        all_items = all_items.replace(r'<em class=\\\"keyword\\\">', '')
        all_items = all_items.replace(r'<\\/em>', '')
        all_items = eval(all_items.replace(r'\"', '"'))
        songinfos = []
        for item in all_items:
            try:
                item['songName'] = item['songName'].encode('utf-8').decode('unicode_escape')
            except:
                item['songName'] = '解码失败: ' + item['songName']
            try:
                item['singer'] = item['singer'].encode('utf-8').decode('unicode_escape')
            except:
                item['singer'] = '解码失败: ' + item['singer']
            params = {
                'songid': str(item['songId']),
                'songtype': 'yc' if 'yc' in item['downloadurl'] else 'fc'
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
                'songtype': 'yc' if 'yc' in item['downloadurl'] else 'fc',
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
                'savename': filterBadCharacter(item.get('songName', f'{keyword}_{int(time.time())}')),
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
        }
        self.search_url = 'http://search.5sing.kugou.com/?keyword='
        self.songinfo_url = 'http://mobileapi.5sing.kugou.com/song/getSongUrl'
        self.lyric_url = 'http://mobileapi.5sing.kugou.com/song/newget'