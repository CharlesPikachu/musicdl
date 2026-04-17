'''
Function:
    Implementation of XimalayaMusicClient: https://www.ximalaya.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import time
import math
import copy
import base64
import binascii
from itertools import chain
from Crypto.Cipher import AES
from contextlib import suppress
from rich.progress import Progress
from ..sources import BaseMusicClient
from urllib.parse import urlencode, urlparse, parse_qs
from ..utils import resp2json, legalizestring, safeextractfromdict, usesearchheaderscookies, SongInfo, SongInfoUtils, AudioLinkTester


'''XimalayaMusicClient'''
class XimalayaMusicClient(BaseMusicClient):
    source = 'XimalayaMusicClient'
    ALLOWED_SEARCH_TYPES = ['album', 'track']
    def __init__(self, **kwargs):
        self.allowed_search_types = list(set(kwargs.pop('allowed_search_types', XimalayaMusicClient.ALLOWED_SEARCH_TYPES)))
        super(XimalayaMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'appid': '0', 'condition': 'relation', 'core': 'track', 'device': 'android', 'deviceId': '9a68144e-de5b-3c60-be5e-adce947ab5ff', 'kw': keyword, 'live': 'true', 'needSemantic': 'true', 'network': 'wifi', 'operator': '1', 'page': '1', 'paidFilter': 'false', 'plan': 'c', 'recall': 'normal', 'rows': self.search_size_per_page, 'search_version': '2.8', 'spellchecker': 'true', 'version': '6.6.48', 'voiceAsinput': 'false'}).update(rule)
        # construct search urls
        base_url, search_urls, page_size = 'https://searchwsa.ximalaya.com/front/v1?', [], self.search_size_per_page
        for search_type in XimalayaMusicClient.ALLOWED_SEARCH_TYPES:
            if search_type not in self.allowed_search_types: continue
            (default_rule_search_type := copy.deepcopy(default_rule))['core'], count = search_type, 0
            while self.search_size_per_source > count:
                (page_rule := copy.deepcopy(default_rule_search_type))['rows'] = str(page_size)
                page_rule['page'] = str(int(count // page_size) + 1)
                search_urls.append(base_url + urlencode(page_rule))
                count += page_size
        # return
        return search_urls
    '''_crackplayurl'''
    def _crackplayurl(self, ciphertext: str):
        if not ciphertext or not isinstance(ciphertext, str): return ciphertext
        cipher = AES.new(binascii.unhexlify("aaad3e4fd540b0f79dca95606e72bf93"), AES.MODE_ECB)
        plaintext = cipher.decrypt(base64.urlsafe_b64decode(ciphertext + "=" * (4 - len(ciphertext) % 4)))
        return re.sub(r"[^\x20-\x7E]", "", plaintext.decode("utf-8"))
    '''_parsewithcggapi'''
    def _parsewithcggapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('id') or search_result.get('trackId'), SongInfo(source=self.source)
        # parse
        (resp := self.get(f"https://api-v2.cenguigui.cn/api/music/ximalaya.php?trackId={song_id}", **request_overrides)).raise_for_status()
        if ('0 MB' == (download_result := resp2json(resp=resp))['size']) or (not (download_url := download_result.get('url'))) or (not str(download_url).startswith('http')): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('nickname')), album=legalizestring(search_result.get('album_title') or search_result.get('albumTitle')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration', 0) or 0)), duration=SongInfoUtils.seconds2hms(search_result.get('duration', 0) or 0), lyric=None, cover_url=search_result.get('cover_path'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('id') or search_result.get('trackId'), SongInfo(source=self.source)
        # parse
        (resp := self.get(f"https://www.ximalaya.com/mobile-playpage/track/v3/baseInfo/{int(time.time() * 1000)}", params={"device": "web", "trackId": song_id, "trackQualityLevel": '3'}, **request_overrides)).raise_for_status()
        if not (track_info := safeextractfromdict((download_result := resp2json(resp=resp)), ['trackInfo'], {}) or {}) or not isinstance(track_info, dict): return song_info
        for encrypted_url in sorted((safeextractfromdict(track_info, ['playUrlList'], []) or []), key=lambda x: int(x['fileSize']), reverse=True):
            if not isinstance(encrypted_url, dict) or not (download_url := self._crackplayurl(encrypted_url.get('url'))) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('nickname')), album=legalizestring(search_result.get('album_title') or search_result.get('albumTitle')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration', 0) or 0)), duration=SongInfoUtils.seconds2hms(search_result.get('duration', 0) or 0), lyric=None, cover_url=search_result.get('cover_path'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and (song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): break
        # return
        return song_info
    '''_parsebytrack'''
    def _parsebytrack(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        for search_result in search_results['response']['docs']:
            if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): continue
            song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}}, identifier=song_id)
            for parser in [self._parsewithcggapi, self._parsewithofficialapiv1]:
                with suppress(Exception): song_info = parser(search_result=search_result, request_overrides=dict(request_overrides or {}))
                if song_info.with_valid_download_url and (song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): break
            if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
            if song_info.with_valid_download_url: song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        return song_infos
    '''_parsebyalbum'''
    def _parsebyalbum(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        for search_result in search_results['response']['docs']:
            if (not isinstance(search_result, dict)) or (not (album_id := search_result.get('id'))): continue
            download_results, page_size, tracks, unique_track_ids, request_overrides = [], 200, [], set(), request_overrides or {}
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_results, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('nickname')), album=f"{search_result.get('tracks', 0) or 0} Episodes", 
                ext=None, file_size_bytes=None, file_size=None, identifier=album_id, duration_s=None, duration='-:-:-', lyric=None, cover_url=search_result.get('cover_path'), download_url=None, download_url_status={}, episodes=[],
            )
            num_pages = math.ceil(int(search_result.get('tracks', 0) or 0) / page_size)
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/{num_pages}) pages downloaded in album {album_id}", total=num_pages)
            for page_num_idx, page_num in enumerate(range(1, num_pages + 1)):
                if page_num_idx > 0: progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({page_num_idx}/{num_pages}) pages downloaded in album {album_id}")
                with suppress(Exception): download_results.append(resp2json(resp=self.get(f'http://mobile.ximalaya.com/mobile/v1/album/track?albumId={album_id}&pageId={page_num}&pageSize={page_size}&isAsc=true', **request_overrides)))
            progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({page_num_idx+1}/{num_pages}) pages downloaded in album {album_id}")
            for track in chain.from_iterable((safeextractfromdict(download_result, ['data', 'list'], []) or []) for download_result in download_results):
                if (not isinstance(track, dict)) or (not track.get('trackId')) or (track.get('trackId') in unique_track_ids): continue
                unique_track_ids.add(track.get('trackId')); tracks.append(track)
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/{len(tracks)}) episodes completed in album {album_id}", total=len(tracks))
            for track_idx, track in enumerate(tracks):
                if track_idx > 0: progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({track_idx}/{len(tracks)}) episodes completed in album {album_id}")
                eps_info = SongInfo(source=self.source, raw_data={'search': track, 'download': {}, 'lyric': {}})
                for parser in [self._parsewithcggapi, self._parsewithofficialapiv1]:
                    with suppress(Exception): eps_info = parser(search_result=track, request_overrides=request_overrides)
                    if eps_info.with_valid_download_url and (eps_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): break
                if not eps_info.with_valid_download_url or eps_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                if eps_info.with_valid_download_url: song_info.episodes.append(eps_info)
            progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({track_idx+1}/{len(tracks)}) episodes completed in album {album_id}")
            if len(song_info.episodes) == 0 or not song_info.with_valid_download_url: continue
            with suppress(Exception): song_info.duration_s = sum([float(eps.duration_s) for eps in song_info.episodes]); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
            with suppress(Exception): song_info.file_size_bytes = sum([float(eps.file_size_bytes) for eps in song_info.episodes]); song_info.file_size = SongInfoUtils.byte2mb(song_info.file_size_bytes)
            if song_info.with_valid_download_url: song_info.album = f"{len(song_info.episodes)} Episodes"; song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        return song_infos
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            # --parse based on search type
            search_type = parse_qs(urlparse(search_url).query, keep_blank_values=True).get('core')[0]
            parsers = {'album': self._parsebyalbum, 'track': self._parsebytrack}
            parsers[search_type](resp2json(resp), song_infos=song_infos, request_overrides=request_overrides, progress=progress)
            # --update progress
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Error: {err})")
            self.logger_handle.error(f"{self.source}._search >>> {search_url} (Error: {err})", disable_print=self.disable_print)
        # return
        return song_infos