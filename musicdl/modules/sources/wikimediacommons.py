'''
Function:
    Implementation of WikimediaCommonsMusicClient: https://commons.wikimedia.org/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import random
import string
from contextlib import suppress
from rich.progress import Progress
from collections.abc import Callable
from ..sources import BaseMusicClient
from urllib.parse import urlencode, urlparse, parse_qs
from ..utils import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict, SongInfo, AudioLinkTester, SongInfoUtils


'''WikimediaCommonsMusicClient'''
class WikimediaCommonsMusicClient(BaseMusicClient):
    source = 'WikimediaCommonsMusicClient'
    def __init__(self, **kwargs):
        super(WikimediaCommonsMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"accept": "application/json", "referer": "https://commons.wikimedia.org/", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"}
        self.default_download_headers = {"referer": "https://commons.wikimedia.org/", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {
            'action': 'query', 'generator': 'search', 'gsrsearch': f'{keyword} filetype:audio', 'gsrnamespace': 6, 'gsrlimit': self.search_size_per_page, 'gsroffset': 0, 
            'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata', 'iiurlwidth': 500, 'format': 'json', 'formatversion': 2, 'origin': '*',
        }).update(rule)
        # construct search urls
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'https://commons.wikimedia.org/w/api.php?'
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['gsroffset'] = count
            page_rule['gsrlimit'] = page_size
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, song_info, song_info_flac, image_info = request_overrides or {}, SongInfo(source=self.source), song_info_flac or SongInfo(source=self.source), safeextractfromdict(search_result, ['imageinfo', 0], {}) or {}
        extract_ext_meta_data_func: Callable[[dict], dict] = lambda image_info: {key: value.get('value') if isinstance(value, dict) else value for key, value in (image_info.get('extmetadata', {}) or {}).items()}
        if not (download_url := (image_info.get('url') or '')) or not str(download_url).startswith('http'): return song_info
        if not str(image_info.get('mime', '')).startswith('audio/') and os.path.splitext(urlparse(str(download_url)).path)[1].lower().lstrip('.') not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            title = (ext_meta_data := extract_ext_meta_data_func(image_info)).get('ObjectName') or ext_meta_data.get('ImageDescription') or str(search_result.get('title', '')).removeprefix('File:')
            singer = ext_meta_data.get('Artist') or ext_meta_data.get('Credit') or ext_meta_data.get('Author') or ext_meta_data.get('Attribution')
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(os.path.splitext(str(title))[0]), singers=legalizestring(singer), album=legalizestring(ext_meta_data.get('Collection') or ext_meta_data.get('Categories') or 'Wikimedia Commons'), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=str(search_result.get('pageid') or ''.join(random.choices(string.ascii_letters + string.digits, k=10))), duration_s=image_info.get('duration'), duration=SongInfoUtils.seconds2hms(image_info.get('duration')), lyric='NULL', cover_url=image_info.get('thumburl'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, search_result_idx, page_size = request_overrides or {}, -1, int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('gsrlimit', [self.search_size_per_page])[0]))
        page_no = int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('gsroffset', [0])[0]) / page_size) + 1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            search_results = list(pages.values()) if isinstance((pages := (resp2json(resp=resp).get('query', {}) or {}).get('pages', [])), dict) else pages
            for search_result_idx, search_result in enumerate(search_results):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, request_overrides=request_overrides)
                # --append to song_infos
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
            # --update progress
            progress.update(task_id, description=f'{self.source}._search >>> {search_result_idx+1} search results processed on page {page_no}')
        # failure
        except Exception as err:
            progress.update(task_id, description=f'{self.source}._search >>> {keyword} on page {page_no} (Error: {err})')
            self.logger_handle.error(f'{self.source}._search >>> {keyword} on page {page_no} (Error: {err})', disable_print=self.disable_print)
        # return
        return song_infos