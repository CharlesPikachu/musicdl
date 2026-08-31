'''
Function:
    Implementation of BodianMusicClient: https://bodian.kuwo.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import uuid
import copy
import time
import json
import html
import random
import base64
import hashlib
import warnings
import requests
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from typing import Any, Dict, Tuple
from typing_extensions import Unpack
from pathvalidate import sanitize_filepath
from ..utils.hosts import BODIAN_MUSIC_HOST
from .base import BaseMusicClient, BaseMusicClientKwargs
from urllib.parse import urlencode, urlparse, parse_qs, unquote, quote
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils
warnings.filterwarnings('ignore')


'''BodianMusicClient'''
class BodianMusicClient(BaseMusicClient):
    source = 'BodianMusicClient'
    DEFAULT_MUSIC_QUALITY_ID = '6' # Actual testing shows that audio streams with higher bitrates than 2000k FLAC are in an encrypted state (DRM-protected)
    MUSIC_QUALITIES: Dict[str, Tuple[str, str]] = {"1": ("mp3", "128kmp3"), "2": ("mp3", "320kmp3"), "3": ("ogg", "100kogg"), "4": ("ogg", "192kogg"), "5": ("ogg", "300kogg"), "6": ("flac", "2000kflac"), "7": ("mflac", "20201kmflac"), "8": ("aac", "48kaac"), "9": ("mflac", "20501kmflac"), "10": ("mflac", "20900kmflac"), "11": ("mgg", "22000kmgg"), "12": ("zp", "20000kzp")}
    AUDIO_TO_MUSIC_QUALITY: Dict[Tuple[str, str], str] = {("mp3", "128"): "1", ("mp3", "320"): "2", ("ogg", "100"): "3", ("ogg", "192"): "4", ("ogg", "300"): "5", ("flac", "2000"): "6", ("mflac", "20201"): "7", ("aac", "48"): "8", ("mflac", "20501"): "9", ("mflac", "20900"): "10", ("mgg", "22000"): "11", ("zp", "20000"): "12"}
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(BodianMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"user-agent": "Dart/3.3 (dart:io)", "plat": "win", "accept-encoding": "gzip", "api-ver": "application/json", "channel": "W1", "brand": "Windows 11 Pro for Workstations", "net": "wifi", "content-type": "application/json", "ver": "1.1.5", "svrver": "13"}
        self.default_download_headers = {"user-agent": "Dart/3.3 (dart:io)", "plat": "win", "accept-encoding": "gzip", "api-ver": "application/json", "channel": "W1", "brand": "Windows 11 Pro for Workstations", "net": "wifi", "content-type": "application/json", "ver": "1.1.5", "svrver": "13"}
        self.default_parse_headers = {"user-agent": "Dart/3.3 (dart:io)", "plat": "win", "accept-encoding": "gzip", "api-ver": "application/json", "channel": "W1", "brand": "Windows 11 Pro for Workstations", "net": "wifi", "content-type": "application/json", "ver": "1.1.5", "svrver": "13"}
        self.auth_info = self.default_search_cookies or self.default_parse_cookies or self.default_download_cookies
        self.auth_info['uid'], self.auth_info['token'], self.auth_info['dev_id'] = self.auth_info.get("uid") or "-1", self.auth_info.get("token") or "", self.auth_info.get("dev_id") or hashlib.md5(uuid.uuid4().bytes).hexdigest()
        self.default_search_headers = {**self.default_search_headers, "devid": self.auth_info['dev_id'], "qimei36": self.auth_info['dev_id']}
        self.default_download_headers = {**self.default_download_headers, "devid": self.auth_info['dev_id'], "qimei36": self.auth_info['dev_id']}
        self.default_parse_headers = {**self.default_parse_headers, "devid": self.auth_info['dev_id'], "qimei36": self.auth_info['dev_id']}
        self.default_headers = self.default_search_headers; self.default_cookies = {}; self.default_search_cookies = {}; self.default_download_cookies = {}; self.default_parse_cookies = {}
        self._initsession()
    '''_signquery'''
    def _signquery(self, path: str, params: Dict[str, Any], body_text: str = "") -> str:
        seed = f"kuwotest{''.join(sorted(ch for ch in urlencode(params) if ch.isalnum()))}"
        if body_text: seed += hashlib.md5(f"{body_text}kuwotest".encode("utf-8")).hexdigest()
        return hashlib.md5(f"{seed}{path}".encode("utf-8")).hexdigest()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"pn": 0, "rn": 20, "keyword": keyword, "correct": "1", "uid": self.auth_info['uid'], "token": self.auth_info['token']}).update(rule)
        # construct search urls
        base_url, search_urls, page_size, count = 'https://bd-api.kuwo.cn/api/search/music/list?', [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['rn'] = page_size
            page_rule['pn'] = str(int(count // page_size))
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithtianbaoapi'''
    def _parsewithtianbaoapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source)
        if not (search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        headers = {"User-Agent": "Dart/2.19 (dart:io)", "plat": "ar", "channel": "aliopen"}
        api_url = f"https://mobi.kuwo.cn/mobi.s?f=web&user={random.randint(1000000, 10000000)}&source=kwplayerhd_ar_4.3.0.8_tianbao_T1A_qirui.apk&type=convert_url_with_sign&br=2000kflac&rid={song_id}"
        (resp := requests.get(api_url, headers=headers, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], None)
        duration_in_secs = int(float(safeextractfromdict(download_result, ['data', 'duration'], 0) or 0))
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name') or search_result.get('songName')), singers=legalizestring(search_result.get('artist')), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('albumPic') or search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithjiakongapi'''
    def _parsewithjiakongapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source)
        if not (search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        params = {"f": "web", "source": "kwplayercar_ar_6.0.0.9_B_jiakong_vh.apk", "type": "convert_url_with_sign", "rid": song_id, "br": '2000kflac', "user": random.randint(0, 4294967295), "loginUid": random.randint(0, 4294967295),}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "Accept": "*/*",}
        (resp := requests.get("https://nmobi.kuwo.cn/mobi.s", headers=headers, params=params, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], None)
        duration_in_secs = int(float(safeextractfromdict(download_result, ['data', 'duration'], 0) or 0))
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name') or search_result.get('songName')), singers=legalizestring(search_result.get('artist')), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('albumPic') or search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.auth_info.get('token'): return SongInfo(source=self.source)
        for parser_func in [self._parsewithjiakongapi, self._parsewithtianbaoapi, ]:
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_getsongmetainfo'''
    def _getsongmetainfo(self, song_id, request_overrides: dict = None):
        # init
        request_overrides, resp = request_overrides or {}, None
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # h5 api
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1", "Referer": f"https://m.kuwo.cn/yinyue/{song_id}", "Accept": "application/json, text/plain, */*"}
        with suppress(Exception): (resp := self.get("https://m.kuwo.cn/newh5/singles/songinfoandlrc", headers=headers, params={"musicId": song_id}, **request_overrides)).raise_for_status()
        if (song_detail := (safeextractfromdict(resp2json(resp=resp), ['data', 'songinfo'], {}) or {})) and song_detail.get('album') and song_detail.get('duration'): return song_detail
        # fallback to parse html page
        headers, resp = {"Referer": "https://www.kuwo.cn/", "Accept-Language": "zh-CN,zh;q=0.9"}, None
        with suppress(Exception): (resp := self.get(f"https://www.kuwo.cn/play_detail/{song_id}", headers=headers, **request_overrides)).raise_for_status()
        if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): return {}
        soup = BeautifulSoup((page_text := html.unescape(resp.text).replace(r"\u002F", "/")), "lxml")
        text_of_func = lambda selector, default=None: (tag.get_text(strip=True) if (tag := soup.select_one(selector)) else default)
        value_of_func = lambda selector, default=None: (tag.get("value", default) if (tag := soup.select_one(selector)) else default)
        cover_candidates = re.findall(r'https://img\d+\.kuwo\.cn/star/(?:albumcover|starheads)/[^"\'<>\s]+?\.jpg', page_text)
        duration_match = (re.search(r'songTimeMinutes:\s*"([^"]+)"', page_text) or re.search(r"duration:\s*(\d+)", page_text))
        duration = (duration_match.group(1) if ":" in duration_match.group(1) else f"{int(duration_match.group(1)) // 60:02d}:{int(duration_match.group(1)) % 60:02d}") if duration_match else ''
        return {'id': song_id, 'songName': value_of_func("#songinfo-name", None), 'artist': text_of_func("p.artist_name span.name", None), 'album': text_of_func("span.album_name", None), 'duration': to_seconds_func(duration), 'pic': next((url for url in cover_candidates if "/500/" in url), cover_candidates[-1] if cover_candidates else None)}
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if not isinstance(search_result, dict) or (not (song_id := search_result.get('id'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            free_sign, (fmt, br) = unquote(search_result.get("freeSign") or search_result.get("fsig") or ""), BodianMusicClient.MUSIC_QUALITIES[BodianMusicClient.DEFAULT_MUSIC_QUALITY_ID]
            # -- check right with freesign
            params = {"uid": self.auth_info['uid'], "token": self.auth_info['token'], "timestamp": str(int(time.time() * 1000)), "musicId": str(song_id), "freeSign": free_sign}
            payload = json.dumps({"musicId": song_id, "freeSign": free_sign}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            params["sign"] = self._signquery("/api/play/music/v2/checkRight", params, body_text=payload.decode("utf-8"))
            (resp := self.get('https://bd-api.kuwo.cn/api/play/music/v2/checkRight', params=params, data=payload, **request_overrides)).raise_for_status()
            # -- restricted to preview playback only
            if safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'status'], None) in {3, '3'}:
                download_url = safeextractfromdict(download_result, ['data', 'audition', 'https'], None) or safeextractfromdict(download_result, ['data', 'audition', 'car_url_https'], None) or safeextractfromdict(download_result, ['data', 'audition', 'url'], None) or safeextractfromdict(download_result, ['data', 'audition', 'car_url'], None)
                with suppress(Exception): duration_in_secs = 0; duration_in_secs = int(float(safeextractfromdict(download_result, ['data', 'audition', 'duration'], 0)))
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(search_result.get('artist')), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                    file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('albumPic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
            # -- access music files with your vip account
            else:
                params = {"uid": self.auth_info['uid'], "token": self.auth_info['token'], "timestamp": str(int(time.time() * 1000)), "devId": self.auth_info['dev_id'], "musicId": str(song_id), "format": fmt, "br": br, "freeSign": free_sign}
                payload = json.dumps({"devId": self.auth_info['dev_id'], "musicId": str(song_id), "format": fmt, "br": br, "freeSign": free_sign}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                params["sign"] = self._signquery("/api/play/music/v2/audioUrl", params, body_text=payload.decode("utf-8"))
                (resp := self.get('https://bd-api.kuwo.cn/api/play/music/v2/audioUrl', headers={"uid": self.auth_info['uid'], "token": self.auth_info['token']}, params=params, data=payload, **request_overrides)).raise_for_status()
                download_result.update(resp2json(resp=resp)); download_url = safeextractfromdict(download_result, ['data', 'audioHttpsUrl'], None) or safeextractfromdict(download_result, ['data', 'audioUrl'], None)
                with suppress(Exception): duration_in_secs = 0; duration_in_secs = int(float(safeextractfromdict(download_result, ['data', 'duration'], 0)))
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(search_result.get('artist')), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                    file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('albumPic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        make_q_func = lambda song_id: base64.b64encode(quote(f"type=lyric&req=2&lrcx=1&rid={song_id}&songname=&artist=&corp=kuwo&fromchannel=bodian", safe="=&").encode("utf-8")).decode("ascii")
        url = f"http://mlyric.kuwo.cn/mobi.s?f=bodian&q={make_q_func(song_id)}&uid={self.auth_info['uid']}&token={self.auth_info['token']}"
        with suppress(Exception): (resp := self.get(url, **request_overrides)).raise_for_status(); song_info.raw_data['lyric'] = resp2json(resp=resp); song_info.lyric = cleanlrc(re.sub(r"<-?\d+,-?\d+>", "", base64.b64decode(song_info.raw_data['lyric']['data']['content']).decode("utf-8", errors="replace"))) or song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, lossless_quality_is_sufficient = request_overrides or {}, False if self.auth_info.get('token') else True
        page_no, search_result_idx = int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('pn')[0]) + 1), -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp)['data']['resultList']):
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
        playlist_url, playlist_id = self.session.head(playlist_url, allow_redirects=True, **(request_overrides := dict(request_overrides or {}))).url, None
        with suppress(Exception): playlist_id, song_infos = ((q := parse_qs(urlparse(playlist_url).query)).get("playlistId") or q.get("playListId") or q.get("pid") or q.get("id"))[0], []
        if not playlist_id: playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, BODIAN_MUSIC_HOST)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, playlist_result_first, source_id = [], 1, {}, ((q := parse_qs(urlparse(playlist_url).query, keep_blank_values=True)).get("source") or q.get("sourceType"))[0]
        while True:
            params = {"source": str(source_id or "5"), "pn": str(page), "rn": "100", "uid": self.auth_info['uid'], "token": self.auth_info['token']}
            with suppress(Exception): (resp := self.get(f"https://bd-api.kuwo.cn/api/service/playlist/{playlist_id}/musicList", params=params, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['data', 'list'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['data', 'list'], [])); page += 1; del resp
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['data', 'total'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["id"]: d for d in tracks_in_playlist}.values())
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
        with suppress(Exception): resp = None; (resp := self.get(f"https://bd-api.kuwo.cn/api/service/playlist/info/{playlist_id}", params={"source": str(source_id), "uid": self.auth_info['uid'], "token": self.auth_info['token']}, **request_overrides)).raise_for_status(); playlist_result_first['meta'] = resp2json(resp=resp)
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['meta', 'data', 'name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos