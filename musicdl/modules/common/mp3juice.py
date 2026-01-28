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
from itertools import zip_longest
from urllib.parse import urlencode
from rich.progress import Progress
from ..sources import BaseMusicClient
from ..utils import legalizestring, usesearchheaderscookies, usedownloadheaderscookies, touchdir, resp2json, byte2mb, safeextractfromdict, SongInfo, SongInfoUtils


'''MP3JuiceMusicClient'''
class MP3JuiceMusicClient(BaseMusicClient):
    source = 'MP3JuiceMusicClient'
    def __init__(self, **kwargs):
        kwargs['search_size_per_source'] = kwargs['search_size_per_source'] * 2
        super(MP3JuiceMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mp3juice.as/", "Origin": "https://mp3juice.as",
        }
        self.default_download_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mp3juice.as/", "Origin": "https://mp3juice.as",
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_getdynamicconfig'''
    def _getdynamicconfig(self, request_overrides: dict = None):
        request_overrides = request_overrides or {}
        url = f"https://mp3juice.as/?t={int(time.time() * 1000)}"
        resp = self.get(url, **request_overrides)
        resp.raise_for_status()
        match = re.search(r"var\s+json\s*=\s*JSON\.parse\('(.+?)'\);", resp.text)
        if not match: match = re.search(r"var\s+json\s*=\s*(\[.+?\]);", resp.text)
        json_str = match.group(1)
        return json_repair.loads(json_str)
    '''_calculateauth'''
    def _calculateauth(self, raw_data):
        data_arr, should_reverse, offset_arr, result_chars = raw_data[0], raw_data[1], raw_data[2], []
        offset_len = len(offset_arr)
        for t in range(len(data_arr)): result_chars.append(chr(data_arr[t] - offset_arr[offset_len - (t + 1)]))
        if should_reverse: result_chars.reverse()
        full_token = "".join(result_chars)
        return full_token[:32]
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        config = self._getdynamicconfig()
        auth_token = self._calculateauth(config)
        # search rules
        default_rule = {'k': auth_token, 'y': 's', 'q': base64.b64encode(quote(keyword, safe="").encode("utf-8")).decode("utf-8"), 't': str(int(time.time()))}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://mp3juice.as/api/v1/search?'
        page_rule = copy.deepcopy(default_rule)
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
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results_yt, search_results_sc = [], []
            for item in resp2json(resp)["yt"]: item['root_source'] = 'YouTube'; search_results_yt.append(item)
            for item in resp2json(resp)["sc"]: item['root_source'] = 'SoundCloud'; search_results_sc.append(item)
            search_results = [x for ab in zip_longest(search_results_yt, search_results_sc) for x in ab if x is not None]
            for search_result in search_results:
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
                # --download results
                if not isinstance(search_result, dict) or ('id' not in search_result): continue
                if search_result['root_source'] in ['SoundCloud'] and ('id_base64' not in search_result or 'title_base64' not in search_result): continue
                song_info, download_result = SongInfo(source=self.source, root_source=search_result['root_source']), dict()
                # ----SoundCloud
                if search_result['root_source'] in ['SoundCloud']:
                    download_url = f"https://thetacloud.org/s/{search_result['id_base64']}/{search_result['title_base64']}/"
                # ----YouTube
                else:
                    params = {param_key: auth_token, 't': str(int(time.time()))}
                    try:
                        init_resp = self.get('https://theta.thetacloud.org/api/v1/init?', params=params, **request_overrides)
                        init_resp.raise_for_status()
                        download_result['init'] = resp2json(resp=init_resp)
                        convert_url = download_result['init'].get('convertURL', '')
                        if not convert_url: continue
                    except:
                        continue
                    convert_url = f'{convert_url}&v={search_result["id"]}&f=mp3&t={str(int(time.time()))}'
                    try:
                        convert_resp = self.get(convert_url, **request_overrides)
                        convert_resp.raise_for_status()
                        download_result['convert'] = resp2json(resp=convert_resp)
                        redirect_url = download_result['convert'].get('redirectURL', '')
                        if not redirect_url: continue
                    except:
                        continue
                    try:
                        resp = self.get(redirect_url, **request_overrides)
                        resp.raise_for_status()
                        download_result['redirect'] = resp2json(resp=resp)
                        download_url: str = download_result['redirect'].get('downloadURL', '')
                        if not download_url: continue
                    except:
                        continue
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['title'], None)),
                    singers='NULL', album='NULL', ext='mp3', file_size='NULL', identifier=search_result['id'], duration='-:-:-', lyric='NULL', cover_url=None, download_url=download_url, 
                    download_url_status=self.audio_link_tester.test(download_url, request_overrides), root_source=search_result['root_source'],
                )
                if not song_info.with_valid_download_url: continue
                # ----you have to download the music contents immediately, otherwise the links will fail.
                song_info.downloaded_contents = self.get(download_url, **request_overrides).content
                song_info.file_size_bytes = song_info.downloaded_contents.__sizeof__()
                song_info.file_size = byte2mb(song_info.file_size_bytes)
                # --append to song_infos
                song_infos.append(song_info)
            # --update progress
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Error: {err})")
        # return
        return song_infos