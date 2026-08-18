'''
Function:
    Implementation of BuguyyMusicClient: https://buguyy.top/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import html
import copy
import warnings
from contextlib import suppress
from urllib.parse import urlencode
from rich.progress import Progress
from typing_extensions import Unpack
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict, searchdictbykey, extractdurationsecondsfromlrc, cleanlrc, SongInfo, QuarkParser, AudioLinkTester, SongInfoUtils
warnings.filterwarnings('ignore')


'''BuguyyMusicClient'''
class BuguyyMusicClient(BaseMusicClient):
    source = 'BuguyyMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(BuguyyMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36", "Referer": "https://buguyy.top/", "Content-Type": "application/json"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'keyword': keyword}).update(rule)
        # construct search urls based on search rules
        base_url = 'https://buguyy.top/api/search?'
        search_urls = [base_url + urlencode(copy.deepcopy(default_rule))]
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result.get("id")
        # parse download url
        (resp := self.get(f'https://buguyy.top/api/getdown?id={song_id}', verify=False, **request_overrides)).raise_for_status()
        quark_download_url: str = safeextractfromdict((download_result := resp2json(resp=resp)), ['kuakedownurl'], '')
        m = re.search(r"(?i)(?:RAR|WAV|FLAC)#(https?://[^#]+)|MP3#(https?://[^#]+)", quark_download_url)
        download_result['quark_parse_result'], download_url = QuarkParser.parsefromurl(m.group(1) or m.group(2), **self.quark_parser_config)
        download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]) else 0
        (resp := self.get(f'https://buguyy.top/api/geturl?id={song_id}', verify=False, **request_overrides)).raise_for_status()
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': (lyric_result := resp2json(resp=resp))}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('singer')), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(lyric_result.get('lrc') or 'NULL'), cover_url=search_result.get('picurl'), download_url=download_url, download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers
        )
        # parse lyric result
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        song_info.lyric = re.sub(r'<br\s*/?>', '\n', song_info.lyric, flags=re.IGNORECASE); song_info.lyric = cleanlrc(html.unescape(song_info.lyric))
        if not song_info.duration or song_info.duration == '-:-:-' or song_info.duration == '00:00:00': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result.get("id")
        # parse download url
        (resp := self.get(f'https://buguyy.top/api/geturl?id={song_id}', verify=False, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')
        if not download_url or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('singer')), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric=cleanlrc(download_result.get('lrc') or 'NULL'), cover_url=search_result.get('picurl'), download_url=download_url_status['download_url'], download_url_status=download_url_status
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        song_info.lyric = re.sub(r'<br\s*/?>', '\n', song_info.lyric, flags=re.IGNORECASE); song_info.lyric = cleanlrc(html.unescape(song_info.lyric))
        if not song_info.duration or song_info.duration == '-:-:-' or song_info.duration == '00:00:00': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, page_no, search_result_idx = request_overrides or {}, 1, -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, verify=False, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp=resp)['data']):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if not isinstance(search_result, dict) or not search_result.get('id'): continue
                # ----parse from quark links
                with suppress(Exception): song_info = self._parsesearchresultfromquark(search_result, request_overrides) if self.quark_parser_config.get('cookies') else SongInfo(source=self.source)
                # ----parse from play url
                with suppress(Exception): song_info = self._parsesearchresultfromweb(search_result, request_overrides) if not song_info.with_valid_download_url else song_info
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
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