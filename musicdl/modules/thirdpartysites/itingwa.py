'''
Function:
    Implementation of ITingWaMusicClient: https://www.itingwa.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
from typing import Unpack
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from urllib.parse import urljoin, parse_qs, urlparse, urlencode
from ..utils import legalizestring, usesearchheaderscookies, cleanlrc, SongInfo, AudioLinkTester


'''ITingWaMusicClient'''
class ITingWaMusicClient(BaseMusicClient):
    source = 'ITingWaMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(ITingWaMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7', 'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7', 'Host': 'www.itingwa.com', 'Sec-CH-UA': '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"', 'Sec-CH-UA-Mobile': '?0', 
            'Sec-CH-UA-Platform': '"Windows"', 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-User': '?1', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
        }
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", "Referer": "https://www.itingwa.com/", "Host": "mp3.itingwa.com"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'c': 'index', 'k': keyword, 't': '1', 'p': '1'}).update(rule)
        # construct search urls
        self.search_size_per_page = min(self.search_size_per_source, 10)
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'https://so.itingwa.com/?'
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['p'] = str(int(count // page_size) + 1)
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        base_url, soup, search_results = "https://www.itingwa.com/", BeautifulSoup(html_text, "lxml"), {}
        for row in soup.select('table.music_list tr'):
            if not (song_node := row.select_one('a[href*="/listen/"]')): continue
            cells, song_url = row.find_all('td', recursive=False), urljoin(base_url, song_node.get('href', ''))
            if not (m := re.compile(r'/listen/(\d+)(?:[/?#]|$)').search(song_url)): continue
            user_node = image_node.find_parent('a') if (image_node := row.select_one('img[data-src], img[src]')) else None
            image_url = (urljoin(base_url, image_node.get('data-src') or image_node.get('src'),) if image_node else None)
            search_results[m.group(1)] = {
                'song_id': m.group(1), 'name': song_node.get_text(' ', strip=True), 'author': (cells[1].get_text(' ', strip=True) if len(cells) > 1 else None),
                'url': song_url, 'avatar': image_url, 'uploader_url': (urljoin(base_url, user_node.get('href', '')) if user_node else None),
            }
        return list(search_results.values())
    '''_extractsonginfo'''
    def _extractsonginfo(self, html_text: str):
        cover = intro.select_one('img') if (intro := (soup := BeautifulSoup(html_text, 'lxml')).select_one('.music_intro')) else None
        player, singer, title = soup.select_one('#tw_player'), soup.select_one('#music_singer'), soup.select_one('.frame1 > h1')
        return {
            'name': next(title.stripped_strings, None) if title else None, 'singer': singer.get_text(strip=True) if singer else None, 'cover': urljoin("https://www.itingwa.com/", cover.get('src', '')) if cover else None, 
            'lyrics': intro.get_text('\n', strip=True) if intro else None, 'play_url': urljoin("https://mp3.itingwa.com/", player.get('init-data', '')) if player else None,
        }
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, page_no, search_result_idx = request_overrides or {}, int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('p')[0])), -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, headers={"Referer": "https://so.itingwa.com/", "Host": "so.itingwa.com"}, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(self._parsesearchresultsfromhtml(resp.text)):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if not isinstance(search_result, dict) or (not search_result.get('url')) or (not search_result.get('song_id')): continue
                song_info, song_id = SongInfo(source=self.source), search_result.get('song_id')
                with suppress(Exception): resp = None; (resp := self.get(search_result['url'], **request_overrides)).raise_for_status()
                if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                if not (download_url := (download_result := self._extractsonginfo(resp.text)).get('play_url')) or not str(download_url).startswith('http'): continue
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name') or download_result.get('name')), singers=legalizestring(search_result.get('author') or download_result.get('singer')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                    file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric=cleanlrc(download_result.get('lyrics') or 'NULL'), cover_url=download_result.get('cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers
                )
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
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