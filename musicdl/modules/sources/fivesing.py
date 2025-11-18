'''
Function:
    Implementation of FiveSingMusicClient: https://5sing.kugou.com/index.html
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import legalizestring, byte2mb, resp2json, isvalidresp, usesearchheaderscookies, AudioLinkTester


'''FiveSingMusicClient'''
class FiveSingMusicClient(BaseMusicClient):
    source = 'FiveSingMusicClient'
    def __init__(self, **kwargs):
        super(FiveSingMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = {}, request_overrides: dict = {}):
        # search rules
        default_rule = {'keyword': keyword, 'sort': 1, 'page': 1, 'filter': 0, 'type': 0}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'http://search.5sing.kugou.com/home/json?'
        search_urls, page_size, count = [], 10, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['page'] = int(count // page_size) + 1
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
            search_results = resp2json(resp)['list']
            for search_result in search_results:
                # --download results
                if 'songId' not in search_result or 'typeEname' not in search_result:
                    continue
                params = {'songid': str(search_result['songId']), 'songtype': search_result['typeEname']}
                resp = self.get('http://mobileapi.5sing.kugou.com/song/getSongUrl', params=params, **request_overrides)
                if (not isvalidresp(resp)) or (resp2json(resp)['code'] not in [1000]):
                    continue
                download_result: dict = resp2json(resp)
                for quality in ['sq', 'hq', 'lq']:
                    data: dict = download_result.get('data', {})
                    download_url = data.get(f'{quality}url', '').strip() or data.get(f'{quality}url_backup', '').strip()
                    if not download_url: continue
                    ext = data.get(f'{quality}ext', 'mp3').strip() or 'mp3'
                    file_size = byte2mb(data.get(f'{quality}size', '0'))
                    download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).test(download_url, request_overrides)
                    if download_url_status['ok']: break
                if not download_url: continue
                if not download_url_status['ok']: continue
                # --lyric results
                params = {'songid': str(search_result['songId']), 'songtype': search_result['typeEname'], 'songfields': '', 'userfields': ''}
                resp = self.get('http://mobileapi.5sing.kugou.com/song/newget', params=params, **request_overrides)
                if isvalidresp(resp):
                    lyric_result: dict = resp2json(resp)
                else:
                    lyric_result = {}
                try:
                    lyric = str(lyric_result.get('data', {}).get('dynamicWords', 'NULL')).strip() or 'NULL'
                except:
                    lyric = 'NULL'
                # --construct song_info
                song_info = dict(
                    source=self.source, raw_data=dict(search_result=search_result, download_result=download_result, lyric_result=lyric_result), 
                    download_url_status=download_url_status, download_url=download_url, ext=ext, file_size=file_size, lyric=lyric, duration='-:-:-',
                    song_name=legalizestring(search_result.get('songName', 'NULL'), replace_null_string='NULL'), 
                    singers=legalizestring(search_result.get('singer', 'NULL'), replace_null_string='NULL'), 
                    album=legalizestring(lyric_result.get('data', {}).get('albumName', 'NULL'), replace_null_string='NULL'),
                    identifier=search_result['songId'],
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