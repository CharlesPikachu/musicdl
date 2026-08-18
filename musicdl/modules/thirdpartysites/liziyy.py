'''
Function:
    Implementation of LiziYYMusicClient: https://liziyy.top/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import json
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from typing_extensions import Unpack
from urllib.parse import urljoin, urlparse, parse_qs, quote
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import legalizestring, usesearchheaderscookies, searchdictbykey, extractdurationsecondsfromlrc, cleanlrc, SongInfo, QuarkParser, AudioLinkTester, SongInfoUtils


'''LiziYYMusicClient'''
class LiziYYMusicClient(BaseMusicClient):
    source = 'LiziYYMusicClient'
    MUSIC_QUALITY_RANK = {"DSD": 100, "DSF": 100, "DFF": 100, "WAV": 95, "AIFF": 95, "FLAC": 90, "ALAC": 90, "APE": 88, "WV": 88, "OPUS": 70, "AAC": 65, "M4A": 65, "OGG": 60, "VORBIS": 60, "MP3": 50, "WMA": 45}
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(LiziYYMusicClient, self).__init__(**kwargs)
        assert self.quark_parser_config.get('cookies'), f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so the songs cannot be downloaded.'
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", "Referer": "https://liziyy.top/"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        self.search_size_per_page = min(self.search_size_per_source, 30)
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            search_urls.append(f'https://liziyy.top/search?page={int(count // page_size)}&keyword={quote(keyword)}')
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        search_results, base_url = [], 'https://liziyy.top/'
        for card in BeautifulSoup(html_text, "lxml").select(".music-card"):
            link, name, singer, image = card.select_one('a[href]'), card.select_one('.music-name'), card.select_one('.music-singer'), card.select_one('img')
            if not link or not name: continue
            song_id = parse_qs(urlparse(urljoin(base_url, link['href'])).query, keep_blank_values=True).get('id')[0].removeprefix('MUSIC_')
            cover = next((image.get(attr) for attr in ('src', 'data-src', 'data-original') if image and image.get(attr)), None)
            search_results.append({'id': song_id, 'name': name.get_text(' ', strip=True), 'singer': singer.get_text(' ', strip=True) if singer else '', 'url': urljoin(base_url, link['href']), 'cover': urljoin(base_url, cover) if cover else '',})
        return search_results
    '''_extractsongdetails'''
    def _extractsongdetails(self, html_text: str):
        soup, m = BeautifulSoup(html_text, 'lxml'), re.search(r"const\s+detailJson\s*=\s*'((?:\\.|[^'\\])*)'\s*;", html_text, re.S)
        if m:
            detail: dict = json.loads(json.loads(f'"{m.group(1)}"')); downloads = []
            lyrics_timed = [{'time': float(item.get('time', 0)), 'text': (item.get('lineLyric', '') or '').strip(),} for item in detail.get('music_lrclist', []) if isinstance(item, dict) and (item.get('lineLyric', '') or '').strip()]
            for key, url in detail.items():
                if (quality_match := re.fullmatch(r'(?:music_)?([a-zA-Z0-9]+)(?:_url|Url)', key)) and url: downloads.append({'quality': quality_match.group(1).upper(), 'url': url,})
        else:
            detail, lyrics_timed = {}, [{'time': None, 'text': node.get_text(' ', strip=True)} for node in soup.select('.lyric-line')]
            downloads = [{'quality': option.get('data-format', '').upper(), 'url': button.get('data-url', '').strip(),} for option in soup.select('.download-option[data-format]') if (button := option.select_one('[data-url]')) and button.get('data-url', '').strip()]
        downloads.sort(key=lambda item: (LiziYYMusicClient.MUSIC_QUALITY_RANK.get(item['quality'], 0), 'sycdn.kuwo.cn' in item['url']), reverse=True)
        name_node, singer_node = soup.select_one('.detail-box h1'), soup.select_one('.detail-box .c a')
        return {
            'name': detail.get('music_name') or (name_node.get_text(' ', strip=True) if name_node else ''), 'singer': detail.get('music_artist') or (singer_node.get_text(' ', strip=True) if singer_node else ''),
            'lyrics': '\n'.join(f'[{int(t // 60):02d}:{t % 60:05.2f}]{x["text"]}' if (t := x.get('time')) is not None else x['text'] for x in lyrics_timed if x.get('text')), 'downloads': downloads,
        }
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, page_no, search_result_idx = request_overrides or {}, int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('page')[0])) + 1, -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(self._parsesearchresultsfromhtml(resp.text)):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if not isinstance(search_result, dict) or (not search_result.get('url')) or (not (song_id := search_result.get('id'))): continue
                with suppress(Exception): resp = None; (resp := self.get(search_result['url'], **request_overrides)).raise_for_status()
                if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                download_result, song_info = self._extractsongdetails(resp.text), SongInfo(source=self.source)
                for download_info in (download_result.get('downloads') or []):
                    if (not isinstance(download_info, dict)) or (not download_info.get('url')) or ('pan.quark.cn' not in download_info.get('url')): continue
                    download_result['quark_parse_result'], download_url = QuarkParser.parsefromurl(download_info['url'], **self.quark_parser_config)
                    if not download_url or not str(download_url).startswith('http'): continue
                    download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                    duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]) else 0
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name') or download_result.get('name')), singers=legalizestring(search_result.get('singer') or download_result.get('singer')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                        identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(download_result.get('lyrics') or 'NULL'), cover_url=search_result.get('cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers,
                    )
                    if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
                if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
                if not song_info.duration or song_info.duration in {'-:-:-', '00:00:00'}: song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
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