'''
Function:
    qq音乐下载: https://y.qq.com/
Author:
    Charles
微信公众号:
    Charles的皮卡丘
'''
import json
import time
import base64
import random
import requests
from .base import Base
from ..utils import seconds2hms, filterBadCharacter


'''QQ音乐下载类'''
class QQMusic(Base):
    def __init__(self, config, logger_handle, **kwargs):
        super(QQMusic, self).__init__(config, logger_handle, **kwargs)
        self.source = 'qqmusic'
        self.__initialize()
    '''歌曲搜索'''
    def search(self, keyword, disable_print=True):
        if not disable_print: self.logger_handle.info('正在%s中搜索 >>>> %s' % (self.source, keyword))
        cfg = self.config.copy()
        data = json.dumps({
            'comm': {
                'g_tk': 997034911, 'uin': ''.join(random.sample('1234567890', 10)), 'format': 'json', 'inCharset': 'utf-8',
                'outCharset': 'utf-8', 'notice': 0, 'platform': 'h5', 'needNewCode': 1, 'ct': 23, 'cv': 0
            },
            'req_0': {
                'method': 'DoSearchForQQMusicDesktop', 'module': 'music.search.SearchCgiService',
                'param': {'remoteplace': 'txt.mqq.all', 'searchid': '55841141906950445', 'search_type': 0,
                'query': keyword, 'page_num': str(cfg.get('page', 1)), 'num_per_page': cfg['search_size_per_source']}
            }
        }, ensure_ascii=False).encode('utf-8')
        response = self.session.post(self.search_url.format(int(round(time.time() * 1000))), headers=self.headers, data=data)
        all_items = response.json()['req_0']['data']['body']['song']['list']
        songinfos = []
        for item in all_items:
            params = {
                'guid': str(random.randrange(1000000000, 10000000000)),
                'loginUin': '3051522991',
                'format': 'json',
                'platform': 'yqq',
                'cid': '205361747',
                'uin': '3051522991',
                'songmid': item['mid'],
                'needNewCode': '0'
            }
            ext = ''
            download_url = ''
            filesize = '-MB'
            for quality in [("A000", "ape", 800), ("F000", "flac", 800), ("M800", "mp3", 320), ("C400", "m4a", 128), ("M500", "mp3", 128)]:
                params['filename'] = '%s%s.%s' % (quality[0], item['mid'], quality[1])
                response = self.session.get(self.mobile_fcg_url, headers=self.ios_headers, params=params)
                response_json = response.json()
                if response_json['code'] != 0: continue
                vkey = response_json.get('data', {}).get('items', [{}])[0].get('vkey', '')
                if vkey:
                    ext = quality[1]
                    download_url = 'http://dl.stream.qqmusic.qq.com/{}?vkey={}&guid={}&uin=3051522991&fromtag=64'.format('%s%s.%s' % (quality[0], item['mid'], quality[1]), vkey, params['guid'])
                    if ext in ['ape', 'flac']:
                        filesize = item['size%s' % ext]
                    elif ext in ['mp3', 'm4a']:
                        filesize = item['size%s' % quality[-1]]
                    break
            if not download_url:
                params = {
                    'data': json.dumps({
                        "req": {"module": "CDN.SrfCdnDispatchServer", "method": "GetCdnDispatch", "param": {"guid": "3982823384", "calltype": 0, "userip": ""}},
                        "req_0": {"module": "vkey.GetVkeyServer", "method": "CgiGetVkey", "param": {"guid": "3982823384", "songmid": [item['mid']], "songtype": [0], "uin": "0", "loginflag": 1, "platform": "20"}},
                        "comm": {"uin": 0, "format": "json", "ct": 24, "cv": 0}
                    })
                }
                response = self.session.get(self.fcg_url, headers=self.ios_headers, params=params)
                response_json = response.json()
                if response_json['code'] == 0 and response_json['req']['code'] == 0 and response_json['req_0']['code'] == 0:
                    ext = 'm4a'
                    if str(response_json["req_0"]["data"]["midurlinfo"][0]["purl"]):
                        download_url = str(response_json["req"]["data"]["freeflowsip"][0]) + str(response_json["req_0"]["data"]["midurlinfo"][0]["purl"])
                    else:
                        download_url = ''
                    filesize = item['file']['size_128mp3']
            if (not download_url) or (filesize == '-MB') or (filesize == 0): continue
            params = {
                'songmid': str(item['mid']),
                'g_tk': '5381',
                'loginUin': '0',
                'hostUin': '0',
                'format': 'json',
                'inCharset': 'utf8',
                'outCharset': 'utf-8',
                'platform': 'yqq'
            }
            response = self.session.get(self.lyric_url, headers={'Referer': 'https://y.qq.com/portal/player.html'}, params=params)
            lyric = base64.b64decode(response.json().get('lyric', '')).decode('utf-8')
            filesize = str(round(filesize/1024/1024, 2)) + 'MB'
            duration = int(item.get('interval', 0))
            songinfo = {
                'source': self.source,
                'songid': str(item['mid']),
                'singers': filterBadCharacter(','.join([s.get('name', '') for s in item.get('singer', [])])),
                'album': filterBadCharacter(item.get('album', {}).get('title', '')),
                'songname': filterBadCharacter(item.get('title', '-')),
                'savedir': cfg['savedir'],
                'savename': filterBadCharacter(item.get('title', f'{keyword}_{int(time.time())}')),
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
        self.ios_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
            'Referer': 'http://y.qq.com'
        }
        self.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Referer': 'https://y.qq.com/',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_3_1 like Mac OS X; zh-CN) AppleWebKit/537.51.1 (KHTML, like Gecko) Mobile/17D50 UCBrowser/12.8.2.1268 Mobile AliApp(TUnionSDK/0.1.20.3) '
        }
        self.search_url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?_webcgikey=DoSearchForQQMusicDesktop&_={}'
        self.mobile_fcg_url = 'https://c.y.qq.com/base/fcgi-bin/fcg_music_express_mobile3.fcg'
        self.fcg_url = 'https://u.y.qq.com/cgi-bin/musicu.fcg'
        self.lyric_url = 'https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg'