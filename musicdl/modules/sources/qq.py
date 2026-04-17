'''
Function:
    Implementation of QQMusicClient: https://y.qq.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import json
import random
import base64
from contextlib import suppress
from typing import TYPE_CHECKING
from .base import BaseMusicClient
from rich.progress import Progress
from ..utils.hosts import QQ_MUSIC_HOSTS
from pathvalidate import sanitize_filepath
from urllib.parse import urlparse, parse_qs, urljoin
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils.qqutils import QQMusicClientUtils, SearchType, Credential, ThirdPartVKeysAPISongFileType, SongFileType, EncryptedSongFileType
from ..utils import resp2json, legalizestring, safeextractfromdict, usesearchheaderscookies, extractdurationsecondsfromlrc, useparseheaderscookies, obtainhostname, hostmatchessuffix, optionalimport, cleanlrc, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils


'''QQMusicClient'''
class QQMusicClient(BaseMusicClient):
    source = 'QQMusicClient'
    def __init__(self, use_encrypted_endpoint: bool = False, **kwargs):
        super(QQMusicClient, self).__init__(**kwargs)
        self.use_encrypted_endpoint = use_encrypted_endpoint
        self.default_search_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36', 'Referer': 'https://y.qq.com/', 'Origin': 'https://y.qq.com/',}
        self.default_parse_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36', 'Referer': 'https://y.qq.com/', 'Origin': 'https://y.qq.com/',}
        self.default_download_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36', 'Referer': 'http://y.qq.com',}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'searchid': QQMusicClientUtils.randomsearchid(), 'query': keyword, 'search_type': SearchType.SONG.value, 'num_per_page': self.search_size_per_page, 'page_num': 1, 'highlight': 1, 'grp': 1}).update(rule)
        # construct search urls
        base_url, search_urls, page_size, count = QQMusicClientUtils.enc_endpoint if self.use_encrypted_endpoint else QQMusicClientUtils.endpoint, [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['num_per_page'] = page_size
            page_rule['page_num'] = int(count // page_size) + 1
            payload = QQMusicClientUtils.buildrequestdata(params=page_rule, module="music.search.SearchCgiService", method="DoSearchForQQMusicMobile", credential=Credential().fromcookiesdict(self.default_cookies or request_overrides.get('cookies', {})))
            search_urls.append({'url': base_url, 'data': json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")})
            if self.use_encrypted_endpoint: search_urls[-1]['params'] = {"sign": QQMusicClientUtils.sign(payload)}
            count += page_size
        # return
        return search_urls
    '''_parsewithvkeysapi'''
    def _parsewithvkeysapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result.get('mid') or search_result.get('songmid')
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse download result
        for music_quality in list(ThirdPartVKeysAPISongFileType.ID_TO_NAME.value.keys())[::-1]:
            with suppress(Exception): resp = None; (resp := self.get(f"https://api.vkeys.cn/v2/music/tencent/geturl?mid={song_id}&quality={music_quality}", timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], None)) or not str(download_url).startswith('http'): continue
            duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['data', 'interval'], '0') or '0')
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'song'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'singer'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        with suppress(Exception): resp = None; (resp := self.get(f"https://api.vkeys.cn/v2/music/tencent/lyric?mid={song_id}", timeout=10, **request_overrides)).raise_for_status()
        lyric_result, lyric = ({}, 'NULL') if (not locals().get('resp') or not hasattr(locals().get('resp'), 'text')) else ((lyric_result := resp2json(resp=resp)), cleanlrc(safeextractfromdict(lyric_result, ['data', 'lrc'], '')))
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_parsewithxcvtsapi'''
    def _parsewithxcvtsapi(self, search_result: dict, request_overrides: dict = None):
        # init
        REQUEST_KEYS, decrypt_func = ['Nzg5OTMzNDRiOWJmMTEwNTY1NTU5OTAwOWNkYmEzZDI=',], lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        MUSIC_QUALITIES = ["臻品母带", "臻品全景声", "臻品2.0", "SQ无损", "HQ高品质", "中品质", "普通", "低品质", "试听"]
        request_overrides, song_id = request_overrides or {}, search_result.get('mid') or search_result.get('songmid')
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(f"https://api.xcvts.cn/api/music/qq?apiKey={decrypt_func(random.choice(REQUEST_KEYS))}&mid={song_id}&type={music_quality}", timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'music'], None)) or not str(download_url).startswith('http'): continue
            lyric = cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or 'NULL')
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'title'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'singer'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album_name'], None)), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=extractdurationsecondsfromlrc(lyric), duration=SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(lyric)), lyric=lyric, cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # return
        return song_info
    '''_parsewithluoyueapi'''
    def _parsewithluoyueapi(self, search_result: dict, request_overrides: dict = None):
        # init
        MUSIC_QUALITIES, request_overrides, song_id = ["flac24bit", "hires", "flac", "320k"], request_overrides or {}, search_result.get('mid') or search_result.get('songmid')
        headers = {"Content-Type": "application/json", "User-Agent": "lx-music-request/2.6.0", "X-Request-Key": "lxmusic"}
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(f"http://220.167.101.253:6001/api/musics/url/tx/{song_id}/{music_quality}", headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data'], None)) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or search_result.get('songname')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=int(float(search_result.get('interval', 0) or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('interval', 0) or 0))), lyric=None, cover_url=f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{safeextractfromdict(search_result, ['album', 'mid'], '') or search_result.get('albummid')}.jpg", download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # return
        return song_info
    '''_parsewithhuibqapi'''
    def _parsewithhuibqapi(self, search_result: dict, request_overrides: dict = None):
        # init
        MUSIC_QUALITIES, request_overrides, song_id = ["flac24bit", "hires", "flac", "320k"], request_overrides or {}, search_result.get('mid') or search_result.get('songmid')
        headers = {"Content-Type": "application/json", "User-Agent": "lx-music-request/2.6.0", "X-Request-Key": "share-v3"}
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(f"https://lxmusicapi.onrender.com/url/tx/{song_id}/{music_quality}", headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], None)) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or search_result.get('songname')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=int(float(search_result.get('interval', 0) or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('interval', 0) or 0))), lyric=None, cover_url=f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{safeextractfromdict(search_result, ['album', 'mid'], '') or search_result.get('albummid')}.jpg", download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # return
        return song_info
    '''_parsewithnkiapi'''
    def _parsewithnkiapi(self, search_result: dict, request_overrides: dict = None):
        # init
        REQUEST_KEYS = ['MjhmZWNlOTI1NDM5YjA1Mjc5MmE5Nzk4OWM4NzBjZWQzODAzYTcxYzZiNTM0ZjcxZTVhNTMzMzhiMmQzMWVmOA==', 'YzRjNGY1ZmMzNmJhZDRjYWNiOTg4MzllMTRmZWE0MDI3N2IzNWVhMmViMWJhYmRhZDdiYmRlMTI4NDAwZjNiMQ==']
        decrypt_func, curl_cffi = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8'), optionalimport('curl_cffi')
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        if TYPE_CHECKING and curl_cffi is not None: import curl_cffi as curl_cffi
        # parse
        with suppress(Exception): resp = None; (resp := curl_cffi.requests.get(f'https://api.nki.pw/API/music_open_api.php?mid={song_id}&apikey={decrypt_func(random.choice(REQUEST_KEYS))}', timeout=10, impersonate="chrome131", verify=False, **request_overrides)).raise_for_status()
        if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): (resp := self.get(f'https://api.nki.pw/API/music_open_api.php?mid={song_id}&apikey={decrypt_func(random.choice(REQUEST_KEYS))}', timeout=10, **request_overrides)).raise_for_status()
        download_url: str = (download_result := resp2json(resp=resp)).get('song_play_url_sq') or download_result.get('song_play_url_pq') or download_result.get('song_play_url_accom') or download_result.get('song_play_url_hq') or download_result.get('song_play_url') or download_result.get('song_play_url_standard') or download_result.get('song_play_url_fq')
        if not download_url or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['duration'], '0') or '0')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('song_name')), singers=legalizestring(download_result.get('singer_name')), album=legalizestring(download_result.get('album_name')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(download_result.get('song_lyric', '') or ''), cover_url=download_result.get('album_pic'), 
            download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithtangapi'''
    def _parsewithtangapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse
        (resp := self.get(f'https://tang.api.s01s.cn/music_open_api.php?mid={song_id}', **request_overrides)).raise_for_status()
        download_url: str = (download_result := resp2json(resp=resp)).get('song_play_url_sq') or download_result.get('song_play_url_pq') or download_result.get('song_play_url_accom') or download_result.get('song_play_url_hq') or download_result.get('song_play_url') or download_result.get('song_play_url_standard') or download_result.get('song_play_url_fq')
        if not download_url or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['duration'], '0') or '0')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('song_name')), singers=legalizestring(download_result.get('singer_name')), album=legalizestring(download_result.get('album_name')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(download_result.get('song_lyric', '') or ''), cover_url=download_result.get('album_pic'), 
            download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithxianyuwapi'''
    def _parsewithxianyuwapi(self, search_result: dict, request_overrides: dict = None):
        # init
        decrypt_func, REQUEST_KEYS = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8'), ['c2stNTI3OWY0MGQ3ODQxZDVmZDFlODEyZWRkMzRhODg4OTQ=', 'c2stNTVkNjE0MDY2NTk1NGU4ZjY2NTFmODNhMmQ2ZWYyNmU=']
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        # parse
        (resp := self.get(f'https://apii.xianyuw.cn/api/v1/qq-music-search?id={song_id}&key={decrypt_func(random.choice(REQUEST_KEYS))}&no_url=0&br=hires', **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['data']['url']) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        lyric = cleanlrc(safeextractfromdict(download_result, ['data', 'lrc'], '') or 'NULL')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'title'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'author'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None) or safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=extractdurationsecondsfromlrc(lyric), duration=SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(lyric)), lyric=lyric, cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status,
        )
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for parser_func in [self._parsewithxcvtsapi, self._parsewithvkeysapi, self._parsewithtangapi, self._parsewithluoyueapi, self._parsewithnkiapi, self._parsewithhuibqapi, self._parsewithxianyuwapi]:
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('mid') or search_result.get('songmid'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            # --non-vip / vip users using enc_endpoint
            if self.use_encrypted_endpoint:
                for music_quality in EncryptedSongFileType.SORTED_QUALITIES.value:
                    params = {"filename": [f"{music_quality[0]}{song_id}{song_id}{music_quality[1]}"], "guid": QQMusicClientUtils.randomguid(), "songmid": [song_id], 'songtype': [0]}
                    current_rule = QQMusicClientUtils.buildrequestdata(params=params, module="music.vkey.GetEVkey", method="CgiGetEVkey", credential=Credential().fromcookiesdict(self.default_cookies or request_overrides.get('cookies', {})), common_override={"ct": "19"})
                    with suppress(Exception): resp = None; (resp := self.post(QQMusicClientUtils.enc_endpoint, data=json.dumps(current_rule, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), params={"sign": QQMusicClientUtils.sign(current_rule)}, **request_overrides)).raise_for_status()
                    if not (download_url := safeextractfromdict((download_result := resp2json(resp)), ['music.vkey.GetEVkey.CgiGetEVkey', 'data', "midurlinfo", 0, "purl"], "") or safeextractfromdict(download_result, ['music.vkey.GetEVkey.CgiGetEVkey', 'data', "midurlinfo", 0, "wifiurl"], "")): continue
                    ekey = safeextractfromdict(download_result, ['music.vkey.GetEVkey.CgiGetEVkey', 'data', "midurlinfo", 0, "ekey"], "")
                    download_url_status: dict = self.audio_link_tester.test(url=(download_url := urljoin(QQMusicClientUtils.music_domain, download_url)), request_overrides=request_overrides, renew_session=True)
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'ekey': ekey}, source=self.source, song_name=legalizestring(search_result.get('title') or search_result.get('songname')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                        file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=int(float(search_result.get('interval', 0) or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('interval', 0) or 0))), lyric=None, cover_url=f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{safeextractfromdict(search_result, ['album', 'mid'], '') or search_result.get('albummid')}.jpg", download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                    )
                    if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                    if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
            # --non-vip / vip users using endpoint
            else:
                for music_quality in SongFileType.SORTED_QUALITIES.value:
                    params = {"filename": [f"{music_quality[0]}{song_id}{song_id}{music_quality[1]}"], "guid": QQMusicClientUtils.randomguid(), "songmid": [song_id], 'songtype': [0]}
                    current_rule = QQMusicClientUtils.buildrequestdata(params=params, module="music.vkey.GetVkey", method="UrlGetVkey", credential=Credential().fromcookiesdict(self.default_cookies or request_overrides.get('cookies', {})), common_override={"ct": "19"})
                    with suppress(Exception): resp = None; (resp := self.post(QQMusicClientUtils.endpoint, data=json.dumps(current_rule, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), **request_overrides)).raise_for_status()
                    if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                    if not (download_url := safeextractfromdict((download_result := resp2json(resp)), ['music.vkey.GetVkey.UrlGetVkey', 'data', "midurlinfo", 0, "purl"], "") or safeextractfromdict(download_result, ['music.vkey.GetVkey.UrlGetVkey', 'data', "midurlinfo", 0, "wifiurl"], "")): continue
                    download_url_status: dict = self.audio_link_tester.test(url=(download_url := urljoin(QQMusicClientUtils.music_domain, download_url)), request_overrides=request_overrides, renew_session=True)
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or search_result.get('songname')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                        file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=int(float(search_result.get('interval', 0) or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('interval', 0) or 0))), lyric=None, cover_url=f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{safeextractfromdict(search_result, ['album', 'mid'], '') or search_result.get('albummid')}.jpg", download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                    )
                    if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                    if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        (lyric_request_overrides := copy.deepcopy(request_overrides)).pop('headers', {}); lyric_result, lyric = {}, 'NULL'
        params = {'songmid': str(song_id), 'g_tk': '5381', 'loginUin': '0', 'hostUin': '0', 'format': 'json', 'inCharset': 'utf8', 'outCharset': 'utf-8', 'platform': 'yqq'}
        with suppress(Exception): (resp := self.get('https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg', headers={'Referer': 'https://y.qq.com/portal/player.html'}, params=params, **lyric_request_overrides)).raise_for_status(); lyric = cleanlrc(base64.b64decode((lyric_result := resp2json(resp)).get('lyric') or '').decode('utf-8'))
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = {}, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, lossless_quality_is_sufficient = request_overrides or {}, False if self.default_cookies or request_overrides.get('cookies') else True
        search_meta = copy.deepcopy(search_url); search_url = search_meta.pop('url')
        # successful
        try:
            # --search results
            (resp := self.post(search_url, **search_meta, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp)['music.search.SearchCgiService.DoSearchForQQMusicMobile']['data']['body']['item_song']:
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
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Error: {err})")
            self.logger_handle.error(f"{self.source}._search >>> {search_url} (Error: {err})", disable_print=self.disable_print)
        # return
        return song_infos
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        # init
        playlist_url, playlist_id = self.session.head(playlist_url, allow_redirects=True, **dict(request_overrides := request_overrides or {})).url, None
        with suppress(Exception): playlist_id, song_infos = parse_qs(urlparse(playlist_url).query, keep_blank_values=False).get('id')[0], []
        if not playlist_id: playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, QQ_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        (resp := self.get("https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg", headers={"Referer": f"https://y.qq.com/n/ryqq/playlist/{playlist_id}"}, params={"disstid": str(playlist_id), "type": "1", "json": "1", "utf8": "1", "onlysong": "0", "format": "json"}, **request_overrides)).raise_for_status()
        tracks_in_playlist = (safeextractfromdict((playlist_result := resp2json(resp=resp)), ['cdlist', 0, 'songlist'], []) or safeextractfromdict(playlist_result, ['cdlist', 0, 'list'], []) or safeextractfromdict(playlist_result, ['songlist'], []) or [])
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
                self.logger_handle.warning(f'Fail to parse song id {song_info.identifier} >>> {song_info.album} {song_info.song_name} {song_info.singers} {song_info.download_url}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result, ['cdlist', 0, 'dissname'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos