'''
Function:
    Implementation of TwoT58MusicClient: https://www.2t58.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
import requests
from typing import Unpack
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from urllib.parse import urljoin, urlparse, quote
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import legalizestring, usesearchheaderscookies, extractdurationsecondsfromlrc, cleanlrc, SongInfo, RandomIPGenerator, AudioLinkTester, SongInfoUtils


'''TwoT58MusicClient'''
class TwoT58MusicClient(BaseMusicClient):
    source = 'TwoT58MusicClient'
    MUSIC_QUALITIES = ['flac', 'wav', '320']
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(TwoT58MusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Connection": "keep-alive",}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers; self.maintain_session = True
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        self.search_size_per_page = min(self.search_size_per_source, 68)
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            if int(count // page_size) + 1 == 1: search_urls.append(f'https://www.2t58.com/so/{quote(keyword)}.html')
            else: search_urls.append(f'https://www.2t58.com/so/{quote(keyword)}/{int(count // page_size) + 1}.html')
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        search_results, base_url = [], 'https://www.2t58.com/'
        for a in BeautifulSoup(html_text, "lxml").select(".play_list ul li .name a"):
            title, href = a.get_text(strip=True), a.get("href", ""); song_id = urlparse(urljoin(base_url, href)).path.strip('/').split('/')[-1].split('.')[0]
            search_results.append({"title": title, "url": urljoin(base_url, href) if base_url else href, "path": href, "id": song_id})
        return search_results[:self.search_size_per_page]
    '''_isverifypage'''
    def _isverifypage(self, html_text: str) -> bool:
        return ("安全人机验证" in html_text and 'name="csrf_token"' in html_text and 'name="human_check"' in html_text)
    '''_extractcsrftoken'''
    def _extractcsrftoken(self, html_text: str) -> str:
        m = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html_text)
        return m.group(1)
    '''_passhumanverify'''
    def _passhumanverify(self, verify_resp: requests.Response, request_overrides: dict = None):
        csrf_token, post_url = self._extractcsrftoken(verify_resp.text), verify_resp.url
        origin = f"{(parsed := urlparse(post_url)).scheme}://{parsed.netloc}"
        headers = {"Referer": verify_resp.url, "Origin": origin, "Content-Type": "application/x-www-form-urlencoded"}
        data = {"csrf_token": csrf_token, "human_check": "on"}
        (resp := self.post(post_url, headers=headers, data=data, allow_redirects=True, timeout=15, **(request_overrides or {}))).raise_for_status()
        resp.encoding = resp.apparent_encoding
        return resp
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        with suppress(Exception): page_no, search_result_idx = 1, -1; page_no = int(re.search(r"/(\d+)\.html/?$", urlparse(search_url).path).group(1))
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, allow_redirects=True, **(request_overrides := request_overrides or {}))).raise_for_status(); resp.encoding = resp.apparent_encoding
            if self._isverifypage(resp.text): resp = self._passhumanverify(resp, request_overrides=request_overrides); (resp := self.get(search_url, allow_redirects=True, **(request_overrides := request_overrides or {}))).raise_for_status(); resp.encoding = resp.apparent_encoding
            for search_result_idx, search_result in enumerate(self._parsesearchresultsfromhtml(resp.text)):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if not isinstance(search_result, dict) or (not search_result.get('url')) or (not search_result.get('id')): continue
                headers, song_info, song_id = copy.deepcopy(self.default_download_headers), SongInfo(source=self.source), search_result['id']
                for music_quality in TwoT58MusicClient.MUSIC_QUALITIES:
                    download_url = f"https://www.2t58.com/plug/down.php?ac=music&id={song_id}&k={music_quality}"; RandomIPGenerator().addrandomipv4toheaders(headers=headers)
                    with suppress(Exception): download_url = self.session.head(download_url, allow_redirects=True, headers=headers).url
                    download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get("title")), singers='NULL', album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                        file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric='NULL', cover_url=None, download_url=download_url_status['download_url'], download_url_status=download_url_status,
                    )
                    if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                # --lyric results
                with suppress(Exception): (resp := self.get(f"https://www.2t58.com/plug/down.php?ac=music&lk=lrc&id={song_id}", **request_overrides)).raise_for_status(); song_info.lyric = cleanlrc(resp.text.replace('[00:00.00]欢迎来访爱听音乐网 www.2t58.com\r\n', '')); song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
                # --cover results
                with suppress(Exception): (resp := self.get(search_result['url'], **request_overrides)).raise_for_status(); soup = BeautifulSoup(resp.text); cover = soup.select_one("#mcover"); song_info.cover_url = cover["src"] if cover and cover.has_attr("src") else None
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