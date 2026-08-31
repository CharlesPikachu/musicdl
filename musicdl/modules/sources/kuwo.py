'''
Function:
    Implementation of KuwoMusicClient: http://www.kuwo.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import time
import html
import random
import base64
import warnings
import requests
from bs4 import BeautifulSoup
from contextlib import suppress
from typing_extensions import Unpack
from pathvalidate import sanitize_filepath
from ..utils.hosts import KUWO_MUSIC_HOSTS
from ..utils.kuwoutils import KuwoMusicClientUtils
from urllib.parse import urlencode, urlparse, parse_qs
from .base import BaseMusicClient, BaseMusicClientKwargs
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils
warnings.filterwarnings('ignore')


'''KuwoMusicClient'''
class KuwoMusicClient(BaseMusicClient):
    source = 'KuwoMusicClient'
    MUSIC_QUALITIES = [(22000, 'flac'), (320, 'mp3')] # playable flac and mp3 formats
    ENC_MUSIC_QUALITIES = [(4000, '4000kflac'), (2000, '2000kflac'), (320, '320kmp3'), (192, '192kmp3'), (128, '128kmp3')] # encrypted mgg format
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(KuwoMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_download_headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_parse_headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"vipver": "1", "client": "kt", "ft": "music", "cluster": "0", "strategy": "2012", "encoding": "utf8", "rformat": "json", "mobi": "1", "issubtitle": "1", "show_copyright_off": "1", "pn": "0", "rn": "10", "all": keyword}).update(rule)
        # construct search urls
        base_url, search_urls, page_size, count = 'http://www.kuwo.cn/search/searchMusicBykeyWord?', [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['rn'] = page_size
            page_rule['pn'] = str(int(count // page_size))
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithccwuapi'''
    def _parsewithccwuapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_'), SongInfo(source=self.source)
        # parse
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", 'Cookie': 'techaro.lol-anubis-auth-e2249c5d=eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhY3Rpb24iOiJDSEFMTEVOR0UiLCJjaGFsbGVuZ2UiOiIwMWEwNThkMS00MGQwLTcyZTctOTNiYi1iMjBiMGM0ODljZGMiLCJleHAiOjE3ODg4MDEzMDcsImlhdCI6MTc4ODE5NjUwNywibWV0aG9kIjoiZmFzdCIsIm5iZiI6MTc4ODE5NjQ0NywicG9saWN5UnVsZSI6ImY4OTkwNTM3ZWFlM2NiMzQiLCJyZXN0cmljdGlvbiI6IjUzNWY2ZTEyMTY4MDc2NDE2MDY0M2I1ZmQxZWE5MTVmMTQ5ZDZkNDIyZWRiZjkwOTgxMDEwZThlYTM3ODFmZTcifQ.WXfJ8LP6AGuye5FBGlIgszz52VK0ypLKu_34EtYu61l04XADvXC62iuR-asSuKhWiSY_HXjitpC0TpIu3SfvDQ'}
        (resp := requests.get(f'http://kw.006lp.ccwu.cc:7119/api/song?id={song_id}&level=lossless&stream=0', timeout=10, headers=headers, verify=False, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], None)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
            identifier=song_id, duration_s=safeextractfromdict(download_result, ['data', 'duration'], None), duration=SongInfoUtils.seconds2hms(safeextractfromdict(download_result, ['data', 'duration'], None)), lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lyrics'], None) or 'NULL'), cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithyyy001api'''
    def _parsewithyyy001api(self, search_result: dict, request_overrides: dict = None):
        # init
        REQUEST_KEYS = ['charlespikachuU2hhbmhhaS11RENkUGhoQ2xlUmd2WFh5bFFCbHFQVHMyb3RtSGNQbFJ5UWdvdlRsbW8wMDRyZko=', 'charlespikachuU2hhbmhhaS0yYlBxOUJFcFV5ZUtENGNESGc0MHp3Nzl6UDN1SkhqalNTS2hCekpYRVpxakdTbzE=', 'charlespikachuU2hhbmhhaS1XenJBNlFWS2N5RlExYk5aemRSZ1NpVHVhR1Z6N21ET29GamVEM0FvS3NGUlFtZ2M=']
        MUSIC_QUALITIES, decrypt_func = ["ff", "p", "h"], lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8')
        request_overrides, song_id = request_overrides or {}, str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_')
        if not (search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        for music_quality in MUSIC_QUALITIES:
            resp = next((resp for _ in range(5) if (resp := requests.get(f"https://apione.apibyte.cn/kwmusic?key={decrypt_func(random.choice(REQUEST_KEYS))}&action=music_url&music_id={song_id}&quality={music_quality}", timeout=10, headers=headers, **request_overrides)).json()['code'] in {'200', 200} or (time.sleep(1) or False)), None)
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            duration_in_secs = int(float(search_result.get('DURATION') or search_result.get('duration') or 0))
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')), singers=legalizestring(search_result.get('ARTIST') or search_result.get('artist')), album=legalizestring(search_result.get('ALBUM') or search_result.get('album')), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('hts_MVPIC') or search_result.get('albumpic') or search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': download_result, 'lyric': {}}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithlxmusicapi'''
    def _parsewithlxmusicapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_')
        headers = {'Content-Type': 'application/json', 'User-Agent': 'lx-music-request/2.6.0', 'X-Request-Key': 'share-v3'}
        if not (search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        (resp := requests.get(f"https://lxmusicapi.onrender.com/url/kw/{song_id}/flac", headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['url']) or not str(download_url).startswith('http'): return SongInfo(source=self.source)
        duration_in_secs = int(float(search_result.get('DURATION') or search_result.get('duration') or 0))
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')), singers=legalizestring(search_result.get('ARTIST') or search_result.get('artist')), album=legalizestring(search_result.get('ALBUM') or search_result.get('album')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('hts_MVPIC') or search_result.get('albumpic') or search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithxcloudvapi'''
    def _parsewithxcloudvapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_')
        headers = {'Origin': 'https://music.xcloudv.top', 'Referer': 'https://music.xcloudv.top/', 'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'}
        if not (search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        (resp := requests.post("https://music.xcloudv.top/php/kuwo_backup_source.php", data={"action": "url", "songid": song_id, "yz": "5"}, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['url']) or not str(download_url).startswith('http'): return SongInfo(source=self.source)
        duration_in_secs = int(float(search_result.get('DURATION') or search_result.get('duration') or 0))
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')), singers=legalizestring(search_result.get('ARTIST') or search_result.get('artist')), album=legalizestring(search_result.get('ALBUM') or search_result.get('album')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('hts_MVPIC') or search_result.get('albumpic') or search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithnxinxzapi'''
    def _parsewithnxinxzapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, MUSIC_QUALITIES = request_overrides or {}, str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_'), ['lossless', 'exhigh', 'standard']
        if not (search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(f"http://music.nxinxz.com/kw.php?id={song_id}&level={music_quality}&type=json", headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            duration_in_secs = int(float(search_result.get('DURATION') or search_result.get('duration') or 0))
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')), singers=legalizestring(search_result.get('ARTIST') or search_result.get('artist')), album=legalizestring(search_result.get('ALBUM') or search_result.get('album')), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('hts_MVPIC') or search_result.get('albumpic') or search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': download_result, 'lyric': {}}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithhaitangwapi'''
    def _parsewithhaitangwapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, MUSIC_QUALITIES = request_overrides or {}, str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_'), ['lossless', 'exhigh', 'standard']
        if not (search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(f"https://musicapi.haitangw.net/music/kw.php?id={song_id}&level={music_quality}&type=json", headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            duration_in_secs = int(float(search_result.get('DURATION') or search_result.get('duration') or 0))
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')), singers=legalizestring(search_result.get('ARTIST') or search_result.get('artist')), album=legalizestring(search_result.get('ALBUM') or search_result.get('album')), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('hts_MVPIC') or search_result.get('albumpic') or search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': download_result, 'lyric': {}}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithgdstudioapi'''
    def _parsewithgdstudioapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_')
        if not (search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        (resp := requests.get(f"https://music-api.gdstudio.xyz/api.php?types=url&id={song_id}&source=kuwo&br=999", headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['url']) or not str(download_url).startswith('http'): return SongInfo(source=self.source)
        duration_in_secs = int(float(search_result.get('DURATION') or search_result.get('duration') or 0))
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')), singers=legalizestring(search_result.get('ARTIST') or search_result.get('artist')), album=legalizestring(search_result.get('ALBUM') or search_result.get('album')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('hts_MVPIC') or search_result.get('albumpic') or search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        l1_parser_funcs = [self._parsewithccwuapi, ] # svip
        l2_parser_funcs = [self._parsewithnxinxzapi, self._parsewithhaitangwapi, self._parsewithxcloudvapi, ] # vip
        l3_parser_funcs = [self._parsewithlxmusicapi, self._parsewithyyy001api, self._parsewithgdstudioapi, ][:0] # invalid or unstable accounts
        for parser_func in (l1_parser_funcs + l2_parser_funcs + l3_parser_funcs):
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
        song_info, request_overrides, song_info_flac, song_id = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source), str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_')
        if not isinstance(search_result, dict) or (not (search_result.get('MUSICRID') or search_result.get('musicrid'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            if not (search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
            for music_quality in KuwoMusicClient.MUSIC_QUALITIES:
                query = f"user=0&corp=kuwo&source=kwplayer_ar_5.1.0.0_B_jiakong_vh.apk&p2p=1&type=convert_url2&sig=0&format={music_quality[1]}&rid={song_id}"
                with suppress(Exception): (resp := self.get(f"http://mobi.kuwo.cn/mobi.s?f=kuwo&q={KuwoMusicClientUtils.encryptquery(query)}", headers={"user-agent": "okhttp/3.10.0"}, **request_overrides)).raise_for_status()
                if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                if not (download_url := re.search(r'http[^\s$\"]+', (download_result := resp.text))) or not ((download_url := download_url.group(0)).startswith('http')): continue
                duration_in_secs = int(float(search_result.get('DURATION') or search_result.get('duration') or 0))
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True); del resp
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('SONGNAME') or search_result.get('name') or search_result.get('songName')), singers=legalizestring(search_result.get('ARTIST') or search_result.get('artist')), album=legalizestring(search_result.get('ALBUM') or search_result.get('album')), ext=download_url_status['ext'], 
                    file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('hts_MVPIC') or search_result.get('albumpic') or search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        encoded_params = KuwoMusicClientUtils.buildlyricsparams(song_id, True)
        with suppress(Exception): (resp := self.get(f"http://newlyric.kuwo.cn/newlyric.lrc?{encoded_params}", **request_overrides)).raise_for_status(); song_info.lyric = cleanlrc(KuwoMusicClientUtils.convertrawlrc(KuwoMusicClientUtils.decodelyrics(resp.content, True))) or song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, lossless_quality_is_sufficient = request_overrides or {}, False if self.default_cookies or request_overrides.get('cookies') else True
        page_no, search_result_idx = int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('pn')[0]) + 1), -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp)['abslist']):
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
        with suppress(Exception): playlist_id, song_infos = parse_qs(urlparse(playlist_url).query, keep_blank_values=False).get('id')[0], []
        if not playlist_id: playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, KUWO_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, playlist_result_first = [], 1, {}
        while True:
            with suppress(Exception): (resp := self.get(f"https://m.kuwo.cn/newh5app/wapi/api/www/playlist/playListInfo?pid={playlist_id}&pn={page}&rn=100", **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['data', 'musicList'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['data', 'musicList'], [])); page += 1; del resp
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['data', 'total'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["musicrid"]: d for d in tracks_in_playlist}.values())
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
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['data', 'name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos