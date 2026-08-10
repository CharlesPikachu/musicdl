'''
Function:
    Implementation of XMFWAVMusicClient: https://www.xmfwav.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import html
import warnings
from typing import Unpack
from contextlib import suppress
from rich.progress import Progress
from urllib.parse import quote, urljoin, urlparse, parse_qs
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import legalizestring, usesearchheaderscookies, extractdurationsecondsfromlrc, searchdictbykey, cleanlrc, SongInfo, AudioLinkTester, SongInfoUtils, QuarkParser
warnings.filterwarnings('ignore')


'''XMFWAVMusicClient'''
class XMFWAVMusicClient(BaseMusicClient):
    source = 'XMFWAVMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(XMFWAVMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36", "Referer": "https://www.xmfwav.com/"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36", "Referer": "https://www.xmfwav.com/"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        self.search_size_per_page = min(self.search_size_per_source, 15)
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            search_urls.append(f'https://www.xmfwav.com/allsrc/{quote(keyword)}?kwd={quote(keyword)}&page={int(count // page_size) + 1}')
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, request_overrides: dict = None):
        # init
        strip_html_func = lambda x: html.unescape(re.sub(r'<[^>]+>', '', x or '')).strip()
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result.get("id")
        # parse download url
        (resp := self.get(f'https://www.xmfwav.com/song/{song_id}', verify=False, **request_overrides)).raise_for_status(); detail_html = resp.text
        download_result = {key: html.unescape(m.group(2)).strip() for key in ['title', 'author', 'url', 'pic'] if (m := re.search(rf'\b{key}\s*:\s*([\'"])(.*?)\1', detail_html, flags=re.I | re.S))}
        download_pages = [urljoin('https://www.xmfwav.com/', u) for u in re.findall(r'href=[\'"]([^\'"]*/msdl/[^\'"]+)[\'"]', detail_html, flags=re.I)]
        download_result['quark_links'] = [m.group(0) for u in download_pages if (m := re.search(r'https?://pan\.quark\.cn/s/[A-Za-z0-9_-]+(?:\?[^"\'<>\s]*)?', html.unescape(self.get(u, verify=False, **request_overrides).text).replace('\\/', '/'), flags=re.I))]
        for quark_download_url in download_result['quark_links']:
            download_result['quark_parse_result'], download_url = QuarkParser.parsefromurl(quark_download_url, **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]) else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or download_result.get('title')), singers=legalizestring(search_result.get('singer') or download_result.get('author')), album=legalizestring(search_result.get('album') or download_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric='NULL', cover_url=urljoin('https://www.xmfwav.com/', download_result.get('pic') or ''), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # parse lyric result
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if (matched := re.search(r'<section[^>]*id=[\'"]demo[\'"][^>]*>.*?<article[^>]*>(.*?)</article>', detail_html, flags=re.IGNORECASE | re.DOTALL)): song_info.lyric = cleanlrc(strip_html_func(re.sub(r'<br\s*/?>', '\n', matched.group(1), flags=re.IGNORECASE)) or 'NULL')
        if not song_info.duration or song_info.duration == '-:-:-' or song_info.duration == '00:00:00': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, request_overrides: dict = None):
        # init
        strip_html_func = lambda x: html.unescape(re.sub(r'<[^>]+>', '', x or '')).strip()
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result.get('id')
        # parse download url
        (resp := self.get(f'https://www.xmfwav.com/song/{song_id}', verify=False, **request_overrides)).raise_for_status(); detail_html = resp.text
        download_result = {key: html.unescape(m.group(2)).strip() for key in ['title', 'author', 'url', 'pic'] if (m := re.search(rf'\b{key}\s*:\s*([\'"])(.*?)\1', detail_html, flags=re.I | re.S))}
        if not (download_url := download_result.get('url')) or not download_url.startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or download_result.get('title')), singers=legalizestring(search_result.get('singer') or download_result.get('author')), album=legalizestring(search_result.get('album') or download_result.get('album')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric='NULL', cover_url=urljoin('https://www.xmfwav.com/', download_result.get('pic') or ''), download_url=download_url_status['download_url'], download_url_status=download_url_status
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if (matched := re.search(r'<section[^>]*id=[\'"]demo[\'"][^>]*>.*?<article[^>]*>(.*?)</article>', detail_html, flags=re.IGNORECASE | re.DOTALL)): song_info.lyric = cleanlrc(strip_html_func(re.sub(r'<br\s*/?>', '\n', matched.group(1), flags=re.IGNORECASE)) or 'NULL')
        if not song_info.duration or song_info.duration == '-:-:-' or song_info.duration == '00:00:00': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, page_no, search_result_idx = request_overrides or {}, int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('page')[0])), -1
        strip_html_func = lambda x: legalizestring(html.unescape(re.sub(r'<[^>]+>', '', x or '')).strip())
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, verify=False, **request_overrides)).raise_for_status()
            for search_result_idx, search_result_html in enumerate(re.findall(r'<a\b[^>]*class=[\'"][^\'"]*\bsrcsong-item\b[^\'"]*[\'"][^>]*>.*?</a>', resp.text, flags=re.IGNORECASE | re.DOTALL)):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if not (id_matched := re.search(r'href=[\'"]/song/(\d+)(?:\.html)?[\'"]', search_result_html, flags=re.IGNORECASE)): continue
                if not (info_matched := re.search(r'<span[^>]*class=[\'"]srcsong-name[\'"][^>]*>(.*?)</span>\s*-\s*<span[^>]*class=[\'"]srcsinger-name[\'"][^>]*>(.*?)</span>\s*</div>', search_result_html, flags=re.IGNORECASE | re.DOTALL)): continue
                search_result = {'id': id_matched.group(1), 'title': strip_html_func(info_matched.group(1)), 'singer': strip_html_func(info_matched.group(2))}
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