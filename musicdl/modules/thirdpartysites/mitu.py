'''
Function:
    Implementation of MituMusicClient: https://www.qqmp3.vip/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
from contextlib import suppress
from urllib.parse import urlencode
from rich.progress import Progress
from ..sources import BaseMusicClient
from ..utils import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict, searchdictbykey, extractdurationsecondsfromlrc, cleanlrc, SongInfo, QuarkParser, AudioLinkTester, SongInfoUtils


'''MituMusicClient'''
class MituMusicClient(BaseMusicClient):
    source = 'MituMusicClient'
    MUSIC_QUALITY_RANK = {"DSD": 100, "DSF": 100, "DFF": 100, "WAV": 95, "AIFF": 95, "FLAC": 90, "ALAC": 90, "APE": 88, "WV": 88, "OPUS": 70, "AAC": 65, "M4A": 65, "OGG": 60, "VORBIS": 60, "MP3": 50, "WMA": 45}
    def __init__(self, **kwargs):
        super(MituMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {
            "accept": "*/*", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "origin": "https://www.qqmp3.vip", "priority": "u=1, i", "referer": "https://www.qqmp3.vip/", "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"', 
            "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"', "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'keyword': keyword, 'type': 'search'}).update(rule)
        # construct search urls
        base_url = 'https://api.qqmp3.vip/api/songs.php?'
        search_urls = [base_url + urlencode(copy.deepcopy(default_rule))]
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result["rid"]
        parse_format_func = lambda label: next((fmt for fmt in sorted(MituMusicClient.MUSIC_QUALITY_RANK, key=len, reverse=True) if re.search(rf"\b{re.escape(fmt)}\b", (s := str(label).upper())) or fmt in s), "UNKNOWN")
        quality_score_func = lambda item: MituMusicClient.MUSIC_QUALITY_RANK.get(parse_format_func(item.split("$$", 1)[0]), 0)
        # parse download url
        (resp := self.get(f'https://api.qqmp3.vip/api/kw.php?rid={song_id}&type=json&level=exhigh&lrc=true', **request_overrides)).raise_for_status()
        quark_download_urls, lyric_result = search_result.get('downurl', []) or [], resp2json(resp=resp)
        for quark_download_url in sorted(quark_download_urls, key=lambda x: quality_score_func(x), reverse=True):
            quark_download_url = str(quark_download_url)[str(quark_download_url).index('http'):]
            if not isinstance(quark_download_url, str) or not quark_download_url.startswith('http'): continue
            download_result, download_url = QuarkParser.parsefromurl(quark_download_url, **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]) else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': lyric_result}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(search_result.get('artist')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, 
                duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(safeextractfromdict(lyric_result, ['data', 'lrc'], 'NULL')), cover_url=search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers,
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # parse lyric result
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if not song_info.duration or song_info.duration == '-:-:-' or song_info.duration == '00:00:00': song_info.duration = SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result["rid"]
        # parse download url
        (resp := self.get(f'https://api.qqmp3.vip/api/kw.php?rid={song_id}&type=json&level=exhigh&lrc=true', **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['data']['url']) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(search_result.get('artist')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lrc'], 'NULL')), cover_url=search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status,
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if not song_info.duration or song_info.duration == '-:-:-' or song_info.duration == '00:00:00': song_info.duration = SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp)['data']:
                # --download results
                if not isinstance(search_result, dict) or ('rid' not in search_result): continue
                # ----parse from quark links
                with suppress(Exception): song_info = self._parsesearchresultfromquark(search_result, request_overrides) if self.quark_parser_config.get('cookies') else SongInfo(source=self.source)
                # ----parse from play url
                with suppress(Exception): song_info = self._parsesearchresultfromweb(search_result, request_overrides) if not song_info.with_valid_download_url else song_info
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
            # --update progress
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Error: {err})")
            self.logger_handle.error(f"{self.source}._search >>> {search_url} (Error: {err})", disable_print=self.disable_print)
        # return
        return song_infos