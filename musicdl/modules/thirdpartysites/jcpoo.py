'''
Function:
    Implementation of JCPOOMusicClient: https://www.jcpoo.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import ast
import copy
import json_repair
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from ..sources import BaseMusicClient
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from ..utils import legalizestring, usesearchheaderscookies, searchdictbykey, extractdurationsecondsfromlrc, cleanlrc, SongInfo, QuarkParser, AudioLinkTester, SongInfoUtils


'''JCPOOMusicClient'''
class JCPOOMusicClient(BaseMusicClient):
    source = 'JCPOOMusicClient'
    MUSIC_QUALITY_RANK = {"DSD": 100, "DSF": 100, "DFF": 100, "WAV": 95, "AIFF": 95, "FLAC": 90, "ALAC": 90, "APE": 88, "WV": 88, "OPUS": 70, "AAC": 65, "M4A": 65, "OGG": 60, "VORBIS": 60, "MP3": 50, "WMA": 45}
    def __init__(self, **kwargs):
        super(JCPOOMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'page': 0, 'keyword': keyword}).update(rule)
        # construct search urls
        base_url, self.search_size_per_page = 'https://www.jcpoo.cn/search?', min(self.search_size_per_source, 30)
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['page'] = int(count // page_size)
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        soup, search_results, base_url = BeautifulSoup(html_text, "lxml"), [], "https://www.jcpoo.cn/"
        for li in soup.select("ul.tuij_song li.song_item2"):
            if not (a := li.select_one("a[href]")): continue
            full_url = urljoin(base_url, (href := a["href"].strip()))
            title = title_div.get_text(strip=True) if (title_div := a.select_one(".song_info2 > div")) else a.get_text(" ", strip=True)
            q = parse_qs(urlparse(href).query); mid = q.get("id", [None])[0]; m = re.compile(r'^(.*?)《(.*?)》$').match(title.strip())
            singer, song_name = (m.group(1).strip(), m.group(2).strip()) if m else (None, title.strip())
            search_results.append({"title": song_name, "artist": singer, "url": full_url, "id": mid.removeprefix('MUSIC_')})
        return search_results[:self.search_size_per_page]
    '''_extractquarklinksfromhtml'''
    def _extractquarklinksfromhtml(self, html_text: str):
        PAT = re.compile(
            r"""(?:const|let|var)\s+
                (?P<key>[A-Za-z0-9_]+?)\s*=\s*
                (?P<quote>["'])
                (?P<url>https?://pan\.quark\.cn/s/[^"']+)
                (?P=quote)
            """, re.VERBOSE
        )
        extract_quark_links_from_text_func = lambda text: [{"key": key, "format": fmt, "url": url} for m in PAT.finditer(text) if (url := m.group("url").strip()) and (key := m.group("key")) and ((base := (key[:-4] if key.endswith("_url") else key)) or True) and (((fmt := (([k for k in JCPOOMusicClient.MUSIC_QUALITY_RANK.keys() if k.lower() in base.lower()] or [base])[-1])) or True))]
        soup, outs, seen, uniq = BeautifulSoup(html_text, "lxml"), [], set(), []
        for s in soup.find_all("script"): "pan.quark.cn/s/" in (js := s.string or s.get_text() or "") and outs.extend(extract_quark_links_from_text_func(js))
        for it in outs: (url := it["url"]) not in seen and (seen.add(url) or uniq.append(it))
        uniq = sorted(uniq, key=lambda x: JCPOOMusicClient.MUSIC_QUALITY_RANK.get(str(x["format"]).upper(), 0), reverse=True)
        return {'quark_links': uniq, 'cover_url': (bytes(m.group(1), "utf-8").decode("unicode_escape").replace(r"\/", "/") if (m := re.search(r'"music_cover"\s*:\s*"(.*?)"', html_text)) else None)}
    '''_extractlrc'''
    def _extractlrc(self, js_text: str):
        # functions
        norm_func = lambda s: re.sub(r"\s+", "", str(s))
        pick_func = lambda d, target: next((v for k, v in d.items() if norm_func(k) == target), None)
        fmt_lrc_time_func = lambda sec: (f"[{int((t := float(norm_func(sec)))) // 60:02d}:{(t - (int(t // 60) * 60)):05.2f}]")
        lrc_list_to_lrc_func = lambda detail: (("\n".join([f"[ti:{detail.get('music_name','')}]", f"[ar:{detail.get('music_artist','')}]", f"[al:{detail.get('music_album','')}]",]).strip() + "\n") + "\n".join(f"{ts}{ly}" for ts, ly in sorted([(fmt_lrc_time_func(t), re.sub(r"\s+", " ", str(lyric)).strip()) for it in (detail.get("music_lrclist", []) or []) for t in [pick_func(it, "time")] for lyric in [pick_func(it, "lineLyric")] if t is not None and lyric is not None], key=lambda x: x[0],)))
        # match
        if not (s := re.search(r"const\s+detailJson\s*=\s*'(.+?)';\s*const\s+detail\s*=\s*JSON\.parse", js_text, re.S)): return {}, 'NULL'
        string = s.group(1).replace("\r", "").replace("\n", ""); lyric_result = json_repair.loads(ast.literal_eval(f'"{string}"')); lyric = cleanlrc(lrc_list_to_lrc_func(lyric_result))
        # return
        return lyric_result, lyric
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result.get('id')
        # parse download url
        (resp := self.get(search_result['url'], **request_overrides)).raise_for_status()
        with suppress(Exception): lyric_result, lyric = self._extractlrc(resp.text)
        if not locals().get('lyric_result') or not locals().get('lyric'): lyric_result, lyric = {}, 'NULL'
        for quark_info in (download_result := self._extractquarklinksfromhtml(resp.text))['quark_links']:
            download_result['quark_parse_result'], download_url = QuarkParser.parsefromurl(quark_info['url'], **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]) else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': lyric_result}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('artist')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=download_result.get('cover_url'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers,
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
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result.get('id')
        # parse download url
        (resp := self.get(search_result['url'], **request_overrides)).raise_for_status()
        with suppress(Exception): lyric_result, lyric = self._extractlrc(resp.text)
        if not locals().get('lyric_result') or not locals().get('lyric'): lyric_result, lyric = {}, 'NULL'
        download_result: dict = self._extractquarklinksfromhtml(resp.text)
        (resp := self.get(f"https://www.jcpoo.cn/audio/play?id={song_id}", **request_overrides)).raise_for_status()
        if not (download_url := resp.text.strip()) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': lyric_result}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('artist')),
            album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric=lyric, 
            cover_url=download_result.get('cover_url'), download_url=download_url_status['download_url'], download_url_status=download_url_status,
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
            for search_result in self._parsesearchresultsfromhtml(resp.text):
                # --download results
                if not isinstance(search_result, dict) or ('url' not in search_result): continue
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