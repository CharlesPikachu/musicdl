'''
Function:
    Implementation of SgogoMusicClient: https://www.sgogo.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import html
import warnings
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from typing_extensions import Unpack
from urllib.parse import quote, urljoin
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import legalizestring, usesearchheaderscookies, searchdictbykey, cleanlrc, SongInfo, QuarkParser, AudioLinkTester, SongInfoUtils
warnings.filterwarnings('ignore')


'''SgogoMusicClient'''
class SgogoMusicClient(BaseMusicClient):
    source = 'SgogoMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(SgogoMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", "Referer": "https://www.sgogo.com/"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls based on search rules
        search_urls = [f'https://www.sgogo.com/src/{quote(keyword)}']
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        search_results, base_url = [], 'https://www.sgogo.com/'
        for item in BeautifulSoup(html_text, "lxml").select('.song-list a.srcsong-item[href]'):
            song, singer, match = item.select_one('.srcsong-name'), item.select_one('.srcsinger-name'), re.search(r'/song/(\d+)', str(item['href']))
            if not song or not singer or not match: continue
            search_results.append({'singer': singer.get_text(' ', strip=True).replace(' ', ''), 'song': song.get_text(' ', strip=True).replace(' ', ''), 'url': urljoin(base_url, item['href']), 'id': match.group(1)})
        return search_results
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id, base_url = request_overrides or {}, SongInfo(source=self.source), search_result.get("id"), "https://www.sgogo.com/"
        text_func = lambda selector: (lambda node: node.get_text("\n", strip=True).lstrip("\ufeff") if node else None)(soup.select_one(selector))
        # parse download url
        (resp := self.get(search_result['url'], verify=False, **request_overrides)).raise_for_status(); (soup := BeautifulSoup(resp.text, 'lxml'))
        player_script = next((script.string or script.get_text() for script in soup.find_all("script") if "new APlayer" in (script.string or script.get_text())), "")
        player_value_func = lambda name: (lambda match: html.unescape(match.group(2)).replace(r"\/", "/") if match else None)(re.search(rf"\b{re.escape(name)}\s*:\s*(['\"])(.*?)\1", player_script, re.S))
        heading = text_func(".dtl-title h1") or ""; fallback_title, separator, fallback_artist = heading.partition(" - ")
        title, artist = player_value_func("title") or fallback_title or None, player_value_func("author") or (fallback_artist if separator else None)
        download_url, cover_url, lyrics = urljoin(base_url, player_value_func("url")), urljoin(base_url, player_value_func("pic")), cleanlrc(text_func("#songlrc article"))
        download_result = {'title': title, 'artist': artist, 'download_url': download_url, 'cover_url': cover_url, 'lyrics': lyrics}
        for anchor in soup.select('a[href^="/msdl/"]'):
            (resp := self.get(urljoin("https://www.sgogo.com/", anchor["href"]), allow_redirects=True, **request_overrides)).raise_for_status()
            download_result['quark_link'] = re.search(r"https://pan\.quark\.cn/s/[A-Za-z0-9]+", resp.text).group()
            download_result['quark_parse_result'], download_url = QuarkParser.parsefromurl(download_result['quark_link'], **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]) else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('song') or download_result.get('title')), singers=legalizestring(search_result.get('singer') or download_result.get('artist')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=download_result.get('lyrics'), cover_url=None, download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id, base_url = request_overrides or {}, SongInfo(source=self.source), search_result.get("id"), "https://www.sgogo.com/"
        text_func = lambda selector: (lambda node: node.get_text("\n", strip=True).lstrip("\ufeff") if node else None)(soup.select_one(selector))
        # parse download url
        (resp := self.get(search_result['url'], verify=False, **request_overrides)).raise_for_status(); (soup := BeautifulSoup(resp.text, 'lxml'))
        player_script = next((script.string or script.get_text() for script in soup.find_all("script") if "new APlayer" in (script.string or script.get_text())), "")
        player_value_func = lambda name: (lambda match: html.unescape(match.group(2)).replace(r"\/", "/") if match else None)(re.search(rf"\b{re.escape(name)}\s*:\s*(['\"])(.*?)\1", player_script, re.S))
        heading = text_func(".dtl-title h1") or ""; fallback_title, separator, fallback_artist = heading.partition(" - ")
        title, artist = player_value_func("title") or fallback_title or None, player_value_func("author") or (fallback_artist if separator else None)
        download_url, cover_url, lyrics = urljoin(base_url, player_value_func("url")), urljoin(base_url, player_value_func("pic")), cleanlrc(text_func("#songlrc article"))
        download_result = {'title': title, 'artist': artist, 'download_url': download_url, 'cover_url': cover_url, 'lyrics': lyrics}
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('song') or download_result.get('title')), singers=legalizestring(search_result.get('singer') or download_result.get('artist')), album='NULL', ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric=download_result.get('lyrics'), cover_url=None, download_url=download_url_status['download_url'], download_url_status=download_url_status
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, page_no, search_result_idx = request_overrides or {}, 1, -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, verify=False, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(self._parsesearchresultsfromhtml(resp.text)):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if not isinstance(search_result, dict) or (not search_result.get('id')): continue
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