'''
Function:
    Implementation of DeezerMusicClient: https://www.deezer.com/us/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import uuid
import copy
import time
import random
import base64
import requests
from pathlib import Path
from contextlib import suppress
from .base import BaseMusicClient
from ..utils.zarz import ZarzDeezerClient
from pathvalidate import sanitize_filepath
from ..utils.hosts import DEEZER_MUSIC_HOSTS
from ..utils.deezerutils import DeezerMusicClientUtils
from urllib.parse import urlencode, urlparse, urljoin, parse_qs
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, usedownloadheaderscookies, safeextractfromdict, extractdurationsecondsfromlrc, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, SongInfoUtils, LyricSearchClient, IOUtils


'''DeezerMusicClient'''
class DeezerMusicClient(BaseMusicClient):
    source = 'DeezerMusicClient'
    def __init__(self, **kwargs):
        kwargs['maintain_session'] = True
        super(DeezerMusicClient, self).__init__(**kwargs)
        if self.default_search_cookies: assert "arl" in self.default_search_cookies, '"arl" should be configured, refer to "https://musicdl.readthedocs.io/en/latest/Clients.html#deezermusicclient-built-in-premium-account"'
        if self.default_parse_cookies: assert "arl" in self.default_parse_cookies, '"arl" should be configured, refer to "https://musicdl.readthedocs.io/en/latest/Clients.html#deezermusicclient-built-in-premium-account"'
        if self.default_download_cookies: assert "arl" in self.default_download_cookies, '"arl" should be configured, refer to "https://musicdl.readthedocs.io/en/latest/Clients.html#deezermusicclient-built-in-premium-account"'
        self.default_search_headers = {
            'Pragma': 'no-cache', 'Origin': 'https://www.deezer.com', 'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-US,en;q=0.9', 'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:135.0) Gecko/20100101 Firefox/135.0', 'DNT': '1',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Accept': '*/*', 'Cache-Control': 'no-cache', 'X-Requested-With': 'XMLHttpRequest', 'Connection': 'keep-alive', 'Referer': 'https://www.deezer.com/login', 
        }
        self.default_parse_headers = {
            'Pragma': 'no-cache', 'Origin': 'https://www.deezer.com', 'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-US,en;q=0.9', 'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:135.0) Gecko/20100101 Firefox/135.0', 'DNT': '1',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Accept': '*/*', 'Cache-Control': 'no-cache', 'X-Requested-With': 'XMLHttpRequest', 'Connection': 'keep-alive', 'Referer': 'https://www.deezer.com/login', 
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers; self.auth_info = {}
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0, auto_supplement_song: bool = True):
        if DeezerMusicClientUtils.IS_ENCRYPTED_RPATTERN.search(song_info.download_url) is None: return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id, auto_supplement_song=auto_supplement_song)
        song_info = super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=[], progress=progress, song_progress_id=song_progress_id, auto_supplement_song=False)[0]
        output_filepath = (output_filepath := Path(song_info.save_path)).parent / f'{output_filepath.stem}.decrypt'
        blowfish_key = DeezerMusicClientUtils.generateblowfishkey(str(song_info.raw_data.get('id')))
        DeezerMusicClientUtils.decryptdownloadedaudiofile(src_path=str(song_info.save_path), dst_path=str(output_filepath), blowfish_key=blowfish_key)
        IOUtils.replacefile(str(output_filepath), str(song_info.save_path))
        downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(song_info, logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else song_info)
        return downloaded_song_infos
    '''_setauthinfo'''
    def _setauthinfo(self, request_overrides: dict = None):
        if self.auth_info and isinstance(self.auth_info, dict): return self.auth_info
        (resp := self.post('http://www.deezer.com/ajax/gw-light.php', params={'api_version': "1.0", 'api_token': 'null', 'input': '3', 'method': 'deezer.getUserData'}, **(request_overrides or {}))).raise_for_status()
        self.auth_info = resp2json(resp=resp)
        return self.auth_info
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}; self._setauthinfo(request_overrides=request_overrides)
        (default_rule := {'q': keyword, 'index': 1, 'limit': 20}).update(rule)
        # construct search urls
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'https://api.deezer.com/search/track?'
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['limit'] = page_size
            page_rule['index'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithmusicfabapi'''
    def _parsewithmusicfabapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result.get('id') or search_result.get('SNG_ID')), {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Content-Type": "application/json", "Accept": "application/json", "Referer": "https://musicfab.io/deezer-to-mp3/", "Origin": "https://musicfab.io"}
        # parse
        download_result, payload = self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides), {"url": f"https://www.deezer.com/en/track/{song_id}"}
        (resp := requests.post("https://musicfab.io/api/deezer", json=payload, headers=headers, timeout=20, **request_overrides)).raise_for_status(); download_result['track_details'] = resp2json(resp=resp)
        download_url = safeextractfromdict(download_result['track_details'], ['data', 'metadata', 'download'], '')
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['results', 'DURATION'], 0) or download_result.get('duration', 0) or 0)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'id': song_id}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['results', 'SNG_TITLE'], None) or download_result.get('title')), singers=legalizestring(safeextractfromdict(download_result, ['results', 'ART_NAME'], None) or safeextractfromdict(download_result, ['artist', 'name'], None)), album=legalizestring(safeextractfromdict(download_result, ['results', 'ALB_TITLE'], None) or safeextractfromdict(download_result, ['album', 'title'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=DeezerMusicClientUtils.getcoverurl(safeextractfromdict(download_result, ['results', 'ALB_PICTURE'], None)) or safeextractfromdict(download_result, ['album', 'cover_xl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithdeezdownloadersapi'''
    def _parsewithdeezdownloadersapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result.get('id') or search_result.get('SNG_ID')), {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "X-Requested-With": "XMLHttpRequest", "Referer": "https://deezdownloaders.com/"}
        # parse
        download_result, params, session = self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides), {"url": f"https://www.deezer.com/en/track/{song_id}"}, requests.Session()
        (resp := session.get("https://deezdownloaders.com/api/track.php", params=params, headers=headers, timeout=20, **request_overrides)).raise_for_status(); download_result['track_details'] = resp2json(resp=resp)
        data = {"name": download_result['track_details']['name'], "artist": download_result['track_details']['artist'], "url": f"https://www.deezer.com/en/track/{song_id}", "token": "none", "zip_download": "false", "quality": "128"}
        headers.update({'Referer': 'https://deezdownloaders.com/track.php', 'Origin': 'https://deezdownloaders.com', "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
        (resp := session.post("https://deezdownloaders.com/api/downloader.php", data=data, headers=headers, timeout=20, **request_overrides)).raise_for_status(); download_result['download'] = resp2json(resp=resp)
        download_url = safeextractfromdict(download_result['download'], ['dlink'], '')
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['results', 'DURATION'], 0) or download_result.get('duration', 0) or 0)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'id': song_id}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['results', 'SNG_TITLE'], None) or download_result.get('title')), singers=legalizestring(safeextractfromdict(download_result, ['results', 'ART_NAME'], None) or safeextractfromdict(download_result, ['artist', 'name'], None)), album=legalizestring(safeextractfromdict(download_result, ['results', 'ALB_TITLE'], None) or safeextractfromdict(download_result, ['album', 'title'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=DeezerMusicClientUtils.getcoverurl(safeextractfromdict(download_result, ['results', 'ALB_PICTURE'], None)) or safeextractfromdict(download_result, ['album', 'cover_xl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithantrahoshiapi'''
    def _parsewithantrahoshiapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result.get('id') or search_result.get('SNG_ID')), {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Origin": "https://antra.hoshi.cfd", "Referer": "https://antra.hoshi.cfd/"}
        accounts = [
            ('charlespikachubGFvd2FuZw==', 'charlespikachubGFvd2FuZzk2MDIxMg=='), ('charlespikachuZ2lybHNsb3ZldG9t', 'charlespikachuZ2lybHNsb3ZldG9tMTIzNDU2'), ('charlespikachuRXJpYw==', 'charlespikachucmFuZG9tOTk5'), ('charlespikachuZ3JlYXRtYW5hbnRyYQ==', 'charlespikachuZ3JlYXRtYW5hbnRyYQ=='), ('charlespikachuaWxpa2V0aGlzc2l0ZQ==', 'charlespikachuaWxpa2V0aGlzc2l0ZQ=='), 
            ('charlespikachubWFya2hlcmU=', 'charlespikachubWFya2hlcmU5OTk2NjY='), ('charlespikachubGFkeWdhZ2FmYW5z', 'charlespikachuMTIzNDU2Nzc2NTQzMjE='), ('charlespikachudGFsYXlvcg==', 'charlespikachudGFsYXlvcnRhbGF5b3I='), ('charlespikachuYnVzaW5lc3M=', 'charlespikachuYnVzaW5lc3M='), 
        ]
        decrypt_func = lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8')
        username, password = random.choice(accounts); username, password = decrypt_func(username), decrypt_func(password)
        # parse
        download_result = self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides); session = requests.Session(); session.headers.update(headers)
        (resp := session.post(f"https://antra.hoshi.cfd/api/auth/login", json={"username": username, "password": password,}, **request_overrides)).raise_for_status()
        (resp := session.post(f"https://antra.hoshi.cfd/api/resolve", json={"url": f"https://www.deezer.com/en/track/{song_id}", "format": "lossless-24",}, **request_overrides)).raise_for_status()
        (resp := session.post(f"https://antra.hoshi.cfd/api/jobs", json={"url": f"https://www.deezer.com/en/track/{song_id}", "format": "lossless-24", "start_index": 0, "end_index": 1,}, **request_overrides)).raise_for_status()
        job_id, max_retry_times, time_interval, status = resp2json(resp=resp)["job_id"], 120, 1, None
        for _ in range(max_retry_times):
            (resp := session.get(f"https://antra.hoshi.cfd/api/jobs/{job_id}/status", **request_overrides)).raise_for_status(); status = resp2json(resp=resp)
            if status.get("status") == "complete": break
            if status.get("status") in ("failed", "error"): raise RuntimeError(status)
            time.sleep(time_interval)
        else: raise TimeoutError(f"job timeout for parsing song id {song_id}")
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['results', 'DURATION'], 0) or download_result.get('duration', 0) or 0)
        (resp := session.get(f"https://antra.hoshi.cfd/api/jobs/{job_id}/download", **request_overrides)).raise_for_status()
        download_url_status: dict = {'ok': True, 'file_size_bytes': resp.content.__sizeof__(), 'file_size': SongInfoUtils.byte2mb(resp.content.__sizeof__()), 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content), 'download_url': f"https://antra.hoshi.cfd/api/jobs/{job_id}/download"}
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'id': song_id}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['results', 'SNG_TITLE'], None) or download_result.get('title')), singers=legalizestring(safeextractfromdict(download_result, ['results', 'ART_NAME'], None) or safeextractfromdict(download_result, ['artist', 'name'], None)), album=legalizestring(safeextractfromdict(download_result, ['results', 'ALB_TITLE'], None) or safeextractfromdict(download_result, ['album', 'title'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=DeezerMusicClientUtils.getcoverurl(safeextractfromdict(download_result, ['results', 'ALB_PICTURE'], None)) or safeextractfromdict(download_result, ['album', 'cover_xl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content,
        )
        song_info = SongInfo(source=self.source, raw_data={'id': song_id}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithflacdownloaderapi'''
    def _parsewithflacdownloaderapi(self, search_result: dict, request_overrides: dict = None):
        # init
        PREPARE_URL = "https://flacdownloader.com/prepare"; ASSET_URL = "https://flacdownloader.com/asset"
        request_overrides, song_id, headers = request_overrides or {}, str(search_result.get('id') or search_result.get('SNG_ID')), {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Accept": "application/json", "Referer": "https://flacdownloader.com/it/download"}
        # parse
        (resp := requests.get(PREPARE_URL, headers=headers, timeout=20, **request_overrides)).raise_for_status(); token = resp2json(resp=resp).get("t")
        download_result = self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Accept": "application/json", "Content-Type": "application/json", "Referer": "https://flacdownloader.com/it/download", "X-Dl-Token": token,}
        payload = {
            "url": f"https://www.deezer.com/track/{song_id}", "title": safeextractfromdict(download_result, ['results', 'SNG_TITLE'], None) or download_result.get('title'),
            "artist": safeextractfromdict(download_result, ['results', 'ART_NAME'], None) or safeextractfromdict(download_result, ['artist', 'name'], None), "format": "flac",
        }
        (resp := requests.post(ASSET_URL, headers=headers, json=payload, timeout=20, **request_overrides)).raise_for_status()
        download_result['track_details'] = resp2json(resp=resp); download_url = safeextractfromdict(download_result['track_details'], ['u'], '')
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['results', 'DURATION'], 0) or download_result.get('duration', 0) or 0)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'id': song_id}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['results', 'SNG_TITLE'], None) or download_result.get('title')), singers=legalizestring(safeextractfromdict(download_result, ['results', 'ART_NAME'], None) or safeextractfromdict(download_result, ['artist', 'name'], None)), album=legalizestring(safeextractfromdict(download_result, ['results', 'ALB_TITLE'], None) or safeextractfromdict(download_result, ['album', 'title'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=DeezerMusicClientUtils.getcoverurl(safeextractfromdict(download_result, ['results', 'ALB_PICTURE'], None)) or safeextractfromdict(download_result, ['album', 'cover_xl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithdeemixerapi'''
    def _parsewithdeemixerapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result.get('id') or search_result.get('SNG_ID')), {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36", "Referer": "https://deemixer.com/", "Origin": "https://deemixer.com"}
        # parse
        download_result, MUSIC_QUALITIES = self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides), ['FLAC', '320', '128']
        for music_quality in MUSIC_QUALITIES:
            payload = {"temp_id": str(uuid.uuid4()), "link": f"https://www.deezer.com/track/{song_id}", "bitrate": music_quality}
            (resp := requests.post("https://deemixer.com/process", json=payload, headers=headers, timeout=10, **request_overrides)).raise_for_status()
            download_result['track_details'] = resp2json(resp=resp); download_url = urljoin('https://deemixer.com/', safeextractfromdict(download_result['track_details'], ['download_url'], ''))
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['results', 'DURATION'], 0) or download_result.get('duration', 0) or 0)
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'id': song_id}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['results', 'SNG_TITLE'], None) or download_result.get('title')), singers=legalizestring(safeextractfromdict(download_result, ['results', 'ART_NAME'], None) or safeextractfromdict(download_result, ['artist', 'name'], None)), album=legalizestring(safeextractfromdict(download_result, ['results', 'ALB_TITLE'], None) or safeextractfromdict(download_result, ['album', 'title'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=DeezerMusicClientUtils.getcoverurl(safeextractfromdict(download_result, ['results', 'ALB_PICTURE'], None)) or safeextractfromdict(download_result, ['album', 'cover_xl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithzarzapi'''
    def _parsewithzarzapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, client = request_overrides or {}, str(search_result.get('id') or search_result.get('SNG_ID')), ZarzDeezerClient()
        # parse
        download_url = safeextractfromdict((download_result := client.getdownloadinfo(song_id, request_overrides=request_overrides)), ['url'], '')
        download_result['meta_info'] = self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides)
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['raw', 'duration'], 0) or 0)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'id': song_id}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['raw', 'title'], None)), singers=legalizestring(safeextractfromdict(download_result, ['raw', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['meta_info', 'album', 'title'], None)), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['meta_info', 'album', 'cover_xl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies: return SongInfo(source=self.source)
        l1_parser_funcs = [self._parsewithantrahoshiapi, self._parsewithzarzapi, ] # vip accounts
        l2_parser_funcs = [self._parsewithflacdownloaderapi, self._parsewithdeemixerapi, ] # vip accounts but unstable
        l3_parser_funcs = [self._parsewithmusicfabapi, ] # free accounts
        l4_parser_funcs = [self._parsewithdeezdownloadersapi, ] # free accounts but unstable
        for parser_func in (l1_parser_funcs + l2_parser_funcs + l3_parser_funcs + l4_parser_funcs):
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_getsongmetainfo'''
    def _getsongmetainfo(self, song_id, request_overrides: dict = None):
        request_overrides, resp = request_overrides or {}, None
        with suppress(Exception): (resp := self.post('http://www.deezer.com/ajax/gw-light.php', params={'api_version': "1.0", 'api_token': safeextractfromdict(self.auth_info, ['results', 'checkForm'], None), 'input': '3', 'method': 'song.getData'}, json={'SNG_ID': song_id}, **request_overrides)).raise_for_status()
        if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or safeextractfromdict((song_detail := resp2json(resp=resp)), ['error'], None): (resp := self.get(f'https://api.deezer.com/track/{song_id}', **request_overrides)).raise_for_status(); song_detail = resp2json(resp=resp)
        return song_detail
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, is_fallback_retry: bool = False, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source); self._setauthinfo(request_overrides=request_overrides)
        if (not isinstance(search_result, dict)) or (not (song_id := (search_result.get('id') or search_result.get('SNG_ID')))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            # --get track details
            download_result = self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides)
            # --get some necessary information for music parse
            license_token, track_token = safeextractfromdict(self.auth_info, ['results', 'USER', 'OPTIONS', 'license_token'], None), safeextractfromdict(download_result, ['results', 'TRACK_TOKEN'], None) or download_result.get('track_token')
            fallback_song_id = safeextractfromdict(download_result, ['results', 'FALLBACK', 'SNG_ID'], None) or safeextractfromdict(download_result, ['fallback', 'sng_id'], None) or safeextractfromdict(download_result, ['fallback', 'id'], None)
            # --music parse from high to low qualities
            for music_quality in (DeezerMusicClientUtils.MUSIC_QUALITIES if (license_token and track_token) else []):
                with suppress(Exception): resp = None; (resp := self.post("https://media.deezer.com/v1/get_url", json={'license_token': license_token, 'media': [{'type': "FULL", "formats": [{"cipher": "BF_CBC_STRIPE", "format": music_quality}]}], 'track_tokens': [track_token,]}, **request_overrides)).raise_for_status()
                if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                download_result['track_details'] = resp2json(resp=resp); candidate_results = safeextractfromdict(download_result['track_details'], ['data', 0, 'media', 0, 'sources'], []) or []
                for candidate_result in [c for c in candidate_results if isinstance(c, dict) and c.get('url') and str(c.get('url')).startswith('http')]:
                    with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['results', 'DURATION'], 0) or download_result.get('duration', 0) or 0)
                    download_url_status: dict = self.audio_link_tester.test(url=candidate_result['url'], request_overrides=request_overrides, renew_session=True)
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'id': song_id}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['results', 'SNG_TITLE'], None) or download_result.get('title')), singers=legalizestring(safeextractfromdict(download_result, ['results', 'ART_NAME'], None) or safeextractfromdict(download_result, ['artist', 'name'], None)), album=legalizestring(safeextractfromdict(download_result, ['results', 'ALB_TITLE'], None) or safeextractfromdict(download_result, ['album', 'title'], None)), 
                        ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=DeezerMusicClientUtils.getcoverurl(safeextractfromdict(download_result, ['results', 'ALB_PICTURE'], None)) or safeextractfromdict(download_result, ['album', 'cover_xl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                    )
                    if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                    if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
            # --fallback id retry if possible
            if (not song_info.with_valid_download_url) and (not is_fallback_retry) and fallback_song_id: return self._parsewithofficialapiv1(search_result={'id': fallback_song_id}, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, lossless_quality_definitions=lossless_quality_definitions, is_fallback_retry=True, request_overrides=request_overrides)
            # --use preview audio link
            if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS:
                download_url = safeextractfromdict(download_result, ['results', 'MEDIA', 0, 'HREF'], None) or download_result.get('preview')
                with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['results', 'DURATION'], 0) or download_result.get('duration', 0) or 0)
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'id': song_id}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['results', 'SNG_TITLE'], None) or download_result.get('title')), singers=legalizestring(safeextractfromdict(download_result, ['results', 'ART_NAME'], None) or safeextractfromdict(download_result, ['artist', 'name'], None)), album=legalizestring(safeextractfromdict(download_result, ['results', 'ALB_TITLE'], None) or safeextractfromdict(download_result, ['album', 'title'], None)), 
                    ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=DeezerMusicClientUtils.getcoverurl(safeextractfromdict(download_result, ['results', 'ALB_PICTURE'], None)) or safeextractfromdict(download_result, ['album', 'cover_xl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        try: (resp := self.post('https://auth.deezer.com/login/renew?jo=p&rto=c&i=c', **request_overrides)).raise_for_status(); headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Origin": "https://www.deezer.com", "Referer": "https://www.deezer.com/", "Authorization": f"Bearer {resp2json(resp=resp)['jwt']}"}; payload = {"operationName": "GetLyrics", "variables": {"trackId": str(song_id)}, "query": "query GetLyrics($trackId: String!) { track(trackId: $trackId) { id lyrics { id text ...SynchronizedWordByWordLines ...SynchronizedLines licence copyright writers __typename } __typename } } fragment SynchronizedWordByWordLines on Lyrics { id synchronizedWordByWordLines { start end words { start end word __typename } __typename } __typename } fragment SynchronizedLines on Lyrics { id synchronizedLines { lrcTimestamp line lineTranslated milliseconds duration __typename } __typename }"}; (resp := requests.post("https://pipe.deezer.com/api", headers=headers, json=payload, **request_overrides)).raise_for_status(); lyric_result = resp2json(resp=resp); lyric = cleanlrc(DeezerMusicClientUtils.covert2lrclyrics(lyric_result['data']['track']['lyrics']) or '')
        except Exception: lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, lossless_quality_is_sufficient = request_overrides or {}, False if self.default_cookies or request_overrides.get('cookies') else True; self._setauthinfo(request_overrides=request_overrides)
        page_no, search_result_idx = int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('index')[0])), -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp=resp)['data']):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
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
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, DEEZER_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, page_size, playlist_result_first = [], 1, 500, {}; self._setauthinfo(request_overrides=request_overrides)
        while True:
            payload = {'playlist_id': playlist_id, 'start': (page - 1) * page_size, 'tab': 0, 'header': True, 'lang': 'de', 'nb': page_size}
            with suppress(Exception): (resp := self.post(f"https://www.deezer.com/ajax/gw-light.php?method=deezer.pagePlaylist&input=3&api_version=1.0&api_token={safeextractfromdict(self.auth_info, ['results', 'checkForm'], None)}", json=payload, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['results', 'SONGS', 'data'], [])): (resp := self.get(f'https://api.deezer.com/playlist/{playlist_id}', **request_overrides)).raise_for_status()
            tracks_per_page = safeextractfromdict((playlist_result := resp2json(resp=resp)), ['results', 'SONGS', 'data'], []) or safeextractfromdict(playlist_result, ['tracks', 'data'], [])
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not tracks_per_page): break
            tracks_in_playlist.extend(tracks_per_page); page += 1; del resp
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['results', 'DATA', 'NB_SONG'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["SNG_ID"]: d for d in tracks_in_playlist}.values()) if 'SNG_ID' in tracks_in_playlist[0] else list({d["id"]: d for d in tracks_in_playlist}.values())
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}})
                song_info_flac = self._parsewiththirdpartapis(search_result=track_info, request_overrides=request_overrides)
                lossless_quality_is_sufficient = False if self.default_cookies or request_overrides.get('cookies') else True
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                if (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse track info {track_info}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['results', 'DATA', 'TITLE'], None) or safeextractfromdict(playlist_result_first, ['title'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos