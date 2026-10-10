'''
Function:
    Implementation of LeedodoMusicClient: https://music.leedodo.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import json
import copy
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from typing_extensions import Unpack
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from urllib.parse import urljoin, parse_qs, urlparse, urlencode
from ..utils import legalizestring, usesearchheaderscookies, cleanlrc, SongInfo, AudioLinkTester


'''LeedodoMusicClient'''
class LeedodoMusicClient(BaseMusicClient):
    source = 'LeedodoMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(LeedodoMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7', 'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7', 'Host': 'music.leedodo.com', 'Sec-CH-UA': '"Chromium";v="154", "Google Chrome";v="154", "Not A(Brand";v="99"', 'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"Windows"', 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-User': '?1', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36',
        }
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36", "Referer": "https://music.leedodo.com/", "Host": "music.leedodo.com"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'s': keyword, 'post_type': 'post'}).update(rule)
        # construct search urls
        self.search_size_per_page = min(self.search_size_per_source, 10)
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'https://music.leedodo.com/?'
        while self.search_size_per_source > count:
            page_rule, page_no = copy.deepcopy(default_rule), int(count // page_size) + 1
            if page_no > 1: page_rule['paged'] = str(page_no)
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        base_url, soup, search_results = "https://music.leedodo.com/", BeautifulSoup(html_text, "lxml"), {}
        for row in soup.select('article.w-grid-item[data-id]'):
            if not (song_node := row.select_one('.post_title a[href*="/song/"]')): continue
            song_url = urljoin(base_url, song_node.get('href', ''))
            if not (m := re.compile(r'/song/(\d+)(?:[/?#]|$)').search(song_url)): continue
            search_results[m.group(1)] = {
                'song_id': m.group(1), 'name': song_node.get_text(' ', strip=True), 'author': user_node.get_text(' ', strip=True) if (user_node := row.select_one('.post_artist a')) else None,
                'url': song_url, 'avatar': None, 'uploader_url': urljoin(base_url, user_node.get('href', '')) if user_node else None,
            }
        return list(search_results.values())
    '''_extractsonginfo'''
    def _extractsonginfo(self, html_text: str):
        base_url, soup = "https://music.leedodo.com/", BeautifulSoup(html_text, 'lxml')
        title, page_node = soup.select_one('h1.post_title'), soup.select_one('meta[property="og:url"]')
        singer = next((node.select_one('a') for node in soup.select('.post_taxonomy') if '艺术家' in node.get_text(' ', strip=True) and node.select_one('a')), None)
        song_url: str = page_node.get('content', '') if page_node else ''
        song_id = m.group(1) if (m := re.compile(r'/song/(\d+)(?:[/?#]|$)').search(song_url)) else None
        return {
            'name': title.get_text(' ', strip=True) if title else None, 'singer': singer.get_text(' ', strip=True) if singer else None, 'cover': None,
            'lyrics': None, 'play_url': urljoin(base_url, f'/req/mp3/{song_id}/') if song_id else None,
        }
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, query_params, search_result_idx = request_overrides or {}, parse_qs(urlparse(url=search_url).query, keep_blank_values=True), -1
        page_no, keyword = int(float(query_params.get('paged', ['1'])[0])), query_params.get('s', [keyword])[0]
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            if page_no <= 1: (resp := self.get(search_url, headers={"Referer": "https://music.leedodo.com/", "Host": "music.leedodo.com"}, **request_overrides)).raise_for_status()
            else:
                template_vars = {'columns': '1', 'exclude_items': 'none', 'img_size': 'default', 'ignore_items_size': 0, 'items_layout': '12041', 'items_offset': '1', 'load_animation': 'none', 'overriding_link': 'none', 'post_id': 8031, 'query_args': {'s': keyword, 'post_type': 'post', 'post_status': ['publish'], 'tax_query': [], 'paged': page_no}, 'orderby_query_args': {'orderby': {'date': 'DESC'}}, 'type': 'masonry', 'us_grid_ajax_index': 1, 'us_grid_filter_params': None, 'us_grid_index': 1, '_us_grid_post_type': 'current_query',}
                data = {'action': 'us_ajax_grid', 'ajax_url': 'https://music.leedodo.com/wp-admin/admin-ajax.php', 'infinite_scroll': 'true', 'max_num_pages': '10', 'pagination': 'ajax', 'permalink_url': 'https://music.leedodo.com', 'template_vars': json.dumps(template_vars, ensure_ascii=False, separators=(',', ':')),}
                headers = {'Accept': '*/*', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Origin': 'https://music.leedodo.com', 'Referer': f'https://music.leedodo.com/?{urlencode({"s": keyword, "post_type": "post"})}', 'X-Requested-With': 'XMLHttpRequest', 'Host': 'music.leedodo.com'}
                (resp := self.post('https://music.leedodo.com/wp-admin/admin-ajax.php', headers=headers, data=data, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(self._parsesearchresultsfromhtml(resp.text)):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if not isinstance(search_result, dict) or (not search_result.get('url')) or (not (song_id := search_result.get('song_id'))): continue
                with suppress(Exception): resp = None; (resp := self.get(search_result['url'], **request_overrides)).raise_for_status()
                if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                if not (download_url := (download_result := self._extractsonginfo(resp.text)).get('play_url')) or not str(download_url).startswith('http'): continue
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name') or download_result.get('name')), singers=legalizestring(search_result.get('author') or download_result.get('singer')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'],
                    file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric=cleanlrc(download_result.get('lyrics') or 'NULL'), cover_url=download_result.get('cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers={**self.default_download_headers, 'Referer': search_result['url']}
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