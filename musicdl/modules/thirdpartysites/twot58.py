'''
Function:
    Implementation of TwoT58MusicClient: https://www.2t58.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from ..sources import BaseMusicClient
from urllib.parse import urljoin, urlparse
from ..utils import legalizestring, usesearchheaderscookies, extractdurationsecondsfromlrc, cleanlrc, SongInfo, RandomIPGenerator, AudioLinkTester, SongInfoUtils


'''TwoT58MusicClient'''
class TwoT58MusicClient(BaseMusicClient):
    source = 'TwoT58MusicClient'
    MUSIC_QUALITIES = ['flac', 'wav', '320']
    def __init__(self, **kwargs):
        super(TwoT58MusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "document", "sec-fetch-mode": "navigate", "sec-fetch-user": "?1", 
            "cookie": "Hm_tf_hx9umupwu8o=1766942296; Hm_lvt_b8f2e33447143b75e7e4463e224d6b7f=1766942296; cac9054cc9568db7fa51d16ee602cd7b=fd6762f9a63b502fda3befef86ea6460; server_name_session=91a76d925399962c481089ef4a83ce4e; Hm_lvt_hx9umupwu8o=1766942296,1768900847; Hm_lpvt_hx9umupwu8o=1768901202", "referer": "https://www.2t58.com/so/%E5%8F%AF%E6%83%9C.html", "priority": "u=0, i", 
            "sec-ch-ua": "\"Not(A:Brand\";v=\"8\", \"Chromium\";v=\"144\", \"Google Chrome\";v=\"144\"", "sec-ch-ua-mobile": "?0", "upgrade-insecure-requests": "1", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36", "sec-fetch-site": "same-origin", 
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        self.search_size_per_page = min(self.search_size_per_source, 68)
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            if int(count // page_size) + 1 == 1: search_urls.append(f'https://www.2t58.com/so/{keyword}.html')
            else: search_urls.append(f'https://www.2t58.com/so/{keyword}/{int(count // page_size) + 1}.html')
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
                if not isinstance(search_result, dict) or ('url' not in search_result) or ('id' not in search_result): continue
                headers, song_info, song_id = copy.deepcopy(self.default_download_headers), SongInfo(source=self.source), search_result['id']
                for quality in TwoT58MusicClient.MUSIC_QUALITIES:
                    download_url = f"https://www.2t58.com/plug/down.php?ac=music&id={song_id}&k={quality}"; RandomIPGenerator().addrandomipv4toheaders(headers=headers)
                    with suppress(Exception): download_url = self.session.head(download_url, allow_redirects=True, headers=headers).url
                    download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(str(search_result.get("title")).split('-', 2)[0]), singers=legalizestring(str(search_result.get("title")).split('-', 2)[-1]), album='NULL', ext=download_url_status['ext'], 
                        file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric='NULL', cover_url=None, download_url=download_url_status['download_url'], download_url_status=download_url_status,
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
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Error: {err})")
            self.logger_handle.error(f"{self.source}._search >>> {search_url} (Error: {err})", disable_print=self.disable_print)
        # return
        return song_infos