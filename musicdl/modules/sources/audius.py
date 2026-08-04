'''
Function:
    Implementation of AudiusMusicClient: https://audius.co/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
from contextlib import suppress
from rich.progress import Progress
from ..sources import BaseMusicClient
from urllib.parse import urlencode, urlparse, parse_qs
from ..utils import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict, SongInfo, AudioLinkTester, SongInfoUtils


'''AudiusMusicClient'''
class AudiusMusicClient(BaseMusicClient):
    source = 'AudiusMusicClient'
    def __init__(self, **kwargs):
        super(AudiusMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"accept": "application/json", "referer": "https://audius.co/", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "authorization": ""}
        self.default_download_headers = {"referer": "https://audius.co/", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'query': keyword, 'limit': self.search_size_per_page, 'offset': 0, 'app_name': 'musicdl'}).update(rule)
        # construct search urls
        search_urls, count, base_url, page_size = [], 0, 'https://api.audius.co/v1/tracks/search?', self.search_size_per_page
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['offset'] = count
            page_rule['limit'] = page_size
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, song_info, song_info_flac = request_overrides or {}, SongInfo(source=self.source), song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            download_url_status: dict = self.audio_link_tester.test(url=(download_url := f'https://api.audius.co/v1/tracks/{song_id}/stream?app_name=musicdl'), request_overrides=request_overrides, renew_session=True)
            duration_in_secs, artwork = int(float(search_result.get('duration') or 0)), search_result.get('artwork') or {}
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': {'url': download_url}, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['user', 'name'], None) or safeextractfromdict(search_result, ['user', 'handle'], None)), album=legalizestring(search_result.get('album_name') or search_result.get('playlist_name')), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric='NULL', cover_url=artwork.get('1000x1000') or artwork.get('480x480') or artwork.get('150x150'), download_url=download_url_status['download_url'], download_url_status=download_url_status,
            )
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, search_result_idx, page_size = request_overrides or {}, -1, int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('limit', [self.search_size_per_page])[0]))
        page_no = int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('offset', [0])[0]) / page_size) + 1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp=resp).get('data', [])):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
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
