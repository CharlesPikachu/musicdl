'''
Function:
    Implementation of SpotifyMusicClient: https://open.spotify.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import time
import base64
import random
import requests
from bs4 import BeautifulSoup
from contextlib import suppress
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from ..utils.hosts import SPOTIFY_MUSIC_HOSTS
from urllib.parse import urlparse, quote, urlunparse, urlencode, parse_qsl
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils.spotifyutils import SpotifyMusicClientPlaylistUtils, SpotifyMusicClientSearchUtils, SpotubeSecureClient
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, useparseheaderscookies, obtainhostname, hostmatchessuffix, extractdurationsecondsfromlrc, SongInfo, AudioLinkTester, LyricSearchClient, IOUtils, SongInfoUtils, RandomIPGenerator


'''SpotifyMusicClient'''
class SpotifyMusicClient(BaseMusicClient):
    source = 'SpotifyMusicClient'
    def __init__(self, **kwargs):
        super(SpotifyMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "Accept": "application/json", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://open.spotify.com/", "Origin": "https://open.spotify.com/"}
        self.default_parse_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "Accept": "application/json", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://open.spotify.com/", "Origin": "https://open.spotify.com/"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            search_urls.append({'api': SpotifyMusicClientSearchUtils.searchbykeyword, 'inputs': {'session': copy.deepcopy(self.session), 'query': keyword, 'limit': page_size, 'offset': count, 'rule': copy.deepcopy(rule), 'request_overrides': request_overrides}, 'page_no': int(count / page_size) + 1})
            count += page_size
        # return
        return search_urls
    '''_parsewithspotubedlapi'''
    def _parsewithspotubedlapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, str(search_result['id'])
        # parse
        download_result = SpotubeSecureClient().getdownloadflagfromspotify(f"https://open.spotify.com/track/{song_id}", 'v1', 'mp3', '320', request_overrides=request_overrides)
        download_url_status: dict = self.audio_link_tester.test(url=(download_url := download_result['flag']), request_overrides=request_overrides, renew_session=True)
        (resp := requests.get(download_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}, **request_overrides)).raise_for_status()
        if download_url_status['file_size'] in {'NULL'}: download_url_status['file_size_bytes'], download_url_status['file_size'] = resp.content.__sizeof__(), SongInfoUtils.byte2mb(resp.content.__sizeof__())
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['track_meta', 'data', 'name'], None)), singers=legalizestring(', '.join(safeextractfromdict(download_result, ['track_meta', 'data', 'artists'], []) or [])), album=legalizestring(safeextractfromdict(download_result, ['track_meta', 'data', 'album_name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
            identifier=song_id, duration_s=float(safeextractfromdict(download_result, ['track_meta', 'data', 'duration'], 0) or 0), duration=SongInfoUtils.seconds2hms(float(safeextractfromdict(download_result, ['track_meta', 'data', 'duration'], 0) or 0)), lyric=None, cover_url=safeextractfromdict(download_result, ['track_meta', 'data', 'cover_url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=self.default_download_headers,
        )
        # return
        return song_info
    '''_parsewithmusicfabapi'''
    def _parsewithmusicfabapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"origin": "https://musicfab.io", "referer": "https://musicfab.io/", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse
        (resp := requests.post('https://musicfab.io/api/spotify', json={"url": f"https://open.spotify.com/track/{song_id}"}, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'metadata', 'download'], None)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['data', 'metadata', 'duration'], '') or '0:00')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'metadata', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'metadata', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'metadata', 'album'], None) or safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'metadata', 'image'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers,
        )
        # return
        return song_info
    '''_parsewithchrisk772000api'''
    def _parsewithchrisk772000api(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"Origin": "https://chrisk772000.github.io", "Referer": "https://chrisk772000.github.io/", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "X-Rapidapi-Host": "spotify-music-mp3-downloader-api.p.rapidapi.com", "X-Rapidapi-Key": "30959fad4amsh1c04bfa7b0509a0p109597jsnbd8a575ffad7"}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse
        (resp := requests.get(f"https://spotify-music-mp3-downloader-api.p.rapidapi.com/download?link=https://open.spotify.com/track/{song_id}", headers=headers, timeout=10, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'medias', 0, 'url'], None)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['data', 'duration'], '') or '0:00')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'title'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'author'], None)), album=legalizestring(safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'thumbnail'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers,
        )
        # return
        return song_info
    '''_parsewithbmediamdapi'''
    def _parsewithbmediamdapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"Referer": "https://bmedia-md-downloads.netlify.app/music", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse
        (resp := requests.get(f"https://bmedia-md-downloads.netlify.app/api-proxy/spotify?url=https://open.spotify.com/track/{song_id}", headers=headers, timeout=10, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'download'], None)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['data', 'metadata', 'duration'], '') or '0:00')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'metadata', 'title'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'metadata', 'artist'], None)), album=legalizestring(safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'metadata', 'images'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers,
        )
        # return
        return song_info
    '''_parsewithrapidapi'''
    def _parsewithrapidapi(self, search_result: dict, request_overrides: dict = None):
        # init
        shared_keys = [
            "efdc9dead0msh3d6b04344364212p1e7029jsn40fd6cc8da39", "1162fa6edbmsh4e3ada3ee7a56eap10e77ajsn2a5e57cad3bc", "b956d6a526msh7b1a2a3662d09cdp11fa3djsn5b6cad23f10f", "53d36da411mshc55da25ad75d914p19c959jsnec7bf74dad86",
            "d44e6cbbffmsh4904ffce35d0541p157e2bjsn63f9db9e85db", "50b5f3b226msh0966c3a7bd972cap10e911jsn3c815d7d3627", "19712ae800msh39302756eeef1abp1b8019jsnc7967b2210ac", "2f5f8f1ed6msha939c8e6949b10ep16c31bjsnb07bb964bbbb",
            "97f21512b9mshbd44e421ed343a1p1a65b9jsn878d08ec3763", "907f71f2camshab357c69afa7df8p1fd360jsndbc11ed3ad7b", "b5a9edd0b8msh435ffe328e2f725p1bdf97jsn0f7c55a85991", "cff3589cb7msh4356e5ee7bf14cdp1a2aecjsne8f75aee4620",
            "be66b9a47emsh51482eb6cc9732ap18309cjsn51d8aa14fbef", "fc9a982916mshe1f3ad77f3e39ddp1f9b06jsna58c9c5eaba0", "e0f326883amsh94b0942a9513da4p16494ajsn29296f6e19fe", "0647bc5201msh84a9358b48d00eep163485jsne7ecf062e49f",
        ]
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"x-rapidapi-key": random.choice(shared_keys), "x-rapidapi-host": "spotify-downloader9.p.rapidapi.com"}
        # parse
        (resp := requests.get(f"https://spotify-downloader9.p.rapidapi.com/downloadSong?songId={song_id}", headers=headers, timeout=10, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'downloadLink'], None)
        (resp := requests.get(download_url, headers=headers, **request_overrides)).raise_for_status()
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        if download_url_status['file_size'] in {'NULL'}: download_url_status['file_size_bytes'], download_url_status['file_size'] = resp.content.__sizeof__(), SongInfoUtils.byte2mb(resp.content.__sizeof__())
        duration_in_secs = float(safeextractfromdict(search_result, ['item', 'data', 'duration', 'totalMilliseconds'], 0) or safeextractfromdict(search_result, ['itemV2', 'data', 'trackDuration', 'totalMilliseconds'], 0) or 0) / 1000
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'title'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None) or safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers,
        )
        # return
        return song_info
    '''_parsewithsavemytracksapi'''
    def _parsewithsavemytracksapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, str(search_result['id']), {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36", "Referer": "https://savemytracks.com/", "Origin": "https://savemytracks.com"}
        session = requests.Session(); session.headers.update((headers := RandomIPGenerator().addrandomipv4toheaders(headers=headers)))
        # parse
        (resp := session.get("https://savemytracks.com/", timeout=20, **request_overrides)).raise_for_status()
        ajax_url = re.search(r"ajaxUrl:\s*'([^']+)'", resp.text).group(1); nonce = re.search(r"nonce:\s*'([^']+)'", resp.text).group(1)
        api_base = re.search(r'"apiBase":"([^"]+)"', resp.text).group(1).replace("\\/", "/").rstrip("/")
        (resp := session.post(ajax_url, files={"action": (None, "vm_auth"), "nonce": (None, nonce)}, timeout=20, **request_overrides)).raise_for_status(); token = resp2json(resp=resp)["data"]["token"]
        (resp := session.get(f"{api_base}/api/spotify-info", params={"url": f"https://open.spotify.com/track/{song_id}"}, headers={"X-Req-V": token}, timeout=30, **request_overrides)).raise_for_status()
        (resp := session.post(f"{api_base}/api/download", json={"url": (download_result := resp2json(resp=resp))["youtubeUrl"], "resolution": "audio", "audio_format": "mp3",}, headers={"X-Req-V": token}, timeout=30, **request_overrides)).raise_for_status()
        download_result['job'] = resp2json(resp=resp); job_id = download_result['job']["job_id"]; max_retry_times = 120
        for _ in range(max_retry_times):
            (resp := session.post(ajax_url, files={"action": (None, "vm_auth"), "nonce": (None, nonce)}, timeout=20, **request_overrides)).raise_for_status(); token = resp2json(resp=resp)["data"]["token"]
            (resp := session.get(f"{api_base}/api/job/{job_id}", headers={"X-Req-V": token}, timeout=30, **request_overrides)).raise_for_status()
            if resp2json(resp=resp).get("status") == "completed" and resp2json(resp=resp).get("download_url"): download_url = resp2json(resp=resp)["download_url"]; break
            if resp2json(resp=resp).get("status") == "failed": raise RuntimeError(resp2json(resp=resp).get("error") or "job failed")
            time.sleep(2)
        else:
            raise TimeoutError("download job timed out")
        (resp := session.get(download_url, timeout=30, **request_overrides)).raise_for_status()
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        if download_url_status['file_size'] in {'NULL'}: download_url_status['file_size_bytes'], download_url_status['file_size'] = len(resp.content), SongInfoUtils.byte2mb(len(resp.content))
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = download_result.get('durationMs') / 1000
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('title')), singers=legalizestring(download_result.get('artist')), album=legalizestring(download_result.get('album') or safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)),
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=download_result.get('thumbnailUrl'), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content,
        )
        # return
        return song_info
    '''_parsewithspotmateapi'''
    def _parsewithspotmateapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, session = request_overrides or {}, str(search_result['id']), requests.Session()
        session.headers = {'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'}
        (resp := session.get('https://spotmate.online/en', **request_overrides)).raise_for_status()
        cookies, soup = "; ".join([f"{cookie.name}={cookie.value}" for cookie in session.cookies]), BeautifulSoup(resp.text, 'lxml')
        csrf_token = soup.find('meta', attrs={'name': 'csrf-token'}).get('content')
        headers = {
            'authority': 'spotmate.online', 'accept': '*/*', 'accept-language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7', 'origin': 'https://spotmate.online', 'referer': 'https://spotmate.online/en', 'x-csrf-token': csrf_token, 
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"', 'sec-fetch-dest': 'empty', 'sec-fetch-site': 'same-origin', 'content-type': 'application/json', 
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36', 'cookie': cookies, 'sec-fetch-mode': 'cors', 
        }
        # parse
        (resp := session.post('https://spotmate.online/getTrackData', json={'spotify_url': f'https://open.spotify.com/track/{song_id}'}, headers=headers, **request_overrides)).raise_for_status(); download_result = resp2json(resp=resp)
        (resp := session.post('https://spotmate.online/convert', json={'urls': f'https://open.spotify.com/track/{song_id}'}, headers=headers, **request_overrides)).raise_for_status(); download_result['convert'] = resp2json(resp=resp)
        duration_in_secs = float(safeextractfromdict(download_result, ['duration_ms'], 0) or 0) / 1000
        (resp := requests.get((download_url := download_result['convert']['url']), headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}, **request_overrides)).raise_for_status()
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        if download_url_status['file_size'] in {'NULL'}: download_url_status['file_size_bytes'], download_url_status['file_size'] = resp.content.__sizeof__(), SongInfoUtils.byte2mb(resp.content.__sizeof__())
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (download_result.get('artists', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['album', 'images', 0, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=self.default_download_headers,
        )
        # return
        return song_info
    '''_parsewithspowloadapi'''
    def _parsewithspowloadapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, session = request_overrides or {}, str(search_result['id']), requests.Session()
        session.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36', 'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'}
        # parse
        (resp := session.get('https://spowload.cc/en2', **request_overrides)).raise_for_status()
        initial_csrf_token = re.search(r'<meta name="csrf-token" content="([^"]+)">', resp.text).group(1)
        (resp := session.post('https://spowload.cc/analyze', data={'_token': initial_csrf_token, 'trackUrl': f'https://open.spotify.com/track/{song_id}'}, allow_redirects=True, **request_overrides)).raise_for_status()
        new_csrf_token = re.search(r'<meta name="csrf-token" content="([^"]+)">', resp.text).group(1)
        cover_url = m.group(1) if (m := re.search(r'name="Image-[^"]+"\s+value="([^"]+)"', resp.text)) else ''
        convert_headers = {'X-CSRF-TOKEN': new_csrf_token, 'Content-Type': 'application/json', 'Accept': 'application/json', 'Referer': resp.url}
        (resp := session.post('https://spowload.cc/convert', json={'urls': f'https://open.spotify.com/track/{song_id}', 'cover': cover_url}, headers=convert_headers, **request_overrides)).raise_for_status()
        download_result = resp2json(resp=resp); task_id = download_result.get('task_id') or download_result.get('taskId')
        if not task_id or (download_result.get('url') and str(download_result.get('url')).startswith('http')): download_url = download_result['url']
        else:
            while (True and task_id):
                time.sleep(2); (resp := session.get(f'https://spowload.cc/tasks/{quote(task_id)}', **request_overrides)).raise_for_status()
                download_result['task_submit_result'] = resp2json(resp=resp); parse_result = safeextractfromdict(resp2json(resp=resp), ['data', 'result'], {}) or {}
                download_url = parse_result.get('download_url') or safeextractfromdict(parse_result, ['data', 'download_url'], None) or safeextractfromdict(parse_result, ['data', 'url'], None)
                if (download_url and str(download_url).startswith('http')) or (safeextractfromdict(resp2json(resp=resp), ['data', 'status'], None) in {'failed'}): break
        duration_in_secs = float(safeextractfromdict(search_result, ['item', 'data', 'duration', 'totalMilliseconds'], 0) or safeextractfromdict(search_result, ['itemV2', 'data', 'trackDuration', 'totalMilliseconds'], 0) or 0) / 1000
        (resp := requests.get(download_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}, **request_overrides)).raise_for_status()
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        if download_url_status['file_size'] in {'NULL'}: download_url_status['file_size_bytes'], download_url_status['file_size'] = resp.content.__sizeof__(), SongInfoUtils.byte2mb(resp.content.__sizeof__())
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['item', 'data', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'name'], None)), singers=legalizestring(', '.join(safeextractfromdict(singer, ['profile', 'name'], None) for singer in (safeextractfromdict(search_result, ['item', 'data', 'artists', 'items'], []) or safeextractfromdict(search_result, ['itemV2', 'data', 'artists', 'items'], []) or []) if safeextractfromdict(singer, ['profile', 'name'], None))), album=legalizestring(safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'coverArt', 'sources', -1, 'url'], None) or safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'coverArt', 'sources', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=self.default_download_headers,
        )
        # return
        return song_info     
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for parser_func in [self._parsewithspowloadapi, self._parsewithspotmateapi, self._parsewithrapidapi, self._parsewithspotubedlapi, self._parsewithsavemytracksapi, self._parsewithbmediamdapi, self._parsewithchrisk772000api, self._parsewithmusicfabapi, ]:
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            pass  # TODO: Solve DRM Issues in Spotify
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, search_api, search_api_inputs, page_no, search_result_idx = request_overrides or {}, search_url['api'], search_url['inputs'], search_url['page_no'], -1
        lossless_quality_is_sufficient = False if self.default_cookies or request_overrides.get('cookies') else True
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            for search_result_idx, search_result in enumerate(safeextractfromdict((search_resp := search_api(**search_api_inputs)), ['data', 'searchV2', 'tracksV2', 'items'], []) or safeextractfromdict(search_resp, ['data', 'searchV2', 'tracks', 'items'], [])):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                search_result['id'] = safeextractfromdict(search_result, ['item', 'data', 'id'], None) or str(safeextractfromdict(search_result, ['item', 'data', 'uri'], '')).removeprefix('spotify:track:')
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
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **dict(request_overrides := request_overrides or {})).url
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, SPOTIFY_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, playlist_result_first = SpotifyMusicClientPlaylistUtils.parse(copy.deepcopy(self.session), playlist_id=playlist_id, request_overrides=request_overrides)
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
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['data', 'playlistV2', 'name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos