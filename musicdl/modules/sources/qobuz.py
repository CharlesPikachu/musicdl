'''
Function:
    Implementation of QobuzMusicClient: https://play.qobuz.com/discover
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import time
import random
import base64
import struct
import tempfile
import requests
from contextlib import suppress
from .base import BaseMusicClient
from ..utils.hosts import QOBUZ_MUSIC_HOSTS
from pathvalidate import sanitize_filepath, sanitize_filename
from urllib.parse import urlencode, urlparse, parse_qs, quote
from ..utils.qobuzutils import QobuzMusicClientUtils, ArcodClient, QobuzCommunityClient
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, hostmatchessuffix, obtainhostname, useparseheaderscookies, usedownloadheaderscookies, SongInfo, AudioLinkTester, LyricSearchClient, IOUtils, SongInfoUtils


'''QobuzMusicClient'''
class QobuzMusicClient(BaseMusicClient):
    source = 'QobuzMusicClient'
    arcod_client = ArcodClient(base_url="https://arcod.xyz")
    def __init__(self, **kwargs):
        super(QobuzMusicClient, self).__init__(**kwargs)
        if self.default_search_cookies: assert QobuzMusicClientUtils.get_token_func(self.default_search_cookies, "user_auth_token", "X-User-Auth-Token", "x-user-auth-token"), '"x-user-auth-token" should be configured, refer to "https://musicdl.readthedocs.io/en/latest/Clients.html#qobuzmusicclient-built-in-premium-account"'
        if self.default_parse_cookies: assert QobuzMusicClientUtils.get_token_func(self.default_parse_cookies, "user_auth_token", "X-User-Auth-Token", "x-user-auth-token"), '"x-user-auth-token" should be configured, refer to "https://musicdl.readthedocs.io/en/latest/Clients.html#qobuzmusicclient-built-in-premium-account"'
        if self.default_download_cookies: assert QobuzMusicClientUtils.get_token_func(self.default_download_cookies, "user_auth_token", "X-User-Auth-Token", "x-user-auth-token"), '"x-user-auth-token" should be configured, refer to "https://musicdl.readthedocs.io/en/latest/Clients.html#qobuzmusicclient-built-in-premium-account"'
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "Accept": "application/json"}
        self.default_parse_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "Accept": "application/json"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
        if self.default_search_cookies: self.default_search_headers.update({'X-User-Auth-Token': QobuzMusicClientUtils.get_token_func(self.default_search_cookies, "user_auth_token", "X-User-Auth-Token", "x-user-auth-token")})
        if self.default_parse_cookies: self.default_parse_headers.update({'X-User-Auth-Token': QobuzMusicClientUtils.get_token_func(self.default_parse_cookies, "user_auth_token", "X-User-Auth-Token", "x-user-auth-token")})
        if self.default_download_cookies: self.default_download_headers.update({'X-User-Auth-Token': QobuzMusicClientUtils.get_token_func(self.default_download_cookies, "user_auth_token", "X-User-Auth-Token", "x-user-auth-token")})
        self.default_headers = self.default_search_headers; self.default_search_cookies = {}; self.default_parse_cookies = {}; self.default_download_cookies = {}
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0, auto_supplement_song: bool = True):
        # fallback to general music download method
        if 'decryption' not in song_info.raw_data: return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id, auto_supplement_song=auto_supplement_song)
        # deal with tidal stream object
        song_info, decrypt_audio_settings, request_overrides = copy.deepcopy(song_info), dict(song_info.raw_data['decryption']), dict(request_overrides or {})
        song_info._save_path = sanitize_filepath(song_info.save_path); song_info.work_dir = os.path.dirname(song_info.save_path); IOUtils.touchdir(song_info.work_dir)
        url_template, n_segments, raw_key, segment_uuid = decrypt_audio_settings['url_template'], decrypt_audio_settings['n_segments'], decrypt_audio_settings['raw_key'], None
        progress.update(song_progress_id, total=n_segments+1, kind='hls', description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Downloading)")
        try: 
            with tempfile.TemporaryDirectory(prefix="musicdl-QobuzMusicClient-track-") as tmpdir:
                fp = open((tmp_path := os.path.join(tmpdir, f'{sanitize_filename(str(song_info.identifier))}.mp4')), 'wb')
                for seg_idx in range(n_segments + 1):
                    if seg_idx > 0: progress.advance(song_progress_id, 1); progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Downloading: {seg_idx}/{n_segments+1} Segments)")
                    seg_data = self.get(str(url_template).replace("$SEGMENT$", str(seg_idx)), **request_overrides).content
                    if seg_idx == 1: segment_uuid = QobuzMusicClientUtils.getqobuzsegmentuuid(seg_data)
                    fp.write(QobuzMusicClientUtils.decryptqobuzsegment(seg_data, raw_key, segment_uuid))
                fp.close(); progress.advance(song_progress_id, 1); progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Downloading: {seg_idx+1}/{n_segments+1} Segments)")
                song_info._save_path, song_info.ext = AudioLinkTester.extractaudiofromvideolossless(tmp_path, song_info.save_path)
                downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(song_info, logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else song_info)
        except Exception as err:
            progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})")
            self.logger_handle.error(f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})", disable_print=self.disable_print)
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, timestamp = rule or {}, request_overrides or {}, str(int(time.time()))
        QobuzMusicClientUtils.initsearchappid(self.session, headers=self.default_headers, cookies=self.default_cookies, request_overrides=request_overrides)
        (default_rule := {'query': keyword, 'offset': 0, 'limit': 10}).update(rule)
        # construct search urls
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'https://www.qobuz.com/api.json/0.2/catalog/search?'
        sig = QobuzMusicClientUtils.getrequestsig('catalog/search', default_rule, timestamp, QobuzMusicClientUtils.SEARCH_APP_SECRET)
        default_rule.update({"app_id": QobuzMusicClientUtils.SEARCH_APP_ID, "request_ts": timestamp, "request_sig": sig})
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['limit'] = page_size
            page_rule['offset'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithzarzqbzapi'''
    def _parsewithzarzqbzapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"User-Agent": "SpotiFLAC-Mobile/4.5.0", "Accept": "application/json"}
        # parse
        payload = {"quality": QobuzMusicClientUtils.MUSIC_QUALITIES[0], "upload_to_r2": False, "url": f"https://open.qobuz.com/track/{song_id}"}
        (resp := requests.post("https://api.zarz.moe/v1/dl/qbz", json=payload, headers=headers, timeout=10, allow_redirects=False, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['download_url'], '')
        real_music_quality = real_music_quality[0] if isinstance((real_music_quality := parse_qs(urlparse(str(download_url)).query, keep_blank_values=True).get('fmt') or QobuzMusicClientUtils.MUSIC_QUALITIES[0]), list) else real_music_quality
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': real_music_quality}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['performer', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('duration') or 0))), lyric=None, cover_url=safeextractfromdict(search_result, ['album', 'image', 'large'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        song_info = SongInfo(source=self.source, raw_data={'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithzarzqbz2api'''
    def _parsewithzarzqbz2api(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"User-Agent": "SpotiFLAC-Mobile/4.5.0", "Accept": "application/json"}
        # parse
        payload = {"quality": QobuzMusicClientUtils.MUSIC_QUALITIES[0], "upload_to_r2": False, "url": f"https://open.qobuz.com/track/{song_id}"}
        (resp := requests.post("https://api.zarz.moe/v1/dl/qbz2", json=payload, headers=headers, timeout=10, allow_redirects=False, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['download_url'], '')
        real_music_quality = real_music_quality[0] if isinstance((real_music_quality := parse_qs(urlparse(str(download_url)).query, keep_blank_values=True).get('fmt') or QobuzMusicClientUtils.MUSIC_QUALITIES[0]), list) else real_music_quality
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': real_music_quality}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['performer', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('duration') or 0))), lyric=None, cover_url=safeextractfromdict(search_result, ['album', 'image', 'large'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        song_info = SongInfo(source=self.source, raw_data={'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithanandserverapi'''
    def _parsewithanandserverapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36", "Accept": "audio/flac, audio/*, */*", "Accept-Encoding": "identity", "Referer": "https://open.qobuz.com/", "Origin": "https://open.qobuz.com", "X-API-Key": "ak_8e3f1a7c2b5d9e4f0a6c3b8d1e5f2a9c7b4d0e6f", "api-key": "ak_8e3f1a7c2b5d9e4f0a6c3b8d1e5f2a9c7b4d0e6f",}
        # parse
        for download_url in [f"https://qobuz.anandserver.cfd/api/stream/{song_id}?strict_24=1", f"https://qobuz.anandserver.cfd/api/stream/{song_id}"]:
            with suppress(Exception): resp = None; (resp := requests.get(download_url, headers=headers, stream=True, timeout=30, **request_overrides)).raise_for_status()
            if resp is None or not hasattr(resp, 'status_code') or resp.status_code not in (200, 206): continue
            download_url_status = {'ok': True, 'file_size_bytes': int(resp.headers.get('Content-Length')), 'file_size': SongInfoUtils.byte2mb(resp.headers.get('Content-Length')), 'ext': 'flac', 'download_url': download_url}
            real_music_quality = QobuzMusicClientUtils.MUSIC_QUALITIES[0] if 'strict_24=1' in download_url else QobuzMusicClientUtils.MUSIC_QUALITIES[2]
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': {}, 'lyric': {}, 'quality': real_music_quality}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['performer', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('duration') or 0))), lyric=None, cover_url=safeextractfromdict(search_result, ['album', 'image', 'large'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=headers,
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithspotbyeqzzapi'''
    def _parsewithspotbyeqzzapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, app_version = request_overrides or {}, str(search_result['id']), "7.2.0"
        # parse
        download_result = QobuzCommunityClient(app_version=app_version).requesttrack(song_id, quality="24", request_overrides=request_overrides)
        real_music_quality = real_music_quality[0] if isinstance((real_music_quality := parse_qs(urlparse(str((download_url := download_result['url']))).query, keep_blank_values=True).get('fmt') or QobuzMusicClientUtils.MUSIC_QUALITIES[0]), list) else real_music_quality
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': real_music_quality}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['performer', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('duration') or 0))), lyric=None, cover_url=safeextractfromdict(search_result, ['album', 'image', 'large'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        song_info = SongInfo(source=self.source, raw_data={'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewitharcodapi'''
    def _parsewitharcodapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, country = request_overrides or {}, str(search_result['id']), None
        decrypt_func, accounts = lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8'), [('charlespikachuZzIwODJieXAxaUBsbm92aWMuY29t', 'charlespikachucmFuZG9tOTk5'), ('charlespikachucGlrYWNodUBsaW5zaGl5b3UuY29t', 'charlespikachucGlrYTk5OTY2Ng=='), ('charlespikachudGhlYWNjb3VudHRoaWVmd2lsbGRpZUBsaW5zaGl5b3UuY29t', 'charlespikachudGhlYWNjb3VudHRoaWVmd2lsbGRpZQ==')]
        email, password = random.choice(accounts); email, password = decrypt_func(email), decrypt_func(password)
        # parse
        QobuzMusicClient.arcod_client.login(email=email, password=password, request_overrides=request_overrides)
        track_info = QobuzMusicClient.arcod_client.gettrack(song_id, country=country, request_overrides=request_overrides)
        payload = QobuzMusicClient.arcod_client.buildtrackdownloadpayload(track_info, quality=QobuzMusicClientUtils.MUSIC_QUALITIES[0], output_format="FLAC", bitrate="320", country=country)
        download_id, download_token = QobuzMusicClient.arcod_client.createdownload(payload, country=country, request_overrides=request_overrides)
        final_status = QobuzMusicClient.arcod_client.polluntilcompleted(download_id, download_token=download_token, interval=2, max_polls=300, request_overrides=request_overrides)
        url_info = QobuzMusicClient.arcod_client.getfreshdownloadurl(download_id, download_token=download_token, request_overrides=request_overrides)
        download_result = {'track_info': track_info, 'final_status': final_status, 'url_info': url_info}
        download_url_status: dict = self.audio_link_tester.test(url=url_info['downloadUrl'], request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[0]}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['performer', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('duration') or 0))), lyric=None, cover_url=safeextractfromdict(search_result, ['album', 'image', 'large'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        song_info = SongInfo(source=self.source, raw_data={'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithcyrusna29api'''
    def _parsewithcyrusna29api(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Referer": "https://qobuz-tidal-eclipse.cyrusna29.workers.dev/"}
        # parse
        (resp := requests.post(f"https://qobuz-tidal-eclipse.cyrusna29.workers.dev/generate", json={"quality": "HIRES"}, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        api_url = f"https://qobuz-tidal-eclipse.cyrusna29.workers.dev/u/{resp2json(resp=resp)['token']}/stream/{song_id}"
        (resp := requests.get(api_url, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')
        real_music_quality = real_music_quality[0] if isinstance((real_music_quality := parse_qs(urlparse(str(download_url)).query, keep_blank_values=True).get('fmt') or QobuzMusicClientUtils.MUSIC_QUALITIES[0]), list) else real_music_quality
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': real_music_quality}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['performer', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('duration') or 0))), lyric=None, cover_url=safeextractfromdict(search_result, ['album', 'image', 'large'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        song_info = SongInfo(source=self.source, raw_data={'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithgdstudioxyzapi'''
    def _parsewithgdstudioxyzapi(self, search_result: dict, request_overrides: dict = None):
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
        params = {"types": "url", "id": str(song_id), "source": "qobuz", "br": str(999), "s": struct.pack("<4I", a0, b0, c0, d0).hex()[-8:].upper()}
        (resp := requests.post(api_url, data=params, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')
        real_music_quality = real_music_quality[0] if isinstance((real_music_quality := parse_qs(urlparse(str(download_url)).query, keep_blank_values=True).get('fmt') or QobuzMusicClientUtils.MUSIC_QUALITIES[0]), list) else real_music_quality
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': real_music_quality}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['performer', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('duration') or 0))), lyric=None, cover_url=safeextractfromdict(search_result, ['album', 'image', 'large'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        song_info = SongInfo(source=self.source, raw_data={'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithgdstudioorgapi'''
    def _parsewithgdstudioorgapi(self, search_result: dict, request_overrides: dict = None):
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
        params = {"types": "url", "id": str(song_id), "source": "qobuz", "br": str(999), "s": struct.pack("<4I", a0, b0, c0, d0).hex()[-8:].upper()}
        (resp := requests.post(api_url, data=params, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')
        real_music_quality = real_music_quality[0] if isinstance((real_music_quality := parse_qs(urlparse(str(download_url)).query, keep_blank_values=True).get('fmt') or QobuzMusicClientUtils.MUSIC_QUALITIES[0]), list) else real_music_quality
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': real_music_quality}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['performer', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('duration') or 0))), lyric=None, cover_url=safeextractfromdict(search_result, ['album', 'image', 'large'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        song_info = SongInfo(source=self.source, raw_data={'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if QobuzMusicClientUtils.get_token_func(self.default_headers, "X-User-Auth-Token", "x-user-auth-token"): return SongInfo(source=self.source, raw_data={'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]})
        l1_parser_funcs = [self._parsewithgdstudioxyzapi, self._parsewithcyrusna29api, self._parsewithgdstudioorgapi, self._parsewithanandserverapi, self._parsewitharcodapi, self._parsewithspotbyeqzzapi, ] # vip accounts
        l2_parser_funcs = [self._parsewithzarzqbzapi, self._parsewithzarzqbz2api, ] # vip accounts but unstable
        for parser_func in (l1_parser_funcs + l2_parser_funcs):
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}, 'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}, 'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]})
        request_overrides, song_info_flac = request_overrides or {}, song_info_flac or copy.deepcopy(song_info)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        QobuzMusicClientUtils.initparseappid(self.session, headers=self.default_headers, cookies=self.default_cookies, request_overrides=request_overrides)
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            for music_quality in QobuzMusicClientUtils.MUSIC_QUALITIES:
                if song_info_flac.with_valid_download_url and QobuzMusicClientUtils.MUSIC_QUALITIES.index(music_quality) >= QobuzMusicClientUtils.MUSIC_QUALITIES.index(song_info_flac.raw_data.get('quality', QobuzMusicClientUtils.MUSIC_QUALITIES[-1])): song_info = song_info_flac; break
                with suppress(Exception): (headers := {'X-Session-Id': (session_data := QobuzMusicClientUtils.startsession(session=self.session, headers={**self.default_headers, **{"X-App-Id": QobuzMusicClientUtils.PARSE_APP_ID}}, cookies=self.default_cookies, request_overrides=request_overrides))['session_id']}).update({**self.default_headers, **{"X-App-Id": QobuzMusicClientUtils.PARSE_APP_ID}})
                if not locals().get('headers') or not hasattr(locals().get('headers'), 'items'): continue
                with suppress(Exception): download_result = None; download_result = QobuzMusicClientUtils.gettrackinfo(self.session, headers=headers, cookies=self.default_cookies, track_id=song_id, quality=music_quality, request_overrides=request_overrides)
                if not locals().get('download_result') or not hasattr(locals().get('download_result'), 'items') or not all(download_result.get(k) for k in ['url_template', 'n_segments', 'key']): continue
                decrypt_audio_settings = {'url_template': download_result.get('url_template'), 'n_segments': download_result.get('n_segments'), 'session_key': QobuzMusicClientUtils.derivesessionkey(session_data.get('infos', 'c2FsdA.aW5mbw'))}
                decrypt_audio_settings['raw_key'] = QobuzMusicClientUtils.unwrapcontentkey(decrypt_audio_settings['session_key'], download_result.get('key'))
                download_url_status: dict = self.audio_link_tester.test(url=str(decrypt_audio_settings['url_template']).replace('$SEGMENT$', '0'), request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality, 'decryption': decrypt_audio_settings}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['performer', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None)), ext=download_url_status['ext'], 
                    file_size_bytes='HLS', file_size='HLS', identifier=song_id, duration_s=int(float(download_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(download_result.get('duration') or 0))), lyric=None, cover_url=safeextractfromdict(search_result, ['album', 'image', 'large'], None), download_url=decrypt_audio_settings['url_template'], download_url_status=download_url_status, 
                )
                song_info.ext = 'mp3' if music_quality in {5} else 'flac' # re-set audio format to FLAC or MP3 to avoid unnecessary bugs
                if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, lossless_quality_is_sufficient, search_result_idx = request_overrides or {}, False if QobuzMusicClientUtils.get_token_func(self.default_headers, "X-User-Auth-Token", "x-user-auth-token") else True, -1
        QobuzMusicClientUtils.initsearchappid(self.session, headers=self.default_headers, cookies=self.default_cookies, request_overrides=request_overrides)
        page_no = int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('offset')[0]) / self.search_size_per_page) + 1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, headers={**self.default_headers, **{"X-App-Id": QobuzMusicClientUtils.SEARCH_APP_ID}}, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp)['tracks']['items']):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}, 'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]})
                # --parse with third part apis
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                # --append to song_infos
                if (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url: song_infos.append(song_info)
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
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **(request_overrides := dict(request_overrides or {}))).url
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, QOBUZ_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, page_size, playlist_result_first = [], 1, 500, {}
        self.default_headers.update({"X-App-Id": QobuzMusicClientUtils.initsearchappid(self.session, headers=self.default_headers, cookies=self.default_cookies, request_overrides=request_overrides)[0]})
        while True:
            with suppress(Exception): (resp := self.get("https://www.qobuz.com/api.json/0.2/playlist/get?", params={"playlist_id": playlist_id, "extra": 'tracks', "offset": (page-1)*page_size, 'limit': page_size}, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['tracks', 'items'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['tracks', 'items'], [])); page += 1; del resp
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['tracks', 'total'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["id"]: d for d in tracks_in_playlist}.values())
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}, 'quality': QobuzMusicClientUtils.MUSIC_QUALITIES[-1]})
                song_info_flac = self._parsewiththirdpartapis(search_result=track_info, request_overrides=request_overrides)
                lossless_quality_is_sufficient = False if self.default_cookies or request_overrides.get('cookies') else True
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                if (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse track info {track_info}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos