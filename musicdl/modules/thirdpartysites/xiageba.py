'''
Function:
    Implementation of XiagebaMusicClient: https://xiageba.liumingye.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import uuid
import copy
from contextlib import suppress
from rich.progress import Progress
from typing_extensions import Unpack
from urllib.parse import urlparse, parse_qs, urlencode
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import legalizestring, usesearchheaderscookies, searchdictbykey, resp2json, cleanlrc, SongInfo, QuarkParser, AudioLinkTester, SongInfoUtils


'''XiagebaMusicClient'''
class XiagebaMusicClient(BaseMusicClient):
    source = 'XiagebaMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(XiagebaMusicClient, self).__init__(**kwargs)
        assert self.quark_parser_config.get('cookies'), f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so the songs cannot be downloaded.'
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"q": keyword, "page": 1, "pageSize": 20}).update(rule)
        # construct search urls
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'https://xiageba.liumingye.cn/api/music/search?'
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['page'] = int(count // page_size) + 1
            page_rule['pageSize'] = page_size
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
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
            for search_result_idx, search_result in enumerate(resp2json(resp=resp)['data']):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if not isinstance(search_result, dict) or (not (song_id := search_result.get('id'))): continue
                with suppress(Exception): resp = None; (resp := self.get(f"https://xiageba.liumingye.cn/music/{song_id}/_payload.json?{uuid.uuid4()}", **request_overrides)).raise_for_status()
                if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                download_result, song_info = resp2json(resp=resp), SongInfo(source=self.source, raw_data={'search': search_result})
                lyrics = next(((lambda v: download_result[v] if type(v) is int and 0 <= v < len(download_result) else v)(x["lyrics"]) for x in download_result if isinstance(x, dict) and "lyrics" in x), None)
                for quark_link in [u for x in download_result if isinstance(x, dict) and "url" in x for u in [(lambda v: download_result[v] if type(v) is int and 0 <= v < len(download_result) else v)(x["url"])] if isinstance(u, str) and u.startswith("https://pan.quark.cn/")]:
                    quark_parse_result, download_url = QuarkParser.parsefromurl(quark_link, **self.quark_parser_config)
                    download_result_constructed = {'quark_parse_result': quark_parse_result, 'downloads': download_result}
                    if not download_url or not str(download_url).startswith('http'): continue
                    download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                    duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result_constructed, 'duration') if int(float(d)) > 0]) else 0
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result_constructed, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('artist')), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                        identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(lyrics), cover_url=search_result.get('cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers,
                    )
                    if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
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