'''
Function:
    Implementation of FangpiMusicClient: https://www.fangpi.net/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import json_repair
from bs4 import BeautifulSoup
from .base import BaseMusicClient
from rich.progress import Progress
from urllib.parse import urljoin, urlparse
from ..utils import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict, searchdictbykey, seconds2hms, extractdurationsecondsfromlrc, cleanlrc, SongInfo, QuarkParser


'''FangpiMusicClient'''
class FangpiMusicClient(BaseMusicClient):
    source = 'FangpiMusicClient'
    def __init__(self, **kwargs):
        super(FangpiMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
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
        search_urls = [f'https://www.fangpi.net/s/{keyword}']
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        soup = BeautifulSoup(html_text, "lxml")
        search_results, base_url = [], "https://www.fangpi.net"
        for row in soup.select('div.card.mb-1 div.card-text > div.row'):
            link = row.select_one('a.music-link')
            if not link: continue
            href = link.get('href', '').strip()
            if not href: continue
            url = urljoin(base_url, href)
            title_span = link.select_one('.music-title span')
            if title_span: title = title_span.get_text(strip=True)
            else: title = link.get_text(strip=True)
            artist_tag = link.find('small')
            artist = artist_tag.get_text(strip=True) if artist_tag else ""
            search_results.append({"title": title, "artist": artist, "url": url})
        return search_results
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, download_result: dict, soup: BeautifulSoup, request_overrides: dict = None):
        # init
        request_overrides, song_info = request_overrides or {}, SongInfo(source=self.source)
        # parse
        quark_download_urls = download_result.get('mp3_extra_urls', []) or []
        for quark_download_url in quark_download_urls:
            quark_download_url = quark_download_url['share_link']
            download_result['quark_parse_result'], download_url = QuarkParser.parsefromurl(quark_download_url, **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            duration = [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]
            duration_s = duration[0] if duration else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['mp3_title'], None)), singers=legalizestring(safeextractfromdict(download_result, ['mp3_author'], None)), 
                album='NULL', ext='mp3', file_size='NULL', identifier=download_result.get('mp3_id') or urlparse(str(search_result['url'])).path.strip('/').split('/')[-1], duration_s=duration_s, duration=seconds2hms(duration_s), lyric=cleanlrc(soup.find("div", id="content-lrc").get_text("\n", strip=True)), 
                cover_url=safeextractfromdict(download_result, ['mp3_cover'], None), download_url=download_url, download_url_status=self.quark_audio_link_tester.test(download_url, request_overrides), default_download_headers=self.quark_default_download_headers,
            )
            song_info.download_url_status['probe_status'] = self.quark_audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
            if song_info.with_valid_download_url: break
        if not song_info.duration or song_info.duration == '-:-:-':
            format_duration_func = lambda d: "{:02}:{:02}:{:02}".format(*([0] * (3 - len(d.split(":"))) + list(map(int, d.split(":")))))
            song_info.duration = format_duration_func(download_result.get('mp3_duration', '00:00:00') or '00:00:00')
            if song_info.duration == '00:00:00': song_info.duration = '-:-:-'
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration = seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, download_result: dict, soup: BeautifulSoup, request_overrides: dict = None):
        # init
        request_overrides, song_info = request_overrides or {}, SongInfo(source=self.source)
        # parse
        if 'play_id' not in download_result or not download_result['play_id']: return song_info
        try:
            resp = self.post('https://www.fangpi.net/api/play-url', json={'id': download_result['play_id']}, **request_overrides)
            resp.raise_for_status()
            download_result['api/play-url'] = resp2json(resp=resp)
        except:
            download_result['api/play-url'] = {}
        download_url = safeextractfromdict(download_result['api/play-url'], ['data', 'url'], '')
        if not download_url: return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['mp3_title'], None)), singers=legalizestring(safeextractfromdict(download_result, ['mp3_author'], None)), 
            album='NULL', ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=download_result.get('mp3_id') or urlparse(str(search_result['url'])).path.strip('/').split('/')[-1], duration='-:-:-', lyric=cleanlrc(soup.find("div", id="content-lrc").get_text("\n", strip=True)), 
            cover_url=safeextractfromdict(download_result, ['mp3_cover'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        song_info.download_url_status['probe_status'] = self.quark_audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
        if not song_info.duration or song_info.duration == '-:-:-':
            try: song_info.duration = '{:02d}:{:02d}:{:02d}'.format(*([0,0,0] + list(map(int, re.findall(r'\d+', safeextractfromdict(download_result, ['data', 'duration'], '')))))[-3:])
            except: song_info.duration = '-:-:-'
            if song_info.duration == '00:00:00': song_info.duration = '-:-:-'
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
            search_results = self._parsesearchresultsfromhtml(resp.text)
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('url' not in search_result): continue
                song_info = SongInfo(source=self.source)
                # ----fetch basic information
                try: resp = self.get(search_result['url'], **request_overrides); resp.raise_for_status()
                except: continue
                soup = BeautifulSoup(resp.text, "lxml")
                script_tag = soup.find("script", string=re.compile(r"window\.appData"))
                if script_tag is None: continue
                js_text: str = script_tag.string
                m = re.search(r"window\.appData\s*=\s*(\{.*?\})\s*;", js_text, re.S)
                if not m: continue
                download_result = json_repair.loads(m.group(1))
                # ----parse from quark links
                if self.quark_parser_config.get('cookies'): song_info = self._parsesearchresultfromquark(search_result, download_result, soup, request_overrides)
                # ----parse from play url
                if not song_info.with_valid_download_url: song_info = self._parsesearchresultfromweb(search_result, download_result, soup, request_overrides)
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