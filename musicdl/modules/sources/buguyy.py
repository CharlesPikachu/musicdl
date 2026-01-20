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
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict, searchdictbykey, seconds2hms, cleanlrc, SongInfo, QuarkParser


'''BuguyyMusicClient'''
class BuguyyMusicClient(BaseMusicClient):
    source = 'BuguyyMusicClient'
    def __init__(self, **kwargs):
        super(BuguyyMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {
            "accept": "application/json, text/plain, */*", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "origin": "https://buguyy.top", "priority": "u=1, i", "referer": "https://buguyy.top/", "sec-ch-ua": "\"Chromium\";v=\"142\", \"Google Chrome\";v=\"142\", \"Not_A Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
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
        default_rule = {'keyword': keyword}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://a.buguyy.top/newapi/search.php?'
        page_rule = copy.deepcopy(default_rule)
        search_urls = [base_url + urlencode(page_rule)]
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info = request_overrides or {}, SongInfo(source=self.source)
        # parse
        try:
            resp = self.get(f'https://a.buguyy.top/newapi/geturl2.php?id={search_result["id"]}', verify=False, **request_overrides)
            resp.raise_for_status()
            lyric_result = resp2json(resp=resp)
        except:
            lyric_result = dict()
        quark_download_urls = [u for u in [search_result.get('downurl', ''), search_result.get('ktmdownurl', '')] if u]
        for quark_download_url in quark_download_urls:
            m = re.search(r"(?i)(?:WAV|FLAC)#(https?://[^#]+)|MP3#(https?://[^#]+)", quark_download_url)
            quark_download_url = m.group(1) or m.group(2)
            download_result, download_url = QuarkParser.parsefromurl(quark_download_url, **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            duration = [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]
            duration_s = duration[0] if duration else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': lyric_result}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['title'], None)), 
                singers=legalizestring(safeextractfromdict(search_result, ['singer'], None)), album=legalizestring(safeextractfromdict(lyric_result, ['data', 'album'], None)), ext='wav',
                file_size='NULL', identifier=search_result['id'], duration_s=duration_s, duration=seconds2hms(duration_s), lyric=cleanlrc(safeextractfromdict(lyric_result, ['data', 'lrc'], '')),
                cover_url=safeextractfromdict(search_result, ['picurl'], None), download_url=download_url, download_url_status=self.quark_audio_link_tester.test(download_url, request_overrides),
                default_download_headers=self.quark_default_download_headers
            )
            song_info.download_url_status['probe_status'] = self.quark_audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
            if song_info.with_valid_download_url: break
        if not song_info.duration or song_info.duration == '-:-:-':
            try: song_info.duration = '{:02d}:{:02d}:{:02d}'.format(*([0,0,0] + list(map(int, re.findall(r'\d+', safeextractfromdict(lyric_result, ['data', 'duration'], '')))))[-3:])
            except: song_info.duration = '-:-:-'
            if song_info.duration == '00:00:00': song_info.duration = '-:-:-'
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        song_info.lyric = re.sub(r'<br\s*/?>', '\n', song_info.lyric, flags=re.IGNORECASE)
        song_info.lyric = html.unescape(song_info.lyric)
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info = request_overrides or {}, SongInfo(source=self.source)
        # parse
        try:
            resp = self.get(f'https://a.buguyy.top/newapi/geturl2.php?id={search_result["id"]}', verify=False, **request_overrides)
            resp.raise_for_status()
            download_result = resp2json(resp=resp)
        except:
            download_result = dict()
        download_url = safeextractfromdict(download_result, ['data', 'url'], '')
        if not download_url: return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['title'], None)), 
            singers=legalizestring(safeextractfromdict(search_result, ['singer'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url.split('?')[0].split('.')[-1],
            file_size='NULL', identifier=search_result['id'], duration=None, lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lrc'], '')), cover_url=safeextractfromdict(search_result, ['picurl'], None), 
            download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        song_info.download_url_status['probe_status'] = self.quark_audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
        if not song_info.duration or song_info.duration == '-:-:-':
            try: song_info.duration = '{:02d}:{:02d}:{:02d}'.format(*([0,0,0] + list(map(int, re.findall(r'\d+', safeextractfromdict(download_result, ['data', 'duration'], '')))))[-3:])
            except: song_info.duration = '-:-:-'
            if song_info.duration == '00:00:00': song_info.duration = '-:-:-'
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        song_info.lyric = re.sub(r'<br\s*/?>', '\n', song_info.lyric, flags=re.IGNORECASE)
        song_info.lyric = html.unescape(song_info.lyric)
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
            resp = self.get(search_url, verify=False, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp=resp)['data']['list']
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('id' not in search_result): continue
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