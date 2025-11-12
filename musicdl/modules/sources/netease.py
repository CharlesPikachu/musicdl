'''
Function:
    Implementation of NeteaseMusicClient: https://music.163.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import json
import copy
import random
from .base import BaseMusicClient
from rich.progress import Progress
from ..utils.neteaseutils import EapiCryptoUtils
from ..utils import byte2mb, resp2json, isvalidresp, seconds2hms, legalizestring, safeextractfromdict, AudioLinkTester


'''NeteaseMusicClient'''
class NeteaseMusicClient(BaseMusicClient):
    source = 'NeteaseMusicClient'
    def __init__(self, **kwargs):
        super(NeteaseMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Referer': 'https://music.163.com/',
        }
        self.default_download_headers = {}
        self.default_headers = self.default_search_headers
        default_cookies = {'MUSIC_U': '1eb9ce22024bb666e99b6743b2222f29ef64a9e88fda0fd5754714b900a5d70d993166e004087dd3b95085f6a85b059f5e9aba41e3f2646e3cebdbec0317df58c119e5'}
        if not self.default_search_cookies: self.default_search_cookies = default_cookies
        if not self.default_download_cookies: self.default_download_cookies = default_cookies
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = {}, request_overrides: dict = {}):
        # search rules
        default_rule = {'s': keyword, 'type': 1, 'limit': 10, 'offset': 0}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://music.163.com/api/cloudsearch/pc'
        search_urls, page_size, count = [], 10, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['offset'] = int(count // page_size) * page_size
            search_urls.append({'url': base_url, 'data': page_rule})
            count += page_size
        # return
        return search_urls
    '''_search'''
    def _search(self, keyword: str = '', search_url: dict = {}, request_overrides: dict = {}, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        search_meta = copy.deepcopy(search_url)
        search_url = search_meta.pop('url')
        # successful
        try:
            # --search results
            resp = self.post(search_url, **search_meta, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['result']['songs']
            for search_result in search_results:
                # --download results
                if 'id' not in search_result:
                    continue
                qualties = ["jymaster", "jyeffect", "sky", "hires", "lossless", "exhigh", "standard"]
                for quality in qualties:
                    header = {"os": "pc", "appver": "", "osver": "", "deviceId": "pyncm!"}
                    header["requestId"] = str(random.randrange(20000000, 30000000))
                    params = {
                        'ids': [search_result['id']], 'level': quality, 'encodeType': 'flac', 'header': json.dumps(header),
                    }
                    if quality == 'sky': params['immerseType'] = 'c51'
                    params = EapiCryptoUtils.encryptparams(url='https://interface3.music.163.com/eapi/song/enhance/player/url/v1', payload=params)
                    resp = self.post('https://interface3.music.163.com/eapi/song/enhance/player/url/v1', data={"params": params}, **request_overrides)
                    if not isvalidresp(resp):  continue
                    download_result: dict = resp2json(resp)
                    if (download_result.get('code') not in [200]) or ('data' not in download_result) or (not download_result['data']) or \
                       (not isinstance(download_result['data'], list)) or (not isinstance(download_result['data'][0], dict)):
                        continue
                    download_url = download_result['data'][0].get('url', '')
                    if not download_url: continue
                    download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_cookies).test(download_url, request_overrides)
                    if download_url_status['ok']: break
                if not download_url: continue
                if not download_url_status['ok']: continue
                duration = seconds2hms(search_result.get('dt', 0) / 1000 if isinstance(search_result.get('dt', 0), (int, float)) else '0')
                ext = download_result['data'][0].get('type', 'mp3')
                file_size = byte2mb(download_result['data'][0].get('size', '0'))
                # --lyric results
                data = {'id': search_result['id'], 'cp': 'false', 'tv': '0', 'lv': '0', 'rv': '0', 'kv': '0', 'yv': '0', 'ytv': '0', 'yrv': '0'}
                resp = self.post('https://interface3.music.163.com/api/song/lyric', data=data, **request_overrides)
                if isvalidresp(resp):
                    try:
                        lyric_result: dict = resp2json(resp)
                        lyric = lyric_result.get('lrc', {}).get('lyric', 'NULL') or lyric_result.get('tlyric', {}).get('lyric', 'NULL')
                    except:
                        lyric_result, lyric = dict(), 'NULL'
                else:
                    lyric_result, lyric = dict(), 'NULL'
                # --construct song_info
                song_info = dict(
                    source=self.source, raw_data=dict(search_result=search_result, download_result=download_result, lyric_result=lyric_result), 
                    download_url_status=download_url_status, download_url=download_url, ext=ext, file_size=file_size, lyric=lyric, duration=duration, 
                    song_name=legalizestring(search_result.get('name', 'NULL'), replace_null_string='NULL'), 
                    singers=legalizestring(', '.join([singer.get('name', 'NULL') for singer in search_result.get('ar', [])]), replace_null_string='NULL'), 
                    album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], 'NULL'), replace_null_string='NULL'),
                    identifier=search_result['id'],
                )
                # --append to song_infos
                song_infos.append(song_info)
            # --update progress
            progress.advance(progress_id, 1)
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Error: {err})")
        # return
        return song_infos