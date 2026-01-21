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
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict, seconds2hms, searchdictbykey, extractdurationsecondsfromlrc, cleanlrc, SongInfo, QuarkParser


'''MituMusicClient'''
class MituMusicClient(BaseMusicClient):
    source = 'MituMusicClient'
    MUSIC_QUALITY_RANK = {"DSD": 100, "DSF": 100, "DFF": 100, "WAV": 95, "AIFF": 95, "FLAC": 90, "ALAC": 90, "APE": 88, "WV": 88, "OPUS": 70, "AAC": 65, "M4A": 65, "OGG": 60, "VORBIS": 60, "MP3": 50, "WMA": 45}
    def __init__(self, **kwargs):
        super(MituMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {
            "accept": "*/*", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "origin": "https://www.qqmp3.vip",
            "priority": "u=1, i", "referer": "https://www.qqmp3.vip/", "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"', 
            "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"', "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {'keyword': keyword, 'type': 'search'}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://api.qqmp3.vip/api/songs.php?'
        page_rule = copy.deepcopy(default_rule)
        search_urls = [base_url + urlencode(page_rule)]
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info = request_overrides or {}, SongInfo(source=self.source)
        parse_format_func = lambda label: next((fmt for fmt in sorted(MituMusicClient.MUSIC_QUALITY_RANK, key=len, reverse=True) if re.search(rf"\b{re.escape(fmt)}\b", (s := label.upper())) or fmt in s), "UNKNOWN")
        quality_score_func = lambda item: MituMusicClient.MUSIC_QUALITY_RANK.get(parse_format_func(item.split("$$", 1)[0]), 0)
        # parse
        try: resp = self.get(f'https://api.qqmp3.vip/api/kw.php?rid={search_result["rid"]}&type=json&level=exhigh&lrc=true', **request_overrides); resp.raise_for_status(); lyric_result = resp2json(resp=resp)
        except: lyric_result = {}
        quark_download_urls: list[str] = search_result.get('downurl', []) or []
        quark_download_urls = sorted(quark_download_urls, key=lambda x: quality_score_func(x), reverse=True)
        for quark_download_url in quark_download_urls:
            download_result, download_url = QuarkParser.parsefromurl(quark_download_url, **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            duration = [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]
            duration_s = duration[0] if duration else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': lyric_result}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)),
                singers=legalizestring(safeextractfromdict(search_result, ['artist'], None)), album='NULL', ext='mp3', file_size='NULL', identifier=search_result['rid'], duration_s=duration_s,
                duration=seconds2hms(duration_s), lyric=cleanlrc(safeextractfromdict(lyric_result, ['data', 'lrc'], '')), cover_url=safeextractfromdict(search_result, ['pic'], None), download_url=download_url,
                download_url_status=self.quark_audio_link_tester.test(download_url, request_overrides), default_download_headers=self.quark_default_download_headers,
            )
            song_info.download_url_status['probe_status'] = self.quark_audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
            if song_info.with_valid_download_url: break
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration = seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info = request_overrides or {}, SongInfo(source=self.source)
        # parse
        resp = self.get(f'https://api.qqmp3.vip/api/kw.php?rid={search_result["rid"]}&type=json&level=exhigh&lrc=true', **request_overrides)
        resp.raise_for_status()
        download_result = resp2json(resp=resp)
        download_url = download_result['data']['url']
        if not download_url: return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)),
            singers=legalizestring(safeextractfromdict(search_result, ['artist'], None)), album='NULL', ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=search_result['rid'], 
            duration='-:-:-', lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lrc'], '')), cover_url=safeextractfromdict(search_result, ['pic'], None), download_url=download_url,
            download_url_status=self.audio_link_tester.test(download_url, request_overrides), 
        )
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration = seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
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
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['data']
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('rid' not in search_result): continue
                song_info = SongInfo(source=self.source)
                # ----parse from quark links
                if self.quark_parser_config.get('cookies'): song_info = self._parsesearchresultfromquark(search_result, request_overrides)
                # ----parse from play url
                if not song_info.with_valid_download_url: song_info = self._parsesearchresultfromweb(search_result, request_overrides)
                # ----filter if invalid
                if not song_info.with_valid_download_url: continue
                # --append to song_infos
                song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
            # --update progress
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Error: {err})")
        # return
        return song_infos