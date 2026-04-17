'''
Function:
    Implementation of MP3JuiceMusicClient: https://mp3juice.co/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
import time
import base64
import json_repair
from urllib.parse import quote
from contextlib import suppress
from itertools import zip_longest
from urllib.parse import urlencode
from rich.progress import Progress
from ..sources import BaseMusicClient
from ..utils import legalizestring, usesearchheaderscookies, resp2json, SongInfo, SongInfoUtils, AudioLinkTester


'''MP3JuiceMusicClient'''
class MP3JuiceMusicClient(BaseMusicClient):
    source = 'MP3JuiceMusicClient'
    def __init__(self, **kwargs):
        kwargs['search_size_per_source'] = kwargs['search_size_per_source'] * 2
        super(MP3JuiceMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Referer": "https://mp3juice.sc/", "Origin": "https://mp3juice.sc"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Referer": "https://mp3juice.sc/", "Origin": "https://mp3juice.sc"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_getdynamicconfig'''
    def _getdynamicconfig(self, request_overrides: dict = None):
        (resp := self.get(f"https://mp3juice.as/?t={int(time.time() * 1000)}", **dict(request_overrides or {}))).raise_for_status()
        if not (match := re.search(r"var\s+json\s*=\s*JSON\.parse\('(.+?)'\);", resp.text)): match = re.search(r"var\s+json\s*=\s*(\[.+?\]);", resp.text)
        return json_repair.loads(match.group(1))
    '''_calculateauth'''
    def _calculateauth(self, raw_data):
        data_arr, should_reverse, offset_arr, result_chars = raw_data[0], raw_data[1], raw_data[2], []
        result_chars = [chr(data_arr[t] - offset_arr[len(offset_arr) - 1 - t]) for t in range(len(data_arr))]
        full_token = "".join(reversed(result_chars) if should_reverse else result_chars)
        return full_token[:32]
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, auth_token = rule or {}, request_overrides or {}, self._calculateauth((config := self._getdynamicconfig()))
        (default_rule := {'k': auth_token, 'y': 's', 'q': base64.b64encode(quote(keyword, safe="").encode("utf-8")).decode("utf-8"), 't': str(int(time.time()))}).update(rule)
        # construct search urls
        base_url, page_rule = 'https://mp3juice.sc/api/v1/search?', copy.deepcopy(default_rule)
        search_urls = [{'url': base_url + urlencode(page_rule), 'auth_token': auth_token, 'param_key': chr(config[6])}]
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = None, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, search_meta = request_overrides or {}, copy.deepcopy(search_url)
        search_url, auth_token, param_key = search_meta['url'], search_meta['auth_token'], search_meta['param_key']
        # successful
        try:
            # --search results
            (resp := self.get(search_url, allow_redirects=True, **request_overrides)).raise_for_status()
            search_results_yt = [{**item, "root_source": "YouTube"} for item in resp2json(resp)["yt"]]
            search_results_sc = [{**item, "root_source": "SoundCloud"} for item in resp2json(resp)["sc"]]
            for search_result in [x for ab in zip_longest(search_results_yt, search_results_sc) for x in ab if x is not None]:
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
                # --download results
                if not isinstance(search_result, dict) or (not (song_id := search_result.get('id'))): continue
                if search_result['root_source'] in ['SoundCloud'] and ('id_base64' not in search_result or 'title_base64' not in search_result): continue
                song_info, download_result = SongInfo(source=self.source, root_source=search_result['root_source']), dict()
                # ----SoundCloud
                if search_result['root_source'] in ['SoundCloud']: download_url = f"https://thetacloud.org/s/{search_result['id_base64']}/{search_result['title_base64']}/"
                # ----YouTube
                else:
                    with suppress(Exception): (init_resp := self.get('https://theta.thetacloud.org/api/v1/init?', params={param_key: auth_token, 't': str(int(time.time()))}, **request_overrides)).raise_for_status(); download_result['init'] = resp2json(resp=init_resp)
                    if not locals().get('init_resp') or not hasattr(locals().get('init_resp'), 'text') or ('init' not in download_result) or (not (convert_url := download_result['init'].get('convertURL', ''))): continue
                    with suppress(Exception): (convert_resp := self.get(f'{convert_url}&v={search_result["id"]}&f=mp3&t={str(int(time.time()))}', **request_overrides)).raise_for_status(); download_result['convert'] = resp2json(resp=convert_resp)
                    if not locals().get('convert_resp') or not hasattr(locals().get('convert_resp'), 'text') or ('convert' not in download_result) or (not (redirect_url := download_result['convert'].get('redirectURL', ''))): continue
                    with suppress(Exception): (redirect_resp := self.get(redirect_url, **request_overrides)).raise_for_status(); download_result['redirect'] = resp2json(resp=redirect_resp)
                    if not locals().get('redirect_resp') or not hasattr(locals().get('redirect_resp'), 'text') or ('redirect' not in download_result) or (not (download_url := download_result['redirect'].get('downloadURL', ''))): continue
                    del init_resp; del convert_resp; del redirect_resp
                # ----summarize
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers='NULL', album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                    file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric='NULL', cover_url=None, download_url=download_url_status['download_url'], download_url_status=download_url_status, root_source=search_result['root_source'],
                )
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                # ----you have to download the music contents immediately, otherwise the links will fail.
                song_info.downloaded_contents = self.get(download_url, **request_overrides).content
                song_info.file_size_bytes = song_info.downloaded_contents.__sizeof__()
                song_info.file_size = SongInfoUtils.byte2mb(song_info.file_size_bytes)
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
            # --update progress
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Error: {err})")
            self.logger_handle.error(f"{self.source}._search >>> {search_url} (Error: {err})", disable_print=self.disable_print)
        # return
        return song_infos