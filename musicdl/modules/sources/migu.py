'''
Function:
    Implementation of MiguMusicClient: https://music.migu.cn/v5/#/musicLibrary
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
from .base import BaseMusicClient
from rich.progress import Progress
from urllib.parse import urlencode
from ..utils import byte2mb, resp2json, isvalidresp, seconds2hms, legalizestring, safeextractfromdict, AudioLinkTester


'''MiguMusicClient'''
class MiguMusicClient(BaseMusicClient):
    source = 'MiguMusicClient'
    def __init__(self, **kwargs):
        super(MiguMusicClient, self).__init__(**kwargs)
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
        default_rule = {
            "text": keyword, 'pageNo': 1, 'pageSize': 10
        }
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://app.u.nf.migu.cn/pc/resource/song/item/search/v1.0?'
        search_urls, page_size, count = [], 10, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['pageNo'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = {}, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)
            for search_result in search_results:
                # --download results
                if 'copyrightId' not in search_result or 'contentId' not in search_result:
                    continue
                file_size, ext = 'NULL', 'NULL'
                for rate in sorted(search_result.get('audioFormats', []), key=lambda x: int(x['isize']), reverse=True):
                    if byte2mb(rate.get('isize', '0')) == 'NULL' or (not rate.get('formatType', '')) or (not rate.get('resourceType', '')):
                        continue
                    ext = {'PQ': 'mp3', 'HQ': 'mp3', 'SQ': 'flac', 'ZQ24': 'flac'}.get(rate['formatType'], 'NULL')
                    file_size = byte2mb(rate.get('isize', '0'))
                    download_url = f"https://app.pd.nf.migu.cn/MIGUM3.0/v1.0/content/sub/listenSong.do?channel=mx&copyrightId={search_result['copyrightId']}&contentId={search_result['contentId']}&toneFlag={rate['formatType']}&resourceType={rate['resourceType']}&userId=15548614588710179085069&netType=00"
                    download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_cookies).test(download_url, request_overrides)
                    if download_url_status['ok']: break
                if not download_url_status['ok']: continue
                try:
                    download_result = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_cookies).probe(download_url, request_overrides)
                except:
                    download_result = {'download_url': download_url, 'file_size': 'NULL', 'ext': 'NULL'}
                if download_result['ext'] == 'NULL':
                    download_result['ext'] = ext if (ext and ext != 'NULL') else 'mp3'
                if download_result['file_size'] == 'NULL':
                    download_result['file_size'] = file_size
                duration = seconds2hms(search_result.get('duration', '0'))
                # --lyric results
                lyric_url = safeextractfromdict(search_result, ['ext', 'lrcUrl'], '') or safeextractfromdict(search_result, ['ext', 'mrcUrl'], '') or \
                            safeextractfromdict(search_result, ['ext', 'trcUrl'], '')
                if lyric_url:
                    resp = self.get(lyric_url, **request_overrides)
                    if isvalidresp(resp):
                        resp.encoding = 'utf-8'
                        lyric_result, lyric = {'lyric': resp.text}, resp.text
                    else:
                        lyric_result, lyric = {}, 'NULL'
                else:
                    lyric_result, lyric = {}, 'NULL'
                # --construct song_info
                song_info = dict(
                    source=self.source, raw_data=dict(search_result=search_result, download_result=download_result, lyric_result=lyric_result), 
                    download_url_status=download_url_status, download_url=download_url, ext=download_result['ext'], file_size=download_result['file_size'], 
                    lyric=lyric, duration=duration, song_name=legalizestring(search_result.get('songName', 'NULL'), replace_null_string='NULL'), 
                    singers=legalizestring(', '.join([singer.get('name', 'NULL') for singer in search_result.get('singerList', [])]), replace_null_string='NULL'), 
                    album=legalizestring(search_result.get('album', 'NULL'), replace_null_string='NULL'),
                    identifier=search_result['copyrightId'] + '-' + search_result['contentId'],
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