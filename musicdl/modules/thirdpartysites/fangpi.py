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
from typing_extensions import Unpack
from urllib.parse import urljoin, urlparse, quote
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import legalizestring, usesearchheaderscookies, resp2json, safeextractfromdict, searchdictbykey, extractdurationsecondsfromlrc, cleanlrc, SongInfo, QuarkParser, AudioLinkTester, SongInfoUtils


'''FangpiMusicClient'''
class FangpiMusicClient(BaseMusicClient):
    source = 'FangpiMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        kwargs['enable_search_curl_cffi'] = True
        super(FangpiMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "Upgrade-Insecure-Requests": "1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8", "Origin": "https://www.fangpi.net", "Referer": "https://www.fangpi.net/",
        }
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        search_urls = [f'https://www.fangpi.net/s/{quote(keyword)}']
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
    def _parsesearchresultfromquark(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result.get("mp3_id") or urlparse(str(search_result['url'])).path.strip('/').split('/')[-1]
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse download url
        for quark_download_url in (search_result.get('mp3_extra_urls', []) or []):
            if not str(quark_download_url := quark_download_url['share_link']).startswith('http') or 'pan.quark.cn' not in quark_download_url: continue
            download_result, download_url = QuarkParser.parsefromurl(quark_download_url, **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]) else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('mp3_title')), singers=legalizestring(search_result.get('mp3_author')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=search_result.get('lyric'), cover_url=search_result.get('mp3_cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers,
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # parse lyric result
        if song_info.duration in {'-:-:-', '00:00:00'}: song_info.duration_s = to_seconds_func(search_result.get('mp3_duration', '00:00:00') or '00:00:00'); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if song_info.duration in {'-:-:-', '00:00:00'}: song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, play_id = request_overrides or {}, SongInfo(source=self.source), search_result.get("play_id")
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse download url
        (resp := self.post('https://www.fangpi.net/member/common-play-url', json={'id': play_id}, **request_overrides)).raise_for_status()
        download_result = resp2json(resp=resp); download_url = safeextractfromdict(download_result, ['data', 'url'], '')
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('mp3_title')), singers=legalizestring(search_result.get('mp3_author')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
            identifier=search_result.get('mp3_id') or urlparse(str(search_result['url'])).path.strip('/').split('/')[-1], duration_s=None, duration='-:-:-', lyric=search_result.get('lyric'), cover_url=search_result.get('mp3_cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        song_info.duration_s = to_seconds_func(search_result.get('mp3_duration', '00:00:00') or '00:00:00')
        song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if song_info.duration in {'-:-:-', '00:00:00'}: song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_getsongmetainfo'''
    def _getsongmetainfo(self, search_result, request_overrides: dict = None):
        (resp := self.get(search_result['url'], **(request_overrides or {}))).raise_for_status()
        script_tag = (soup := BeautifulSoup(resp.text, "lxml")).find("script", string=re.compile(r"window\.appData"))
        m = re.search(r'JSON\.parse\(\s*(?P<lit>(["\'])(?:\\.|(?!\2).)*?\2)\s*\)', str(script_tag.string), re.S)
        meta_info: dict = json_repair.loads(ast.literal_eval(m.group('lit')))
        meta_info['mp3_cover'] = str(meta_info.get('mp3_cover', '') or '').replace("\\/", "/")
        extra_recommend_wap_url = str(meta_info.get('extra_recommend_wap_url', '') or '')
        meta_info['extra_recommend_wap_url'] = extra_recommend_wap_url.replace("\\/", "/") if extra_recommend_wap_url.startswith('http') else base64.b64decode(extra_recommend_wap_url).decode('utf-8')
        for share_link in (meta_info.get("mp3_extra_urls", []) or []): isinstance(share_link, dict) and share_link.__setitem__('share_link', sl.replace("\\/", "/") if (sl := str(share_link.get('share_link', ''))).startswith('http') else base64.b64decode(sl).decode('utf-8'))
        meta_info['lyric'] = cleanlrc(soup.find("div", id="content-lrc").get_text("\n", strip=True))
        return meta_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, page_no, search_result_idx = request_overrides or {}, 1, -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(self._parsesearchresultsfromhtml(resp.text)):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if not isinstance(search_result, dict) or not search_result.get('url'): continue
                with suppress(Exception): search_result.update(self._getsongmetainfo(search_result=search_result, request_overrides=request_overrides))
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