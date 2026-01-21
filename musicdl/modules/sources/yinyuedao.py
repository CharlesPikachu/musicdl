'''
Function:
    Implementation of YinyuedaoMusicClient: https://1mp3.top/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import json_repair
from bs4 import BeautifulSoup
from .base import BaseMusicClient
from rich.progress import Progress
from ..utils import legalizestring, usesearchheaderscookies, safeextractfromdict, seconds2hms, searchdictbykey, SongInfo, QuarkParser


'''YinyuedaoMusicClient'''
class YinyuedaoMusicClient(BaseMusicClient):
    source = 'YinyuedaoMusicClient'
    MUSIC_QUALITY_RANK = {"DSD": 100, "DSF": 100, "DFF": 100, "WAV": 95, "AIFF": 95, "FLAC": 90, "ALAC": 90, "APE": 88, "WV": 88, "OPUS": 70, "AAC": 65, "M4A": 65, "OGG": 60, "VORBIS": 60, "MP3": 50, "WMA": 45}
    def __init__(self, **kwargs):
        super(YinyuedaoMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "priority": "u=0, i", "referer": "https://1mp3.top/",
            "sec-ch-ua": "\"Chromium\";v=\"142\", \"Google Chrome\";v=\"142\", \"Not_A Brand\";v=\"99\"", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document", "sec-fetch-mode": "navigate", "sec-fetch-site": "same-origin", "sec-fetch-user": "?1", "upgrade-insecure-requests": "1",
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
        # construct search urls
        search_urls = [f'https://1mp3.top/?key={keyword}&search=1']
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        soup = BeautifulSoup(html_text, "lxml")
        search_results = []
        for li in soup.select("#musicList > li"):
            music_data = json_repair.loads(li.select_one("a.download-btn").get("data-music"))
            search_results.append({
                "id_attr": li.get("data-music-id"), "title_attr": li.get("data-music-title"), "singer_attr": li.get("data-music-singer"), "cover_attr": li.get("data-music-cover"), "id": music_data.get("id"), "title": music_data.get("title"), "singer": music_data.get("singer"), 
                "picurl": music_data.get("picurl"), "create_time": music_data.get("create_time"), "mtype": music_data.get("mtype"), "downlist": music_data.get("downlist", []) or [], "ktmdownlist": music_data.get("ktmdownlist", []) or [],
            })
        return search_results
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info = request_overrides or {}, SongInfo(source=self.source)
        sort_by_format_func = lambda items: sorted(items, key=lambda x: YinyuedaoMusicClient.MUSIC_QUALITY_RANK.get((x.get("format") or "").upper(), 0), reverse=True)
        # parse
        quark_download_urls = [*(search_result.get('downlist', []) or []), *(search_result.get('ktmdownlist', []) or [])]
        quark_download_urls = sort_by_format_func([qdu for qdu in quark_download_urls if qdu])
        for quark_download_url in quark_download_urls:
            if not safeextractfromdict(quark_download_url, ['format'], ''): continue
            quark_download_url = quark_download_url['url']
            download_result, download_url = QuarkParser.parsefromurl(quark_download_url, **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            duration = [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]
            duration_s = duration[0] if duration else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['title'], None)), 
                singers=legalizestring(safeextractfromdict(search_result, ['singer'], None)), album='NULL', ext='mp3', file_size='NULL', identifier=search_result['id'], duration_s=duration_s, 
                duration=seconds2hms(duration_s), lyric='NULL', cover_url=search_result.get("picurl"), download_url=download_url, download_url_status=self.quark_audio_link_tester.test(download_url, request_overrides), 
                default_download_headers=self.quark_default_download_headers,
            )
            song_info.download_url_status['probe_status'] = self.quark_audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
            if song_info.with_valid_download_url: break
        if not song_info.duration or song_info.duration == 'NULL': song_info.duration = '-:-:-'
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info = request_overrides or {}, SongInfo(source=self.source)
        # parse
        resp = self.get(f'https://1mp3.top/include/geturl.php?id={search_result["id"]}', **request_overrides)
        resp.raise_for_status()
        download_url = resp.text.strip()
        if not download_url or not str(download_url).startswith('http'): return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['title'], None)), 
            singers=legalizestring(safeextractfromdict(search_result, ['singer'], None)), album='NULL', ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', 
            identifier=search_result['id'], duration='-:-:-', lyric='NULL', cover_url=safeextractfromdict(search_result, ['picurl'], None), download_url=download_url, 
            download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
        if not song_info.duration or song_info.duration == 'NULL': song_info.duration = '-:-:-'
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
            search_results = self._parsesearchresultsfromhtml(resp.text)
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