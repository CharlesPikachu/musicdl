'''
Function:
    虾米音乐下载: https://www.xiami.com/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import re
import time
import json
import requests
from .base import Base
from hashlib import md5
from ..utils.misc import *


'''虾米音乐下载类'''
class Xiami(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(Xiami, self).__init__(config, logger_handle, **kwargs)
        self.source = 'xiami'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword):
        self.logger_handle.info('正在%s中搜索 ——> %s...' % (self.source, keyword))
        cfg = self.config.copy()
        token = self.__getToken()
        search_url = self.base_url.format(action=self.actions['searchsongs'])
        params = {
            'key': keyword,
            'pagingVO': {'page': '1', 'pageSize': str(cfg['search_size_per_source'])}
        }
        response = self.session.get(search_url, headers=self.headers, params=self.__xiamiSign(params, token))
        all_items = response.json()['data']['data']['songs']
        songinfos = []
        for item in all_items:
            download_url = ''
            for file_info in item['listenFiles']:
                if not file_info['downloadFileSize']: continue
                filesize = str(round(int(file_info['downloadFileSize'])/1024/1024, 2)) + 'MB'
                download_url = file_info['listenFile']
                ext = file_info['format']
                duration = int(file_info.get('length', 0)) / 1000
                break
            if not download_url: continue
            lyric_url, lyric = item.get('lyricInfo', {}).get('lyricFile', ''), ''
            if lyric_url:
                response = self.session.get(lyric_url, headers=self.headers)
                response.encoding = 'utf-8'
                lyric = response.text
            songinfo = {
                'source': self.source,
                'songid': str(item['songId']),
                'singers': filterBadCharacter(item.get('artistName', '-')),
                'album': filterBadCharacter(item.get('albumName', '-')),
                'songname': filterBadCharacter(item.get('songName', '-')).split('–')[0].strip(),
                'savedir': cfg['savedir'],
                'savename': '_'.join([self.source, filterBadCharacter(item.get('songName', '-')).split('–')[0].strip()]),
                'download_url': download_url,
                'lyric': lyric,
                'filesize': filesize,
                'ext': ext,
                'duration': seconds2hms(duration)
            }
            if not songinfo['album']: songinfo['album'] = '-'
            songinfos.append(songinfo)
        return songinfos
    '''虾米签名'''
    def __xiamiSign(self, params, token=''):
        appkey = '23649156'
        t = str(int(time.time() * 1000))
        request_str = {
            'header': {'appId': '200', 'platformId': 'h5'},
            'model': params
        }
        data = json.dumps({'requestStr': json.dumps(request_str)})
        sign = '%s&%s&%s&%s' % (token, t, appkey, data)
        sign = md5(sign.encode('utf-8')).hexdigest()
        params = {
            't': t,
            'appKey': appkey,
            'sign': sign,
            'data': data
        }
        return params
    '''获得请求所需的token'''
    def __getToken(self):
        action = self.actions['getsongdetail']
        url = self.base_url.format(action=action)
        params = {'songId': '1'}
        response = self.session.get(url, params=self.__xiamiSign(params))
        cookies = response.cookies.get_dict()
        return cookies['_m_h5_tk'].split('_')[0]
    '''初始化'''
    def __initialize(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
            'Referer': 'http://h.xiami.com',
            'Connection': 'keep-alive',
            'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
            'Accept-Encoding': 'gzip,deflate,sdch',
            'Accept': '*/*'
        }
        self.base_url = 'https://acs.m.xiami.com/h5/{action}/1.0/'
        self.actions = {
            'searchsongs': 'mtop.alimusic.search.searchservice.searchsongs',
            'getsongdetail': 'mtop.alimusic.music.songservice.getsongdetail',
            'getsongs': 'mtop.alimusic.music.songservice.getsongs',
            'getsonglyrics': 'mtop.alimusic.music.lyricservice.getsonglyrics'
        }