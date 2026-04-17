'''
Function:
    Implementation of FangpiMusicClient: https://www.fangpi.net/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import ast
import base64
import json_repair
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from ..sources import BaseMusicClient
from urllib.parse import urljoin, urlparse
from ..utils import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict, searchdictbykey, extractdurationsecondsfromlrc, cleanlrc, SongInfo, QuarkParser, AudioLinkTester, SongInfoUtils


'''FangpiMusicClient'''
class FangpiMusicClient(BaseMusicClient):
    source = 'FangpiMusicClient'
    def __init__(self, **kwargs):
        super(FangpiMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36", "referer": "https://www.fangpi.net/"}
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
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
    def _parsesearchresultsfromhtml(self, html, base_url="https://www.fangpi.net"):
        soup, search_results, seen = BeautifulSoup(html, "lxml"), [], set()
        if (result_card := next((card for card in soup.select("div.card") if "搜索结果" in card.get_text(" ", strip=True) and card.select_one("h1.mark")), None)) is None: return []
        for row in result_card.select("div.row"):
            if not (detail := row.select_one('a[href^="/music/"][title]')) or not row.select_one('a.btn[href^="/music/"]'): continue
            if (url := urljoin(base_url, detail["href"])) in seen: continue
            seen.add(url); search_results.append({"id": detail["href"].rsplit("/", 1)[-1], "name": (row.select_one("span.text-primary") or detail).get_text(strip=True), "artist": row.select_one("small.text-jade").get_text(strip=True), "title": detail.get("title", "").strip(), "url": url})
        return search_results
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, download_result: dict, soup: BeautifulSoup, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), download_result.get("mp3_id") or urlparse(str(search_result['url'])).path.strip('/').split('/')[-1]
        # parse download url
        for quark_download_url in (download_result.get('mp3_extra_urls', []) or []):
            download_result['quark_parse_result'], download_url = QuarkParser.parsefromurl(base64.b64decode(quark_download_url['share_link']).decode('utf-8'), **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]) else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('mp3_title')), singers=legalizestring(download_result.get('mp3_author')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, 
                duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(soup.find("div", id="content-lrc").get_text("\n", strip=True)), cover_url=download_result.get('mp3_cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers,
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # parse lyric result
        if not song_info.duration or song_info.duration == '-:-:-' or song_info.duration == '00:00:00':
            format_duration_func = lambda d: "{:02}:{:02}:{:02}".format(*([0] * (3 - len(d.split(":"))) + list(map(int, d.split(":")))))
            song_info.duration = format_duration_func(download_result.get('mp3_duration', '00:00:00') or '00:00:00')
            if song_info.duration == '00:00:00': song_info.duration = '-:-:-'
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if not song_info.duration or song_info.duration == '-:-:-' or song_info.duration == '00:00:00': song_info.duration = SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, download_result: dict, soup: BeautifulSoup, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), download_result.get("play_id")
        # parse download url
        (resp := self.post('https://www.fangpi.net/api/play-url', json={'id': song_id}, **request_overrides)).raise_for_status()
        download_result['api/play-url'] = resp2json(resp=resp); download_url = safeextractfromdict(download_result['api/play-url'], ['data', 'url'], '')
        if not download_url or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('mp3_title')), singers=legalizestring(download_result.get('mp3_author')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
            identifier=download_result.get('mp3_id') or urlparse(str(search_result['url'])).path.strip('/').split('/')[-1], duration_s=None, duration='-:-:-', lyric=cleanlrc(soup.find("div", id="content-lrc").get_text("\n", strip=True)), cover_url=download_result.get('mp3_cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        if not song_info.duration or song_info.duration == '-:-:-' or song_info.duration == '00:00:00':
            format_duration_func = lambda d: "{:02}:{:02}:{:02}".format(*([0] * (3 - len(d.split(":"))) + list(map(int, d.split(":")))))
            song_info.duration = format_duration_func(download_result.get('mp3_duration', '00:00:00') or '00:00:00')
            if song_info.duration == '00:00:00': song_info.duration = '-:-:-'
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
            for search_result in self._parsesearchresultsfromhtml(resp.text):
                # --download results
                if not isinstance(search_result, dict) or ('url' not in search_result): continue
                # ----obtain basic information
                with suppress(Exception): (resp := self.get(search_result['url'], **request_overrides)).raise_for_status()
                if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                if (script_tag := (soup := BeautifulSoup(resp.text, "lxml")).find("script", string=re.compile(r"window\.appData"))) is None: continue
                if not (m := re.search(r'JSON\.parse\(\s*(?P<lit>(["\'])(?:\\.|(?!\2).)*?\2)\s*\)', script_tag.string, re.S)): continue
                if (download_result := json_repair.loads(ast.literal_eval(m.group('lit')))).get("mp3_cover"): download_result["mp3_cover"] = str(download_result["mp3_cover"]).replace("\\/", "/")
                if download_result.get("extra_recommend_wap_url"): download_result["extra_recommend_wap_url"] = str(download_result["extra_recommend_wap_url"]).replace("\\/", "/")
                for share_link in (download_result.get("mp3_extra_urls", []) or []): isinstance(share_link, dict) and share_link.__setitem__('share_link', str(share_link.get('share_link', '')).replace("\\/", "/"))
                # ----parse from quark links
                with suppress(Exception): song_info = self._parsesearchresultfromquark(search_result, download_result, soup, request_overrides) if self.quark_parser_config.get('cookies') else SongInfo(source=self.source)
                # ----parse from play url
                with suppress(Exception): song_info = self._parsesearchresultfromweb(search_result, download_result, soup, request_overrides) if not song_info.with_valid_download_url else song_info
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