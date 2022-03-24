'''
Function:
    咪咕音乐下载: http://www.migu.cn/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import time
import requests
from .base import Base
from ..utils import seconds2hms, filterBadCharacter


'''咪咕音乐下载类'''
class Migu(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(Migu, self).__init__(config, logger_handle, **kwargs)
        self.source = 'migu'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword, disable_print=True):
        if not disable_print: self.logger_handle.info('正在%s中搜索 >>>> %s' % (self.source, keyword))
        cfg = self.config.copy()
        params = {
            'ua': 'Android_migu',
            'version': '5.0.1',
            'text': keyword,
            'pageNo': str(cfg.get('page', 1)),
            'pageSize': cfg['search_size_per_source'],
            'searchSwitch': '{"song":1,"album":0,"singer":0,"tagSong":0,"mvSong":0,"songlist":0,"bestShow":1}',
        }
        response = self.session.get(self.search_url, headers=self.headers, params=params)
        all_items = response.json()['songResultData']['result']
        songinfos = []
        for item in all_items:
            ext = ''
            download_url = ''
            filesize = '-MB'
            for rate in sorted(item.get('rateFormats', []), key=lambda x: int(x['size']), reverse=True):
                if (int(rate['size']) == 0) or (not rate.get('formatType', '')) or (not rate.get('resourceType', '')): continue
                ext = 'flac' if rate.get('formatType') == 'SQ' else 'mp3'
                download_url = self.player_url.format(
                    copyrightId=item['copyrightId'], 
                    contentId=item['contentId'], 
                    toneFlag=rate['formatType'],
                    resourceType=rate['resourceType']
                )
                filesize = str(round(int(rate['size'])/1024/1024, 2)) + 'MB'
                break
            if not download_url: continue
            lyric_url, lyric = item.get('lyricUrl', ''), ''
            if lyric_url:
                response = self.session.get(lyric_url, headers=self.headers)
                response.encoding = 'utf-8'
                lyric = response.text
            duration = '-:-:-'
            songinfo = {
                'source': self.source,
                'songid': str(item['id']),
                'singers': filterBadCharacter(','.join([s.get('name', '') for s in item.get('singers', [])])),
                'album': filterBadCharacter(item.get('albums', [{'name': '-'}])[0].get('name', '-')),
                'songname': filterBadCharacter(item.get('name', '-')),
                'savedir': cfg['savedir'],
                'savename': filterBadCharacter(item.get('name', f'{keyword}_{int(time.time())}')),
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
            'Referer': 'https://m.music.migu.cn/', 
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.75 Mobile Safari/537.36'
        }
        self.search_url = 'http://pd.musicapp.migu.cn/MIGUM3.0/v1.0/content/search_all.do'
        self.player_url = 'https://app.pd.nf.migu.cn/MIGUM3.0/v1.0/content/sub/listenSong.do?channel=mx&copyrightId={copyrightId}&contentId={contentId}&toneFlag={toneFlag}&resourceType={resourceType}&userId=15548614588710179085069&netType=00'