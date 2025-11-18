'''
Function:
    Implementation of QianqianMusicClient: http://music.taihe.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import time
import copy
import hashlib
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import byte2mb, resp2json, isvalidresp, seconds2hms, legalizestring, safeextractfromdict, usesearchheaderscookies, AudioLinkTester


'''QianqianMusicClient'''
class QianqianMusicClient(BaseMusicClient):
    source = 'QianqianMusicClient'
    def __init__(self, **kwargs):
        super(QianqianMusicClient, self).__init__(**kwargs)
        self.appid = '16073360'
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Referer': 'https://music.91q.com/',
            'From': 'Web',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_addsignandtstoparams'''
    def _addsignandtstoparams(self, params: dict):
        secret = '0b50b02fd0d73a9c4c8c3a781c30845f'
        params['timestamp'] = str(int(time.time()))
        keys = sorted(params.keys())
        string = "&".join(f"{k}={params[k]}" for k in keys)
        params['sign'] = hashlib.md5((string + secret).encode('utf-8')).hexdigest()
        return params
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = {}, request_overrides: dict = {}):
        # search rules
        default_rule = {'word': keyword, 'type': '1', 'pageNo': '1', 'pageSize': '10', 'appid': self.appid}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://music.91q.com/v1/search?'
        search_urls, page_size, count = [], 10, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['pageNo'] = str(int(count // page_size) + 1)
            page_rule = self._addsignandtstoparams(params=page_rule)
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = {}, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['data']['typeTrack']
            for search_result in search_results:
                # --download results
                if 'TSID' not in search_result:
                    continue
                params = {'TSID': search_result['TSID'], 'appid': self.appid}
                params = self._addsignandtstoparams(params=params)
                resp = self.get("https://music.91q.com/v1/song/tracklink", params=params, **request_overrides)
                if not isvalidresp(resp): continue
                download_result: dict = resp2json(resp)
                download_url = safeextractfromdict(download_result, ['data', 'path'], '') or safeextractfromdict(download_result, ['data', 'trail_audio_info', 'path'], '')
                if not download_url: continue
                download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).test(download_url, request_overrides)
                if not download_url_status['ok']: continue
                file_size = byte2mb(download_result.get('size', '0'))
                duration = seconds2hms(download_result.get('duration', '0'))
                ext = download_result.get('format', 'mp3')
                if file_size == 'NULL':
                    download_result_suppl = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).probe(download_url, request_overrides)
                    download_result['download_result_suppl'] = download_result_suppl
                    file_size, ext = download_result_suppl['file_size'], download_result_suppl['ext'] if download_result_suppl['ext'] not in ['NULL'] else ext
                # --lyric results
                resp = self.get(search_result['lyric'], **request_overrides)
                if isvalidresp(resp):
                    try:
                        resp.encoding = 'utf-8'
                        lyric = resp.text or 'NULL'
                        lyric_result = dict(lyric=lyric)
                    except:
                        lyric_result, lyric = dict(), 'NULL'
                else:
                    lyric_result, lyric = dict(), 'NULL'
                # --construct song_info
                song_info = dict(
                    source=self.source, raw_data=dict(search_result=search_result, download_result=download_result, lyric_result=lyric_result), 
                    download_url_status=download_url_status, download_url=download_url, ext=ext, file_size=file_size, lyric=lyric, duration=duration, 
                    song_name=legalizestring(search_result.get('title', 'NULL'), replace_null_string='NULL'), 
                    singers=legalizestring(', '.join([singer.get('name', 'NULL') for singer in search_result.get('artist', [])]), replace_null_string='NULL'), 
                    album=legalizestring(search_result.get('albumTitle', 'NULL'), replace_null_string='NULL'),
                    identifier=search_result['TSID'],
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