'''
Function:
    Implementation of LizhiMusicClient: https://www.lizhi.fm/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import legalizestring, resp2json, seconds2hms, usesearchheaderscookies, AudioLinkTester, WhisperLRC


'''LizhiMusicClient'''
class LizhiMusicClient(BaseMusicClient):
    source = 'LizhiMusicClient'
    def __init__(self, **kwargs):
        super(LizhiMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
            'Referer': 'https://m.lizhi.fm',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = {}, request_overrides: dict = {}):
        # search rules
        default_rule = {'deviceId': "h5-b6ef91a9-3dbb-c716-1fdd-43ba08851150", "keywords": keyword, "page": 1, "receiptData": ""}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://m.lizhi.fm/vodapi/search/voice?'
        search_urls, page_size, count = [], 20, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['page'] = int(count // page_size)
            if len(search_urls) > 0:
                try:
                    resp = self.get(search_urls[-1], **request_overrides)
                    receipt_data = resp2json(resp)['receiptData']
                except:
                    receipt_data = ""
                page_rule['receiptData'] = receipt_data
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
            search_results = resp2json(resp)['data']
            for search_result in search_results:
                # --download results
                if ('userInfo' not in search_result) or ('voiceInfo' not in search_result) or ('voicePlayProperty' not in search_result) or ('voiceId' not in search_result['voiceInfo']):
                    continue
                download_url = search_result['voicePlayProperty'].get('trackUrl', '')
                if not download_url: continue
                for quality in ['_ud.mp3', '_hd.mp3', '_sd.m4a']:
                    download_url = download_url[:-7] + quality
                    download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).test(download_url, request_overrides)
                    if download_url_status['ok']: break
                if not download_url_status['ok']: continue
                duration = seconds2hms(search_result['voiceInfo'].get('duration', '0'))
                try:
                    download_result = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).probe(download_url, request_overrides)
                except:
                    download_result = {'download_url': download_url, 'file_size': 'NULL', 'ext': 'NULL'}
                if download_result['ext'] == 'NULL':
                    download_result['ext'] = download_url.split('.')[-1].split('?')[0] or 'mp3'
                # --lyric results, WhisperLRC runs very slowly, disable it by default
                try:
                    if os.environ.get('ENABLE_WHISPERLRC', 'False').lower() == 'true':
                        lyric_result = WhisperLRC(model_size_or_path='small').fromurl(
                            download_url, headers=self.default_download_headers, cookies=self.default_download_cookies, request_overrides=request_overrides
                        )
                        lyric = lyric_result['lyric']
                    else:
                        lyric_result, lyric = dict(), 'NULL'
                except:
                    lyric_result, lyric = dict(), 'NULL'
                # --construct song_info
                song_info = dict(
                    source=self.source, raw_data=dict(search_result=search_result, download_result=download_result, lyric_result=lyric_result), 
                    download_url_status=download_url_status, download_url=download_url, ext=download_result['ext'], file_size=download_result['file_size'], 
                    lyric=lyric, duration=duration, song_name=legalizestring(search_result['voiceInfo'].get('name', 'NULL'), replace_null_string='NULL'), 
                    singers=legalizestring(search_result['userInfo'].get('name', 'NULL'), replace_null_string='NULL'), 
                    album=legalizestring(search_result['voiceInfo'].get('lableName', 'NULL'), replace_null_string='NULL'),
                    identifier=search_result['voiceInfo']['voiceId'],
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