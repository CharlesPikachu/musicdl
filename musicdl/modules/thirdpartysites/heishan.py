'''
Function:
    Implementation of HeishanMusicClient: https://www.163cn.cc/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from typing_extensions import Unpack
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from ..utils import legalizestring, usesearchheaderscookies, searchdictbykey, cleanlrc, SongInfo, AudioLinkTester, QuarkParser, SongInfoUtils


'''HeishanMusicClient'''
class HeishanMusicClient(BaseMusicClient):
    source = 'HeishanMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(HeishanMusicClient, self).__init__(**kwargs)
        assert self.quark_parser_config.get('cookies'), f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so the songs cannot be downloaded.'
        self.default_search_headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36',}
        self.default_download_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36',}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'page': 1, 'keyword': keyword}).update(rule)
        # construct search urls
        base_url, self.search_size_per_page = 'https://www.163cn.cc/search.html?', min(self.search_size_per_source, 20)
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['page'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        soup, search_results, base_url = BeautifulSoup(html_text, 'lxml'), [], 'https://www.163cn.cc/'
        for li in soup.select('.songslist ul li'):
            if not (a := li.select_one('a[href^="/songs/"]')): continue
            if not (m := re.search(r'/songs/(\d+)\.html', str(a.get('href', '') or ''))): continue
            search_results.append({
                'title': (title.get_text(' ', strip=True) if (title := li.select_one('.t h3')) else None), 'artist': (artist.get_text(' ', strip=True) if (artist := li.select_one('.s')) else None), 'date': (date.get_text(' ', strip=True) if (date := li.select_one('.d')) else None), 
                'formats': [span.get_text(' ', strip=True) for span in li.select('.t span')], 'cover_url': (img.get('src') if (img := li.select_one('.pic img[src]')) else None), 'url': urljoin(base_url, a.get('href')), 'id': m.group(1),
            })
        return search_results[:self.search_size_per_page]
    '''_extractlyricfromhtml'''
    def _extractlyricfromhtml(self, html_text: str):
        soup = BeautifulSoup(html_text, 'lxml')
        if not (lyrics := soup.select_one('.lyrics')): return 'NULL'
        lyric = '\n'.join(p.get_text(' ', strip=True) for p in lyrics.select('p'))
        return cleanlrc(lyric.strip() if lyric.strip() else 'NULL')
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result.get('id')
        # parse download result
        (resp := self.get(search_result['url'], **request_overrides)).raise_for_status(); lyric = self._extractlyricfromhtml(resp.text)
        (resp := self.get(f'https://www.163cn.cc/download/{song_id}.html?t=0', **request_overrides)).raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml'); quark_links = list(dict.fromkeys(a['href'] for a in soup.select('a[href^="https://pan.quark.cn/s/"]')))
        (resp := self.get(f'https://www.163cn.cc/download/{song_id}.html?t=1', **request_overrides)).raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml'); quark_links += list(dict.fromkeys(a['href'] for a in soup.select('a[href^="https://pan.quark.cn/s/"]')))
        for quark_download_link in quark_links:
            quark_parse_result, download_url = QuarkParser.parsefromurl(quark_download_link, **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(quark_parse_result, 'duration') if int(float(d)) > 0]) else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': {'quark_download_link': quark_download_link, 'quark_parse_result': quark_parse_result}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('artist')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=search_result.get('cover_url'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers,
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, page_no, search_result_idx = request_overrides or {}, int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('page')[0])), -1
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
                song_info = SongInfo(source=self.source, raw_data={'search': search_result})
                # ----parse from quark links
                with suppress(Exception): song_info = self._parsesearchresultfromquark(search_result, request_overrides) if self.quark_parser_config.get('cookies') else SongInfo(source=self.source)
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