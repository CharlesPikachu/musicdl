'''
Function:
    Implementation of FiveSongMusicClient: https://www.5song.xyz/index.html
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
from bs4 import BeautifulSoup
from rich.progress import Progress
from ..sources import BaseMusicClient
from urllib.parse import urljoin, urlparse
from ..utils import legalizestring, usesearchheaderscookies, searchdictbykey, seconds2hms, extractdurationsecondsfromlrc, cleanlrc, SongInfo, QuarkParser, AudioLinkTester


'''FiveSongMusicClient'''
class FiveSongMusicClient(BaseMusicClient):
    source = 'FiveSongMusicClient'
    MUSIC_QUALITY_RANK = {"DSD": 0, "WAV": 1, "FLAC": 2, "APE": 3, "ALAC": 4, "AAC": 5, "MP3": 6, "OGG": 7, "M4A": 8}
    def __init__(self, **kwargs):
        super(FiveSongMusicClient, self).__init__(**kwargs)
        assert self.quark_parser_config.get('cookies'), f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so the songs cannot be downloaded.'
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        self.search_size_per_page = min(self.search_size_per_source, 10)
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            if int(count // page_size) + 1 == 1: search_urls.append(f'https://www.5song.xyz/search.html?keyword={keyword}')
            else: search_urls.append(f'https://www.5song.xyz/search.html?page={int(count // page_size) + 1}&keyword={keyword}')
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        soup, base_url, search_results = BeautifulSoup(html_text, "lxml"), "https://www.5song.xyz", []
        for li in soup.select("div.list ul > li"):
            if not (a := li.select_one("a[href]")): continue
            href = a.get("href", "").strip(); detail_url = urljoin(base_url, href)
            title_el = a.select_one("div.con div.t h3"); title = title_el.get_text(strip=True) if title_el else None
            formats = [s.get_text(strip=True) for s in a.select("div.con div.t span") if s.get_text(strip=True)]
            singer_el = a.select_one("div.singerNum div.singer"); date_el = a.select_one("div.singerNum div.date"); num_el = a.select_one("div.singerNum div.num")
            singer = singer_el.get_text(strip=True) if singer_el else None; date = date_el.get_text(strip=True) if date_el else None
            num = num_el.get_text(strip=True) if num_el else None; img = a.select_one("div.pic img")
            cover_url = urljoin(base_url, img.get("src")) if img and img.get("src") else None
            search_results.append({"title": title, "formats": formats, "singer": singer, "date": date, "num": num, "detail_url": detail_url, "cover_url": cover_url})
        return search_results
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, base_url = request_overrides or {}, "https://www.5song.xyz"
        guess_format_func = lambda label: (m.group(1) if (m := re.search(r"(DSD|WAV|FLAC|APE|ALAC|AAC|MP3|OGG|M4A)", str(label).upper())) else None)
        sort_by_audio_quality_func = lambda link_list: sorted(link_list, key=lambda x: (FiveSongMusicClient.MUSIC_QUALITY_RANK.get((fmt := guess_format_func(x.get("label", ""))), 999), fmt or ""))
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            search_results = self._parsesearchresultsfromhtml(resp.text)
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('detail_url' not in search_result): continue
                song_info, song_id = SongInfo(source=self.source), urlparse(str(search_result['detail_url'])).path.strip('/').split('/')[-1].split('.')[0]
                # ----fetch basic information
                try: (resp := self.get(search_result['detail_url'], **request_overrides)).raise_for_status()
                except Exception: continue
                soup, quark_links = BeautifulSoup(resp.text, "lxml"), []
                for li in soup.select("div.download ul li[data-url]"):
                    if not (quark_url := (li.get("data-url") or "").strip()): continue
                    a = li.select_one("a[href]"); label = a.get_text(" ", strip=True) if a else None
                    pc_download_href = a.get("href", "").strip() if a else None
                    pc_download_url = urljoin(base_url, pc_download_href) if pc_download_href else None
                    if "quark" in quark_url: quark_links.append({"label": label, "quark_url": quark_url, "pc_download_url": pc_download_url})
                if not quark_links: continue
                download_result = dict(quark_links=quark_links)
                # ----parse from quark links
                for quark_link in sort_by_audio_quality_func(download_result['quark_links']):
                    download_result['quark_parse_result'], download_url = QuarkParser.parsefromurl(quark_link['quark_url'], **self.quark_parser_config)
                    if not download_url or not str(download_url).startswith('http'): continue
                    duration = [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]
                    duration_in_secs = duration[0] if duration else 0
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('singer')), album='NULL', ext='mp3', file_size_bytes=None, file_size=None, 
                        identifier=song_id, duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric=cleanlrc("\n".join([p.get_text(strip=True) for p in soup.select_one("div.viewCon div.text").select("p") if p.get_text(strip=True)])), cover_url=search_result.get('cover_url'),
                        download_url=download_url, download_url_status=self.quark_audio_link_tester.test(download_url, request_overrides), default_download_headers=self.quark_default_download_headers,
                    )
                    song_info.download_url_status['probe_status'] = self.quark_audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']; song_info.ext = song_info.download_url_status['probe_status']['ext']
                    if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                    elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
                    if song_info.with_valid_download_url: break
                if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
                if not song_info.duration or song_info.duration == '-:-:-': song_info.duration = seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
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