'''
Function:
    JOOX音乐下载: https://www.joox.com/cn/login
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import json
import time
import base64
import requests
from .base import Base
from ..utils import seconds2hms, filterBadCharacter


'''JOOX音乐下载类'''
class Joox(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(Joox, self).__init__(config, logger_handle, **kwargs)
        self.source = 'joox'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword, disable_print=True):
        if not disable_print: self.logger_handle.info('正在%s中搜索 >>>> %s' % (self.source, keyword))
        cfg = self.config.copy()
        params = {
            'country': 'hk',
            'lang': 'zh_TW',
            'search_input': keyword,
            'sin': '0',
            'ein': cfg['search_size_per_source']
        }
        response = self.session.get(self.search_url, headers=self.headers, params=params)
        all_items = response.json()['itemlist']
        songinfos = []
        for item in all_items:
            params = {
                'songid': item['songid'],
                'lang': 'zh_cn',
                'country': 'hk',
                'from_type': '-1',
                'channel_id': '-1',
                '_': str(int(time.time()*1000))
            }
            response = self.session.get(self.songinfo_url, headers=self.headers, params=params)
            response_json = json.loads(response.text.replace('MusicInfoCallback(', '')[:-1])
            if response_json.get('code') != 0: continue
            for q_key in [('r320Url', '320'), ('r192Url', '192'), ('mp3Url', '128')]:
                download_url = response_json.get(q_key[0], '')
                if not download_url: continue
                filesize = str(round(int(json.loads(response_json['kbps_map'])[q_key[1]])/1024/1024, 2)) + 'MB'
                ext = 'mp3' if q_key[0] in ['r320Url', 'mp3Url'] else 'm4a'
            if not download_url: continue
            params = {
                'musicid': str(item['songid']),
                'country': 'hk',
                'lang': 'zh_cn',
            }
            response = self.session.get(self.lyric_url, headers=self.lyric_headers, params=params)
            lyric = base64.b64decode(response.json().get('lyric', '')).decode('utf-8')
            duration = int(item.get('playtime', 0))
            songinfo = {
                'source': self.source,
                'songid': str(item['songid']),
                'singers': filterBadCharacter(','.join([base64.b64decode(s['name']).decode('utf-8') for s in item.get('singer_list', [])])),
                'album': filterBadCharacter(response_json.get('malbum', '-')),
                'songname': filterBadCharacter(response_json.get('msong', '-')),
                'savedir': cfg['savedir'],
                'savename': filterBadCharacter(response_json.get('msong', f'{keyword}_{int(time.time())}')),
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
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/605.1.15 (KHTML, like Gecko)',
            'Cookie': 'wmid=142420656; user_type=1; country=id; session_key=2a5d97d05dc8fe238150184eaf3519ad;',
            'X-Forwarded-For': '36.73.34.109'
        }
        self.lyric_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Origin': 'https://www.joox.com'
        }
        self.search_url = 'https://api-jooxtt.sanook.com/web-fcgi-bin/web_search'
        self.songinfo_url = 'https://api.joox.com/web-fcgi-bin/web_get_songinfo'
        self.lyric_url = 'https://api-jooxtt.sanook.com/web-fcgi-bin/web_lyric'