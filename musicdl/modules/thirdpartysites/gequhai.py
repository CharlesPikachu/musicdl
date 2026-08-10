'''
Function:
    Implementation of GequhaiMusicClient: https://www.gequhai.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import html
import urllib
import base64
import json_repair
import urllib.parse
from typing import Unpack
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from urllib.parse import urljoin, urlparse, parse_qs, quote
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict, extractdurationsecondsfromlrc, searchdictbykey, cleanlrc, SongInfo, QuarkParser, AudioLinkTester, SongInfoUtils


'''GequhaiMusicClient'''
class GequhaiMusicClient(BaseMusicClient):
    source = 'GequhaiMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(GequhaiMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers; self.maintain_session = True
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        self.search_size_per_page = min(self.search_size_per_source, 12)
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            if int(count // page_size) + 1 == 1: search_urls.append(f'https://www.gequhai.com/s/{quote(keyword)}')
            else: search_urls.append(f'https://www.gequhai.com/s/{quote(keyword)}?page={int(count // page_size) + 1}')
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        soup, base_url, search_results = BeautifulSoup(html_text, "html.parser"), "https://www.gequhai.com", []
        if not (table := soup.select_one("table#myTables")): return []
        for tr in table.select("tbody tr"):
            if len((tds := tr.find_all("td"))) < 3: continue
            idx_text = tds[0].get_text(strip=True); a = tds[1].find("a"); title = a.get_text(strip=True) if a else tds[1].get_text(strip=True)
            href: str = a.get("href", "") if a else ""; play_url = urljoin(base_url, href) if href else ""
            singer = tds[2].get_text(strip=True); play_id = m.group(1) if (m := re.search(r"/play/(\d+)", href or "")) else None
            search_results.append({"index": int(idx_text) if idx_text.isdigit() else idx_text, "title": title, "singer": singer, "href": href, "play_url": play_url, "play_id": play_id})
        return search_results
    '''_extractappdataandwindowvars'''
    def _extractappdataandwindowvars(self, js_text: str) -> dict:
        decode_quark_url_func = lambda quark_url: base64.b64decode(str(quark_url).replace("#", "H").replace("%", "S")).decode("utf-8", errors="strict")
        normalize_texts_func = lambda text: [text, html.unescape(text), urllib.parse.unquote(html.unescape(text))]
        out, m = {}, re.search(r"window\.appData\s*=\s*(\{.*?\})\s*;", js_text, flags=re.S)
        if m: app = json_repair.loads(m.group(1)); out["appData"] = app; out.update(app)
        for k, v in re.findall(r"window\.(\w+)\s*=\s*'([^']*)'\s*;", js_text): out[k] = v
        for k, v in re.findall(r'window\.(\w+)\s*=\s*"([^"]*)"\s*;', js_text): out[k] = v
        seen = set(out); out.update({k: int(v) if re.fullmatch(r"-?\d+", v) else float(v) for k, v in re.findall(r"window\.(\w+)\s*=\s*(-?\d+(?:\.\d+)?)\s*;", js_text) if not (k in seen or seen.add(k))})
        seen = set(out); out.update({k: {"true": True, "false": False, "null": None}[str(v).lower()] for k, v in re.findall(r"window\.(\w+)\s*=\s*(true|false|null)\s*;", js_text, flags=re.I) if not (k in seen or seen.add(k))})
        if "mp3_title" in out and "mp3_author" in out: out.setdefault("mp3_name", f"{out['mp3_title']}-{out['mp3_author']}")
        if "mp3_extra_url" in out: out["mp3_extra_url_decoded"] = decode_quark_url_func(out["mp3_extra_url"])
        if out.get("mp3_extra_url_decoded") and "pan.quark.cn" in out["mp3_extra_url_decoded"]: return out
        if url := next((url for text in normalize_texts_func(js_text) for url in re.findall(r"https?://pan\.quark\.cn/s/[A-Za-z0-9_-]+", text) if url), None): out["mp3_extra_url_decoded"] = url
        return out
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, download_result: dict, soup: BeautifulSoup, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), download_result.get('mp3_id') or urlparse(str(search_result['play_url'])).path.strip('/').split('/')[-1]
        # parse download url
        if not (quark_download_url := download_result.get('mp3_extra_url_decoded')) or not str(quark_download_url).startswith('http'): return song_info
        download_result['quark_parse_result'], download_url = QuarkParser.parsefromdirurl(quark_download_url, **self.quark_parser_config)
        if not download_url: download_result['quark_parse_result'], download_url = QuarkParser.parsefromurl(quark_download_url, **self.quark_parser_config)
        download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]) else 0
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('mp3_title')), singers=legalizestring(download_result.get('mp3_author')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, 
            duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(soup.find("div", id="content-lrc2").get_text("\n", strip=True)), cover_url=download_result.get('mp3_cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers,
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if not song_info.duration or song_info.duration == '-:-:-' or song_info.duration == '00:00:00': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, download_result: dict, soup: BeautifulSoup, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), download_result.get("play_id")
        # parse download url
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "X-Requested-With": "Http",
            "Origin": "https://www.gequhai.com", "Sec-Ch-Ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"", "Sec-Ch-Ua-Mobile": "?0", "Sec-Ch-Ua-Platform": "\"Windows\"", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin", "X-Custom-Header": "Key", 
        }
        (resp := self.post('https://www.gequhai.com/api/music', data={'id': song_id, 'type': '0'}, headers=headers, **request_overrides)).raise_for_status()
        download_result['api/music'] = resp2json(resp=resp); download_url = safeextractfromdict(download_result['api/music'], ['data', 'url'], '')
        if not download_url or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('mp3_title', None)), singers=legalizestring(download_result.get('mp3_author')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
            identifier=download_result.get('mp3_id') or urlparse(str(search_result['play_url'])).path.strip('/').split('/')[-1], duration_s=None, duration='-:-:-', lyric=cleanlrc(soup.find("div", id="content-lrc2").get_text("\n", strip=True)), cover_url=download_result.get('mp3_cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if not song_info.duration or song_info.duration == '-:-:-' or song_info.duration == '00:00:00': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        with suppress(Exception): page_no, search_result_idx = 1, -1; page_no = int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('page')[0]))
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **(request_overrides := request_overrides or {}))).raise_for_status()
            for search_result_idx, search_result in enumerate(self._parsesearchresultsfromhtml(resp.text)):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if not isinstance(search_result, dict) or not search_result.get('play_url'): continue
                # ----obtain basic information
                with suppress(Exception): resp = None; (resp := self.get(search_result['play_url'], **request_overrides)).raise_for_status(); download_result = self._extractappdataandwindowvars(resp.text)
                if not locals().get('resp') or not locals().get('download_result') or not hasattr(locals().get('resp'), 'text'): continue
                # ----parse from quark links
                with suppress(Exception): song_info = self._parsesearchresultfromquark(search_result, download_result, BeautifulSoup(resp.text, 'lxml'), request_overrides) if self.quark_parser_config.get('cookies') else SongInfo(source=self.source)
                # ----parse from play url
                with suppress(Exception): song_info = self._parsesearchresultfromweb(search_result, download_result, BeautifulSoup(resp.text, 'lxml'), request_overrides) if not song_info.with_valid_download_url else song_info
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