'''
Function:
    Implementation of MyFreeMP3MusicClient: https://www.myfreemp3.com.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
from contextlib import suppress
from urllib.parse import urlparse
from rich.progress import Progress
from ..sources import BaseMusicClient
from ..utils import legalizestring, resp2json, usesearchheaderscookies, extractdurationsecondsfromlrc, searchdictbykey, cleanlrc, SongInfo, QuarkParser, AudioLinkTester, SongInfoUtils


'''MyFreeMP3MusicClient'''
class MyFreeMP3MusicClient(BaseMusicClient):
    source = 'MyFreeMP3MusicClient'
    def __init__(self, **kwargs):
        super(MyFreeMP3MusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so only "netease" source can be leveraged.')
        self.allowed_music_sources = ['kuake', 'netease'] if self.quark_parser_config.get('cookies') else ['netease']
        self.default_search_headers = {
            "accept": "*/*", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "content-type": "application/x-www-form-urlencoded; charset=UTF-8", "priority": "u=1, i", "x-requested-with": "XMLHttpRequest",
            "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "origin": "https://www.myfreemp3.com.cn",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "sec-fetch-site": "same-origin",
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, allowed_music_sources, self.search_size_per_page = rule or {}, request_overrides or {}, copy.deepcopy(self.allowed_music_sources), min(10, self.search_size_per_page)
        (default_rule := {'type': 'netease', 'filter': 'name', 'page': '1', 'input': keyword}).update(rule)
        # construct search urls
        search_urls, page_size, base_url = [], self.search_size_per_page, 'https://www.myfreemp3.com.cn/'
        for source in allowed_music_sources:
            (source_default_rule := copy.deepcopy(default_rule))['type'], count = source, 0
            while self.search_size_per_source > count:
                (page_rule := copy.deepcopy(source_default_rule))['page'] = str(int(count // page_size) + 1)
                search_urls.append({'url': base_url, 'data': page_rule, 'source': source})
                count += page_size
        # return
        return search_urls
    '''_parseneteasesearchresult'''
    def _parseneteasesearchresult(self, search_result: dict, request_overrides: dict = None):
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return SongInfo(source=self.source)
        download_url = self.session.head(f'http://music.163.com/song/media/outer/url?id={search_result["id"]}.mp3', timeout=10, allow_redirects=True, **(request_overrides := request_overrides or {})).url
        duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc((search_result.get('lrc') or '').removeprefix('data:text/plain,'))))
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
            identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, root_source='netease',
        )
        return song_info
    '''_parsequarksearchresult'''
    def _parsequarksearchresult(self, search_result: dict, request_overrides: dict = None):
        if (not isinstance(search_result, dict)) or ('url_kk' not in search_result): return SongInfo(source=self.source)
        search_result['id'], request_overrides = urlparse(str(search_result['url_kk'])).path.strip('/').split('/')[-1], request_overrides or {}
        download_result, download_url = QuarkParser.parsefromurl(search_result['url_kk'], **self.quark_parser_config)
        if not download_url or not str(download_url).startswith('http'): return SongInfo(source=self.source)
        download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]) else 0
        song_name, singers = (lambda s: (m.group(2).strip(), m.group(1).strip()) if (m:=re.search(r'^\s*(.*?)\s*[-–—－]\s*(.*?)(?:\.[A-Za-z0-9]{1,5})?\s*(?:\s*[-–—－]\s*.*)?$', s.strip())) else (re.sub(r'\.[^.]+$', '', s.strip()).strip(), ""))(search_result.get('title'))
        lyric: str = cleanlrc((search_result.get('lrc') or '').removeprefix('data:text/plain,'))
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(song_name), singers=legalizestring(singers), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=search_result['id'], 
            duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, root_source='quark', default_download_headers=self.quark_default_download_headers,
        )
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = None, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, search_meta = request_overrides or {}, copy.deepcopy(search_url)
        search_url, source = search_meta.pop('url'), search_meta.pop('source')
        # successful
        try:
            # --search results
            (resp := self.post(search_url, **search_meta, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp)['data']['list']:
                # --download results
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                with suppress(Exception): song_info = {'netease': self._parseneteasesearchresult, 'kuake': self._parsequarksearchresult}[source](search_result, request_overrides)
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
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