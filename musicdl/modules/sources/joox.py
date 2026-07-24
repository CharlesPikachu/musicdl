'''
Function:
    Implementation of JooxMusicClient: https://www.joox.com/intl
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import time
import struct
import base64
import hashlib
import requests
import json_repair
from bs4 import BeautifulSoup
from contextlib import suppress
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from ..utils.hosts import JOOX_MUSIC_HOSTS
from urllib.parse import urlencode, urlparse, parse_qs, quote
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, extractdurationsecondsfromlrc, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, LyricSearchClient, IOUtils, SongInfoUtils


'''JooxMusicClient'''
class JooxMusicClient(BaseMusicClient):
    source = 'JooxMusicClient'
    SALT = "Jo0x@t3Nc3nT"
    def __init__(self, **kwargs):
        super(JooxMusicClient, self).__init__(**kwargs)
        self.auth_info = self.default_search_cookies or self.default_parse_cookies or self.default_download_cookies
        if self.default_search_cookies: self.default_search_cookies = self.default_search_cookies.get('cookies') or {}
        if self.default_parse_cookies: self.default_parse_cookies = self.default_parse_cookies.get('cookies') or {}
        if self.default_download_cookies: self.default_download_cookies = self.default_download_cookies.get('cookies') or {}
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Accept": "application/json, text/plain, */*", "Origin": "https://www.joox.com", "Referer": "https://www.joox.com/", "x-forwarded-for": "36.73.34.109"}
        self.default_parse_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Accept": "application/json, text/plain, */*", "Origin": "https://www.joox.com", "Referer": "https://www.joox.com/", "x-forwarded-for": "36.73.34.109"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "x-forwarded-for": "36.73.34.109"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''makesecret'''
    @staticmethod
    def makesecret(params: dict) -> str:
        enc_func = lambda v: quote(str(v), safe="!*'()")
        qs = "&".join(f"{k}={enc_func(v)}" for k, v in params.items())
        return hashlib.md5((JooxMusicClient.SALT + qs).encode()).hexdigest()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'country': self.auth_info.get('country', 'hk'), 'lang': 'zh_TW', 'key': keyword, 'type': '0'}).update(rule)
        # construct search urls
        base_url = 'https://cache.api.joox.com/openjoox/v2/search_type?'
        search_urls = [base_url + urlencode(copy.deepcopy(default_rule))]
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsewithgdstudioxyzapi'''
    def _parsewithgdstudioxyzapi(self, search_result: dict, lang: str = 'zh_TW', country: str = 'hk', request_overrides: dict = None):
        # init
        host = "music.gdstudio.xyz"; version = "2026.07.21"; time_url = "https://music.gdstudio.xyz/time"; api_url = "https://music.gdstudio.xyz/api.php"
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Origin": "https://music.gdstudio.xyz", "Referer": "https://music.gdstudio.xyz/", "X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/javascript, */*; q=0.01", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        js_encode_uri_component_func = lambda value: (quote(str(value), safe="-_.!~*'()").replace("(", "%28").replace(")", "%29").replace("*", "%2A").replace("'", "%27").replace("!", "%21"))
        left_rotate_func = lambda x, amount: ((((x & 0xFFFFFFFF) << amount) | ((x & 0xFFFFFFFF) >> (32 - amount))) & 0xFFFFFFFF)
        normalize_version_func = lambda value: "".join(part.zfill(2) if len(part) == 1 else part for part in str(value).split("."))
        # parse
        with suppress(Exception): server_time = str(int(time.time())); (server_time_resp := requests.get(time_url, headers=headers, timeout=10, **request_overrides)).raise_for_status(); server_time = server_time_resp.text.strip()
        encoded_id = js_encode_uri_component_func(str(song_id)); raw_sign_text = f"{str(server_time)[:9]}|{host}|{normalize_version_func(version)}|{encoded_id}"
        data = raw_sign_text.encode("utf-8"); bit_len = (len(data) * 8) & 0xFFFFFFFFFFFFFFFF; data += b"\x80"
        while len(data) % 64 != 56: data += b"\x00"
        data += struct.pack("<Q", bit_len); a0 = 0x67452301; b0 = 0xEFCDAB89; c0 = 0x98BADCFE; d0 = 0x10325476
        shifts = [7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21]
        table = [
            0xD76AA478, 0xE8C7B756, 0x242070DB, 0xC1BDCEEE, 0xF57C0FAF, 0x4787C62A, 0xA8304613, 0xFD469501, 0x698098D8, 0x8B44F7AF, 0xFFFF5BB1, 0x895CD7BE, 0x6B901122, 0xFD987193, 0xA679438E, 0x49B40821,
            0xF61E2562, 0xC040B340, 0x265E5A51, 0xE9B6C7AA, 0xD62F105D, 0x02441453, 0xD8A1E681, 0xE7D3FBC8, 0x21E1CDE6, 0xC33707D6, 0xF4D50D87, 0x455A14ED, 0xA9E3E905, 0xFCEFA3F8, 0x676F02D9, 0x8D2A4C8A,
            0xFFFA3942, 0x8771F681, 0x6D9D6123, 0xFDE5380C, 0xA4BEEA44, 0x4BDECFA9, 0xF6BB4B60, 0xBEBFBC70, 0x289B7EC6, 0xEAA127FA, 0xD4EF3085, 0x04881D05, 0xD9D4D039, 0xE6DB99E5, 0x1FA27CF8, 0xC4AC5665,
            0xF4292244, 0x432AFF97, 0xAB9423A7, 0xFC93A039, 0x655B59C3, 0x8F0CCC92, 0xFFEFF47D, 0x85845DD1, 0x6FA87E4F, 0xFE2CE6E0, 0xA3014314, 0x4E0811A1, 0xF7537E82, 0xBD3AF235, 0x2AD7D2BB, 0xEB86D391,
        ]
        for offset in range(0, len(data), 64):
            words = list(struct.unpack("<16I", data[offset: offset + 64])); a, b, c, d = a0, b0, c0, d0
            for i in range(64):
                f, g = (((b & c) | ((~b) & d), i) if i < 16 else ((d & b) | (c & (~d)), (5 * i + 1) % 16) if i < 32 else (b ^ c ^ d, (3 * i + 5) % 16) if i < 48 else (c ^ (b | (~d)), (7 * i) % 16))
                f = (f + a + table[i] + words[g]) & 0xFFFFFFFF; a, d, c, b = d, c, b, (b + left_rotate_func(f, shifts[i])) & 0xFFFFFFFF
            a0 = (a0 + a) & 0xFFFFFFFF; b0 = (b0 + b) & 0xFFFFFFFF; c0 = (c0 + c) & 0xFFFFFFFF; d0 = (d0 + d) & 0xFFFFFFFF
        params = {"types": "url", "id": str(song_id), "source": "joox", "br": str(999), "s": struct.pack("<4I", a0, b0, c0, d0).hex()[-8:].upper()}
        (resp := requests.post(api_url, data=params, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result_gdstudio := resp2json(resp=resp)), ['url'], '')
        (download_result := self._getsongmetainfo(song_id, lang, country, request_overrides)).update(download_result_gdstudio)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (download_result.get('artist_list', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(download_result.get('album_name')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
            identifier=song_id, duration_s=int(float(search_result.get('play_duration') or download_result.get('play_duration') or 0)), duration=SongInfoUtils.seconds2hms(search_result.get('play_duration') or download_result.get('play_duration')), lyric=cleanlrc(base64.b64decode(download_result.get('lrc_content') or '').decode('utf-8')), cover_url=safeextractfromdict(download_result, ['images', 0, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithgdstudioorgapi'''
    def _parsewithgdstudioorgapi(self, search_result: dict, lang: str = 'zh_TW', country: str = 'hk', request_overrides: dict = None):
        # init
        host = "music.gdstudio.org"; version = "2026.07.21"; time_url = "https://music.gdstudio.org/time"; api_url = "https://music.gdstudio.org/api.php"
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Origin": "https://music.gdstudio.org", "Referer": "https://music.gdstudio.org/", "X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/javascript, */*; q=0.01", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        js_encode_uri_component_func = lambda value: (quote(str(value), safe="-_.!~*'()").replace("(", "%28").replace(")", "%29").replace("*", "%2A").replace("'", "%27").replace("!", "%21"))
        left_rotate_func = lambda x, amount: ((((x & 0xFFFFFFFF) << amount) | ((x & 0xFFFFFFFF) >> (32 - amount))) & 0xFFFFFFFF)
        normalize_version_func = lambda value: "".join(part.zfill(2) if len(part) == 1 else part for part in str(value).split("."))
        # parse
        with suppress(Exception): server_time = str(int(time.time())); (server_time_resp := requests.get(time_url, headers=headers, timeout=10, **request_overrides)).raise_for_status(); server_time = server_time_resp.text.strip()
        encoded_id = js_encode_uri_component_func(str(song_id)); raw_sign_text = f"{str(server_time)[:9]}|{host}|{normalize_version_func(version)}|{encoded_id}"
        data = raw_sign_text.encode("utf-8"); bit_len = (len(data) * 8) & 0xFFFFFFFFFFFFFFFF; data += b"\x80"
        while len(data) % 64 != 56: data += b"\x00"
        data += struct.pack("<Q", bit_len); a0 = 0x67452301; b0 = 0xEFCDAB89; c0 = 0x98BADCFE; d0 = 0x10325476
        shifts = [7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21]
        table = [
            0xD76AA478, 0xE8C7B756, 0x242070DB, 0xC1BDCEEE, 0xF57C0FAF, 0x4787C62A, 0xA8304613, 0xFD469501, 0x698098D8, 0x8B44F7AF, 0xFFFF5BB1, 0x895CD7BE, 0x6B901122, 0xFD987193, 0xA679438E, 0x49B40821,
            0xF61E2562, 0xC040B340, 0x265E5A51, 0xE9B6C7AA, 0xD62F105D, 0x02441453, 0xD8A1E681, 0xE7D3FBC8, 0x21E1CDE6, 0xC33707D6, 0xF4D50D87, 0x455A14ED, 0xA9E3E905, 0xFCEFA3F8, 0x676F02D9, 0x8D2A4C8A,
            0xFFFA3942, 0x8771F681, 0x6D9D6123, 0xFDE5380C, 0xA4BEEA44, 0x4BDECFA9, 0xF6BB4B60, 0xBEBFBC70, 0x289B7EC6, 0xEAA127FA, 0xD4EF3085, 0x04881D05, 0xD9D4D039, 0xE6DB99E5, 0x1FA27CF8, 0xC4AC5665,
            0xF4292244, 0x432AFF97, 0xAB9423A7, 0xFC93A039, 0x655B59C3, 0x8F0CCC92, 0xFFEFF47D, 0x85845DD1, 0x6FA87E4F, 0xFE2CE6E0, 0xA3014314, 0x4E0811A1, 0xF7537E82, 0xBD3AF235, 0x2AD7D2BB, 0xEB86D391,
        ]
        for offset in range(0, len(data), 64):
            words = list(struct.unpack("<16I", data[offset: offset + 64])); a, b, c, d = a0, b0, c0, d0
            for i in range(64):
                f, g = (((b & c) | ((~b) & d), i) if i < 16 else ((d & b) | (c & (~d)), (5 * i + 1) % 16) if i < 32 else (b ^ c ^ d, (3 * i + 5) % 16) if i < 48 else (c ^ (b | (~d)), (7 * i) % 16))
                f = (f + a + table[i] + words[g]) & 0xFFFFFFFF; a, d, c, b = d, c, b, (b + left_rotate_func(f, shifts[i])) & 0xFFFFFFFF
            a0 = (a0 + a) & 0xFFFFFFFF; b0 = (b0 + b) & 0xFFFFFFFF; c0 = (c0 + c) & 0xFFFFFFFF; d0 = (d0 + d) & 0xFFFFFFFF
        params = {"types": "url", "id": str(song_id), "source": "joox", "br": str(999), "s": struct.pack("<4I", a0, b0, c0, d0).hex()[-8:].upper()}
        (resp := requests.post(api_url, data=params, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result_gdstudio := resp2json(resp=resp)), ['url'], '')
        (download_result := self._getsongmetainfo(song_id, lang, country, request_overrides)).update(download_result_gdstudio)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (download_result.get('artist_list', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(download_result.get('album_name')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
            identifier=song_id, duration_s=int(float(search_result.get('play_duration') or download_result.get('play_duration') or 0)), duration=SongInfoUtils.seconds2hms(search_result.get('play_duration') or download_result.get('play_duration')), lyric=cleanlrc(base64.b64decode(download_result.get('lrc_content') or '').decode('utf-8')), cover_url=safeextractfromdict(download_result, ['images', 0, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, lang: str = 'zh_TW', country: str = 'hk', request_overrides: dict = None):
        if self.default_cookies: return SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
        for parser_func in [self._parsewithgdstudioxyzapi, self._parsewithgdstudioorgapi, ]:
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, lang, country, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_getsongmetainfo'''
    def _getsongmetainfo(self, song_id, lang: str = 'zh_TW', country: str = 'hk', request_overrides: dict = None):
        params = {"country": country, "lang": lang, "lyric": 1, "fs": 1, "im": 0, "uid": self.auth_info.get('wmid', '142420656'), "usk": self.auth_info.get('session_key', '2a5d97d05dc8fe238150184eaf3519ad'), "id": song_id}
        secret, api_url, path_id = JooxMusicClient.makesecret(params), "https://cache.api.joox.com/openjoox2/v1/track", str(song_id).replace("/", "_")
        del params["id"]; params["secret"] = secret; song_api_url = f"{api_url}/{path_id}"
        with suppress(Exception): resp = None; (resp := self.get(song_api_url, params=params, timeout=20, **request_overrides)).raise_for_status()
        return resp2json(resp=resp)
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, lang: str = 'zh_TW', country: str = 'hk', song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            for download_url in ((safeextractfromdict(download_result := self._getsongmetainfo(song_id, lang, country, request_overrides), ['play_url_list'], []) or []) + [download_result.get('refrain_url')]):
                if not download_url or not (str(download_url).startswith('http')): continue
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (download_result.get('artist_list', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(download_result.get('album_name')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                    identifier=song_id, duration_s=int(float(search_result.get('play_duration') or download_result.get('play_duration') or 0)), duration=SongInfoUtils.seconds2hms(search_result.get('play_duration') or download_result.get('play_duration')), lyric=cleanlrc(base64.b64decode(download_result.get('lrc_content') or '').decode('utf-8')), cover_url=safeextractfromdict(download_result, ['images', 0, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        params, resp = {'musicid': song_id, 'country': country, 'lang': lang}, None
        with suppress(Exception): (resp := self.get('https://api.joox.com/web-fcgi-bin/web_lyric', params=params, **request_overrides)).raise_for_status()
        if resp is None: lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        else: lyric_result: dict = json_repair.loads(resp.text.replace('MusicJsonCallback(', '')[:-1]) or {}; lyric = cleanlrc(base64.b64decode(lyric_result.get('lyric') or '').decode('utf-8')) or 'NULL'
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, parsed_search_url, search_result_idx = request_overrides or {}, parse_qs(urlparse(search_url).query, keep_blank_values=True), -1
        lang, country, page_no, lossless_quality_is_sufficient = parsed_search_url['lang'][0], parsed_search_url['country'][0], 1, False if self.default_cookies or request_overrides.get('cookies') else True
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp=resp)['tracks']):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                search_result = search_result[0] if isinstance(search_result, list) else search_result
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with third part apis
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, lang=lang, country=country, request_overrides=request_overrides)
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, lang=lang, country=country, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
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
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        # init
        playlist_url, lang, country = self.session.head(playlist_url, allow_redirects=True, **(request_overrides := dict(request_overrides or {}))).url, 'zh_TW', self.auth_info.get('country', 'hk')
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, JOOX_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        (resp := self.get(playlist_url, **request_overrides)).raise_for_status()
        if not (script_tag := (BeautifulSoup(resp.text, 'lxml')).find('script', id='__NEXT_DATA__')): return song_infos
        tracks_in_playlist = (playlist_result := json_repair.loads(script_tag.string))['props']['pageProps']['allPlaylistTracks']['tracks']['items']
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}})
                song_info_flac = self._parsewiththirdpartapis(search_result=track_info, lang=lang, country=country, request_overrides=request_overrides)
                lossless_quality_is_sufficient = False if self.default_cookies or request_overrides.get('cookies') else True
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=track_info, lang=lang, country=country, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                if (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse track info {track_info}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result['props']['pageProps']['allPlaylistTracks'], ['name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos