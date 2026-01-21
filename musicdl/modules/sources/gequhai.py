'''
Function:
    Implementation of GequhaiMusicClient: https://www.gequhai.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import base64
import json_repair
from bs4 import BeautifulSoup
from .base import BaseMusicClient
from rich.progress import Progress
from urllib.parse import urljoin, urlparse
from ..utils import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict, extractdurationsecondsfromlrc, seconds2hms, searchdictbykey, cleanlrc, SongInfo, QuarkParser


'''GequhaiMusicClient'''
class GequhaiMusicClient(BaseMusicClient):
    source = 'GequhaiMusicClient'
    def __init__(self, **kwargs):
        super(GequhaiMusicClient, self).__init__(**kwargs)
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
        self.search_size_per_page = min(self.search_size_per_source, 12)
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            if int(count // page_size) + 1 == 1: search_urls.append(f'https://www.gequhai.com/s/{keyword}')
            else: search_urls.append(f'https://www.gequhai.com/s/{keyword}?page={int(count // page_size) + 1}')
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        soup, base_url = BeautifulSoup(html_text, "html.parser"), "https://www.gequhai.com"
        table = soup.select_one("table#myTables")
        if not table: return []
        results = []
        for tr in table.select("tbody tr"):
            tds = tr.find_all("td")
            if len(tds) < 3: continue
            idx_text = tds[0].get_text(strip=True)
            a = tds[1].find("a")
            title = a.get_text(strip=True) if a else tds[1].get_text(strip=True)
            href: str = a.get("href", "") if a else ""
            play_url = urljoin(base_url, href) if href else ""
            singer = tds[2].get_text(strip=True)
            m = re.search(r"/play/(\d+)", href or "")
            play_id = m.group(1) if m else None
            results.append({"index": int(idx_text) if idx_text.isdigit() else idx_text, "title": title, "singer": singer, "href": href, "play_url": play_url, "play_id": play_id})
        return results
    '''_decodequarkurl'''
    def _decodequarkurl(self, quark_url: str):
        b64 = quark_url.replace("#", "H")
        return base64.b64decode(b64).decode("utf-8", errors="strict")
    '''_extractappdataandwindowvars'''
    def _extractappdataandwindowvars(self, js_text: str) -> dict:
        out = {}
        m = re.search(r"window\.appData\s*=\s*(\{.*?\})\s*;", js_text, flags=re.S)
        if m: app = json_repair.loads(m.group(1)); out["appData"] = app; out.update(app)
        for k, v in re.findall(r"window\.(\w+)\s*=\s*'([^']*)'\s*;", js_text): out[k] = v
        for k, v in re.findall(r'window\.(\w+)\s*=\s*"([^"]*)"\s*;', js_text): out[k] = v
        for k, v in re.findall(r"window\.(\w+)\s*=\s*(-?\d+(?:\.\d+)?)\s*;", js_text):
            if k in out: continue
            out[k] = int(v) if re.fullmatch(r"-?\d+", v) else float(v)
        for k, v in re.findall(r"window\.(\w+)\s*=\s*(true|false|null)\s*;", js_text, flags=re.I):
            if k in out: continue
            vv = str(v).lower()
            out[k] = {"true": True, "false": False, "null": None}[vv]
        if "mp3_title" in out and "mp3_author" in out: out.setdefault("mp3_name", f"{out['mp3_title']}-{out['mp3_author']}")
        if "mp3_extra_url" in out: out["mp3_extra_url_decoded"] = self._decodequarkurl(out["mp3_extra_url"])
        return out
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, download_result: dict, soup: BeautifulSoup, request_overrides: dict = None):
        # init
        request_overrides, song_info = request_overrides or {}, SongInfo(source=self.source)
        # parse
        quark_download_url = download_result.get('mp3_extra_url_decoded', '')
        if not quark_download_url or not str(quark_download_url).startswith('http'): return song_info
        download_result['quark_parse_result'], download_url = QuarkParser.parsefromdirurl(quark_download_url, **self.quark_parser_config)
        duration = [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]
        duration_s = duration[0] if duration else 0
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['mp3_title'], None)), singers=legalizestring(safeextractfromdict(download_result, ['mp3_author'], None)), 
            album='NULL', ext='mp3', file_size='NULL', identifier=download_result.get('mp3_id') or urlparse(str(search_result['play_url'])).path.strip('/').split('/')[-1], duration_s=duration_s, duration=seconds2hms(duration_s), lyric=cleanlrc(soup.find("div", id="content-lrc2").get_text("\n", strip=True)), 
            cover_url=safeextractfromdict(download_result, ['mp3_cover'], None), download_url=download_url, download_url_status=self.quark_audio_link_tester.test(download_url, request_overrides), default_download_headers=self.quark_default_download_headers,
        )
        song_info.download_url_status['probe_status'] = self.quark_audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
        if not song_info.with_valid_download_url: return SongInfo(source=self.source)
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
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8", "origin": "https://www.gequhai.com", "priority": "u=1, i",
            "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"", "x-custom-header": "SecretKey", "x-requested-with": "XMLHttpRequest",
            "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        }
        resp = self.post('https://www.gequhai.com/api/music', data={'id': download_result['play_id'], 'type': '0'}, headers=headers, **request_overrides)
        resp.raise_for_status()
        download_result['api/music'] = resp2json(resp=resp)
        download_url = safeextractfromdict(download_result['api/music'], ['data', 'url'], '')
        if not download_url or not str(download_url).startswith('http'): return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['mp3_title'], None)), singers=legalizestring(safeextractfromdict(download_result, ['mp3_author'], None)), 
            album='NULL', ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=download_result.get('mp3_id') or urlparse(str(search_result['play_url'])).path.strip('/').split('/')[-1], duration=None, lyric=cleanlrc(soup.find("div", id="content-lrc2").get_text("\n", strip=True)), 
            cover_url=safeextractfromdict(download_result, ['mp3_cover'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides), 
        )
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
        if not song_info.with_valid_download_url: return SongInfo(source=self.source)
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
                if not isinstance(search_result, dict) or ('play_url' not in search_result): continue
                song_info = SongInfo(source=self.source)
                # ----fetch basic information
                try: resp = self.get(search_result['play_url'], **request_overrides); resp.raise_for_status(); download_result = self._extractappdataandwindowvars(resp.text)
                except: continue
                soup = BeautifulSoup(resp.text, 'lxml')
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