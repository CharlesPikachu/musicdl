'''
Function:
    Implementation of YouTubeMusicClient: https://music.youtube.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
import time
import base64
import random
import secrets
import requests
from ytmusicapi import YTMusic
from contextlib import suppress
from rich.progress import Progress
from typing_extensions import Unpack
from urllib.parse import quote, urlencode
from ..utils.spotifyutils import SpotubeSecureClient
from .base import BaseMusicClient, BaseMusicClientKwargs
from ..utils.youtubeutils import YouTubeAudioURLExtractor, REPAIDAPI_KEYS
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, SongInfo, SongInfoUtils, AudioLinkTester, LyricSearchClient


'''YouTubeMusicClient'''
class YouTubeMusicClient(BaseMusicClient):
    source = 'YouTubeMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(YouTubeMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, decrypt_func = rule or {}, request_overrides or {}, lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        ytmusic_search_api = YTMusic(auth=rule.get('auth'), user=rule.get('user'), requests_session=None, proxies=request_overrides.get('proxies') or self._autosetproxies(), language=rule.get('language', 'en'), location=rule.get('location', ''), oauth_credentials=rule.get('oauth_credentials')).search
        rapidapi_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36", "X-Rapidapi-Host": "youtube-music-api3.p.rapidapi.com", "X-Rapidapi-Key": decrypt_func(random.choice(REPAIDAPI_KEYS)), "Referer": "https://music-download-lake.vercel.app/", "Origin": "https://music-download-lake.vercel.app", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"}
        # construct search urls
        self.search_size_per_page = self.search_size_per_source
        ytmusic_search_rule = {'query': keyword, 'filter': rule.get('filter'), 'scope': rule.get('scope'), 'limit': self.search_size_per_source, 'ignore_spelling': rule.get('ignore_spelling', False)}
        rapidapi_search_rule = {'headers': rapidapi_headers, 'params': {'q': keyword, 'type': 'song', 'limit': self.search_size_per_source}, 'url': 'https://youtube-music-api3.p.rapidapi.com/search'}
        search_urls = [{'candidate_apis': [{'api': self.get, 'inputs': rapidapi_search_rule, 'method': 'rapidapi'}, {'api': ytmusic_search_api, 'inputs': ytmusic_search_rule, 'method': 'ytmusicapi'}]}]
        # return
        return search_urls
    '''_parsewithspotubedlapi'''
    def _parsewithspotubedlapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36", "Origin": "https://spotubedl.com", "Referer": "https://spotubedl.com/", "Accept": "*/*",}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        if not search_result.get('title'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        for engine in ('v1', 'v2', 'v3', 'v4'):
            try:
                download_result = SpotubeSecureClient().getdownloadinfobyvideoid(song_id, engine, 'mp3', quality='320', request_overrides=request_overrides)
                if not (download_url := SpotubeSecureClient.extractflagurl(download_result)) or not str(download_url).startswith('http'): continue
                resp = requests.get(download_url, headers=headers, **request_overrides)
                if not resp.ok:
                    download_url = "https://spotubedl.com/api/download/audiorelay?" + urlencode({"url": download_url})
                    resp = requests.get(download_url, headers=headers, **request_overrides)
                resp.raise_for_status(); download_url_status = {'ok': True, 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content), 'file_size_bytes': resp.content.__sizeof__(), 'file_size': SongInfoUtils.byte2mb(resp.content.__sizeof__()), 'download_url': download_url}; break
            except Exception: continue
        duration_in_secs = int(float(search_result.get('duration_seconds', 0) or 0)) or to_seconds_func(search_result.get('duration') or search_result.get('length') or '0:00')
        assert download_url_status['file_size_bytes'] > (duration_in_secs or 1) * 96 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None) or search_result.get('album')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=headers,
        )
        song_info.cover_url = song_info.cover_url[-1]['url'] if isinstance(song_info.cover_url, (list, tuple)) else song_info.cover_url
        # return
        return song_info
    '''_parsewithyt2songapi'''
    def _parsewithyt2songapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info, session = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source), requests.Session()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Accept": "application/json", "Content-Type": "application/json", "Origin": "https://yt2song.com", "Referer": "https://yt2song.com/",}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        if not search_result.get('title'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        (resp := session.post("https://yt2song.com/api/v1/infos", headers=headers, json={"url": f"https://www.youtube.com/watch?v={song_id}"}, timeout=10, **request_overrides)).raise_for_status()
        download_result = resp2json(resp=resp); payload = {"url": f"https://www.youtube.com/watch?v={song_id}", "name": download_result.get("title", "output"), "startTime": 0, "endTime": int(download_result.get("duration", 0)) - 1, "bitrate": "320", "format": "mp3", "artist": download_result.get("artist", ""), "album": download_result.get("album", ""), "year": download_result.get("year", ""), "description": download_result.get("description", ""), "thumbnail": download_result.get("thumbnail", ""),}
        (resp := session.post("https://yt2song.com/api/v1/download", headers=headers, json=payload, **request_overrides)).raise_for_status()
        download_url_status: dict = {'ok': True, 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content), 'file_size_bytes': resp.content.__sizeof__(), 'file_size': SongInfoUtils.byte2mb(resp.content.__sizeof__())}
        duration_in_secs = int(float(download_result.get('duration', 0) or search_result.get('duration_seconds', 0) or 0)) or to_seconds_func(search_result.get('duration') or search_result.get('length') or '0:00')
        assert download_url_status['file_size_bytes'] > (duration_in_secs or 1) * 96 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('title') or search_result.get('title')), singers=legalizestring(download_result.get('artist') or search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(download_result.get('album') or safeextractfromdict(search_result, ['album', 'name'], None) or search_result.get('album')), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=download_result.get('thumbnail') or search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url='https://yt2song.com/api/v1/download', download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=headers,
        )
        song_info.cover_url = song_info.cover_url[-1]['url'] if isinstance(song_info.cover_url, (list, tuple)) else song_info.cover_url
        # return
        return song_info
    '''_parsewithcutytapi'''
    def _parsewithcutytapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info, session = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source), requests.Session()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        api_url, file_base_url, youtube_url = "https://cutytapi.azurewebsites.net/exec/method", "https://filescutyt.com/", f"https://www.youtube.com/watch?v={song_id}"
        common, options = "--no-playlist --no-mtime -N 8", ("-f ba[acodec!=none]/bestaudio[acodec!=none]/ba/bestaudio/" "best[acodec!=none][height<=360]/worst[acodec!=none] " "-x --audio-format mp3 --audio-quality 0")
        if not search_result.get('title'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        payload = {"methodName": "GetYtDlpData", "arguments": f'{common} {options} {youtube_url}', "userId": secrets.token_urlsafe(16)}
        (resp := session.post(api_url, headers=headers, json=payload, timeout=(15, 900), **request_overrides)).raise_for_status()
        filename = (download_result := resp2json(resp=resp)).get("FileInAzure"); download_url = file_base_url + quote(filename, safe="")
        head = next((head for delay in (0, 1, 2, 4, 8) if not time.sleep(delay) and (head := session.head(download_url, headers=headers, allow_redirects=True, timeout=(10, 30), **request_overrides)) and head.status_code == 200), None) or head
        (resp := session.get(download_url, headers=headers, **request_overrides)).raise_for_status()
        download_url_status = {'file_size_bytes': resp.content.__sizeof__(), 'file_size': SongInfoUtils.byte2mb(resp.content.__sizeof__()), 'ok': True, 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content), 'download_url': download_url}
        duration_in_secs = int(float(search_result.get('duration_seconds', 0) or 0)) or to_seconds_func(search_result.get('duration') or search_result.get('length') or '0:00')
        assert download_url_status['file_size_bytes'] > (duration_in_secs or 1) * 96 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None) or search_result.get('album')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=headers,
        )
        song_info.cover_url = song_info.cover_url[-1]['url'] if isinstance(song_info.cover_url, (list, tuple)) else song_info.cover_url
        # return
        return song_info
    '''_parsewithcnvmp3api'''
    def _parsewithcnvmp3api(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", "Origin": "https://cnvmp3.com", "Referer": "https://cnvmp3.com/v55",}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        if not search_result.get('title'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        urls = {'check': 'https://cnvmp3.com/check_database.php', 'meta': 'https://cnvmp3.com/get_video_data.php', 'convert': 'https://cnvmp3.com/download_video_ucep.php', 'insert': 'https://cnvmp3.com/insert_to_database.php',}
        (resp := requests.post(urls['check'], headers=headers, json={'youtube_id': song_id, 'quality': 0, 'formatValue': 1}, **request_overrides)).raise_for_status()
        download_result = {}; download_result['database'] = database_result = resp2json(resp=resp); database_data = database_result.get('data') or {}
        if database_result.get('success') and database_data.get('server_path'): title = database_data.get('title') or search_result.get('title') or song_id; download_url = database_data['server_path']; cache_hit = True
        else: title, download_url, cache_hit = search_result.get('title'), None, False
        if cache_hit:
            try:
                (resp := requests.get(download_url, headers={'Referer': 'https://cnvmp3.com/', 'User-Agent': headers['User-Agent']}, **request_overrides,)).raise_for_status()
                if not resp.content or 'text/html' in resp.headers.get('content-type', '').lower(): cache_hit = False
            except requests.RequestException:
                cache_hit = False
        if not cache_hit:
            if not title:
                (resp := requests.post(urls['meta'], headers=headers, json={'url': f'https://www.youtube.com/watch?v={song_id}', 'token': '1234'}, **request_overrides)).raise_for_status()
                download_result['metadata'] = metadata_result = resp2json(resp=resp); title = metadata_result.get('title')
                if not metadata_result.get('success') or not title: raise RuntimeError(f'cnvmp3 metadata failed: {metadata_result}')
            (resp := requests.post(urls['convert'], headers=headers, json={'url': f'https://www.youtube.com/watch?v={song_id}', 'quality': 0, 'title': title, 'formatValue': 1,}, **request_overrides)).raise_for_status()
            download_result['converter'] = converter_result = resp2json(resp=resp); download_url = converter_result.get('download_link')
            if not converter_result.get('success') or not download_url: raise RuntimeError(f'cnvmp3 convert failed: {converter_result}')
            (resp := requests.get(download_url, headers={'Referer': 'https://cnvmp3.com/', 'User-Agent': headers['User-Agent']}, **request_overrides,)).raise_for_status()
        download_url_status = {'file_size_bytes': resp.content.__sizeof__(), 'file_size': SongInfoUtils.byte2mb(resp.content.__sizeof__()), 'ok': True, 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content), 'download_url': download_url}
        duration_in_secs = int(float(search_result.get('duration_seconds', 0) or 0)) or to_seconds_func(search_result.get('duration') or search_result.get('length') or '0:00')
        assert download_url_status['file_size_bytes'] > (duration_in_secs or 1) * 96 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None) or search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers={'Referer': 'https://cnvmp3.com/', 'User-Agent': headers['User-Agent']},
        )
        song_info.cover_url = song_info.cover_url[-1]['url'] if isinstance(song_info.cover_url, (list, tuple)) else song_info.cover_url
        # return
        return song_info
    '''_parsewithy2mateapi'''
    def _parsewithy2mateapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source)
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        key_url, converter_url, base_headers = "https://cnv.cx/v2/sanity/key", "https://cnv.cx/v2/converter", {"Origin": "https://frame.y2meta-uk.com", "Referer": "https://frame.y2meta-uk.com/", "Accept": "*/*", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",}
        if not search_result.get('title'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        # --key
        (resp := requests.get(key_url, params={"id": song_id}, headers={**base_headers, "Content-Type": "application/json"}, **request_overrides)).raise_for_status()
        # --converter
        (converter_headers := base_headers.copy())["key"] = (download_result := resp2json(resp=resp)).get("key")
        converter_headers.update({"Content-Type": "application/x-www-form-urlencoded",})
        payload = {"link": f"https://youtu.be/{song_id}", "format": "mp3", "audioBitrate": "320", "videoQuality": "720", "filenameStyle": "pretty", "vCodec": "h264",}
        (resp := requests.post(converter_url, headers=converter_headers, data=payload, **request_overrides)).raise_for_status()
        download_result['converter'] = resp2json(resp=resp); download_url = str(download_result['converter']['url']).replace('/tunnel?', '/tunnel/?', 1)
        # --download
        (resp := requests.get(download_url, headers={"Referer": "https://frame.y2meta-uk.com/", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"}, **request_overrides)).raise_for_status()
        download_url_status = {'file_size_bytes': resp.content.__sizeof__(), 'file_size': SongInfoUtils.byte2mb(resp.content.__sizeof__()), 'ok': True, 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content), 'download_url': download_url}
        duration_in_secs = int(float(search_result.get('duration_seconds', 0) or 0)) or to_seconds_func(search_result.get('duration') or search_result.get('length') or '0:00')
        assert download_url_status['file_size_bytes'] > (duration_in_secs or 1) * 96 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None) or search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
            identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers={"Referer": "https://frame.y2meta-uk.com/", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"},
        )
        song_info.cover_url = song_info.cover_url[-1]['url'] if isinstance(song_info.cover_url, (list, tuple)) else song_info.cover_url
        # return
        return song_info
    '''_parsewith4kdownloadapi'''
    def _parsewith4kdownloadapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source)
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        headers = {'Origin': 'https://4kdownload.to', 'Referer': 'https://4kdownload.to/', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36'}
        page_url, api_url = 'https://4kdownload.to/ensa/youtube-to-mp3', 'https://p.savenow.to/api/v2/download'
        if not search_result.get('title'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        (resp := requests.get(page_url, headers=headers, **request_overrides,)).raise_for_status()
        apikey_match = (re.search(r'''apikey\s*:\s*['"]([^'"]+)''', resp.text, re.I) or re.search(r'''params\.apikey\s*=.*?\|\|\s*['"]([^'"]+)''', resp.text, re.I | re.S,))
        if not apikey_match: raise RuntimeError('4kdownload API key not found')
        (resp := requests.get(api_url, headers=headers, params={'format': 'mp3', 'url': f'https://www.youtube.com/watch?v={song_id}', 'apikey': apikey_match.group(1),}, **request_overrides,)).raise_for_status()
        initial_result = resp2json(resp=resp); progress_url = initial_result.get('progress_url'); progress_result = initial_result; deadline = time.monotonic() + 240
        if not progress_url and not (initial_result.get('download_url') or initial_result.get('url')): raise RuntimeError(initial_result.get('message') or f'Invalid API response: {initial_result}')
        while (time.monotonic() < deadline and not progress_result.get('download_url') and not progress_result.get('url')):
            time.sleep(1.5); (resp := requests.get(progress_url, headers=headers, **request_overrides,)).raise_for_status(); progress_result = resp2json(resp=resp)
            if (progress_result.get('success') is False or progress_result.get('error')): raise RuntimeError(progress_result.get('error') or progress_result.get('message') or progress_result.get('text') or 'MP3 conversion failed')
        if not (download_url := (progress_result.get('download_url') or progress_result.get('url'))): raise TimeoutError('MP3 conversion timed out')
        download_result = {'initial': initial_result, 'progress': progress_result,}
        (resp := requests.get(download_url, headers={'User-Agent': headers['User-Agent']}, **request_overrides,)).raise_for_status()
        if any(value in resp.headers.get('Content-Type', '').lower() for value in ('text/html', 'application/json')): raise RuntimeError('Download URL returned an error document')
        download_url_status = {'file_size_bytes': resp.content.__sizeof__(), 'file_size': SongInfoUtils.byte2mb(resp.content.__sizeof__()), 'ok': True, 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content), 'download_url': download_url}
        # --song info
        duration_in_secs = int(float(search_result.get('duration_seconds', 0) or 0)) or to_seconds_func(search_result.get('duration') or search_result.get('length') or '0:00')
        assert download_url_status['file_size_bytes'] > (duration_in_secs or 1) * 96 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None) or search_result.get('album')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, 
        )
        song_info.cover_url = song_info.cover_url[-1]['url'] if isinstance(song_info.cover_url, (list, tuple)) else song_info.cover_url
        # return
        return song_info
    '''_parsewithmediaytmp3api'''
    def _parsewithmediaytmp3api(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source)
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        song_url, converter_url = f"https://www.youtube.com/watch?v={song_id}", "https://hub.convert1s.com/api/download"
        base_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Accept": "application/json", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "Origin": "https://media.ytmp3.gg", "Referer": "https://media.ytmp3.gg/"}
        if not search_result.get('title'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        # --converter
        download_result, payload = {}, {"url": song_url, "os": "windows", "output": {"type": "audio", "format": "mp3",}, "audio": {"bitrate": "320k"}}
        converter_headers = base_headers.copy(); converter_headers["Content-Type"] = "application/json"
        (resp := requests.post(converter_url, headers=converter_headers, json=payload, **request_overrides)).raise_for_status()
        download_result['converter'] = resp2json(resp=resp); status_url = download_result['converter'].get('statusUrl')
        if not status_url: raise RuntimeError(f"MediaYTMP3 converter response has no statusUrl: {download_result['converter']}")
        # --poll status
        for _ in range(120):
            (resp := requests.get(status_url, headers=base_headers, **request_overrides)).raise_for_status(); download_result['status'] = resp2json(resp=resp)
            if download_result['status'].get('status') == 'completed' and download_result['status'].get('downloadUrl'): break
            if download_result['status'].get('status') in {'failed', 'error', 'blocked'}: raise RuntimeError(f"MediaYTMP3 convert failed: {download_result['status']}")
            time.sleep(1)
        else:
            raise TimeoutError(f"MediaYTMP3 convert timeout: {download_result.get('status')}")
        download_url = download_result['status'].get('downloadUrl'); download_result['download_url'] = download_url
        if not download_url: raise RuntimeError(f"MediaYTMP3 status response has no downloadUrl: {download_result['status']}")
        # --download
        download_headers = {"User-Agent": base_headers["User-Agent"], "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8", "Accept-Language": base_headers["Accept-Language"], "Referer": "https://media.ytmp3.gg/"}
        (resp := requests.get(download_url, headers=download_headers, **request_overrides)).raise_for_status()
        download_url_status = {'file_size_bytes': resp.content.__sizeof__(), 'file_size': SongInfoUtils.byte2mb(resp.content.__sizeof__()), 'ok': True, 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content), 'download_url': download_url}
        # --song info
        duration_in_secs = int(float(search_result.get('duration_seconds', 0) or 0)) or to_seconds_func(search_result.get('duration') or search_result.get('length') or '0:00')
        assert download_url_status['file_size_bytes'] > (duration_in_secs or 1) * 96 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None) or search_result.get('album')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=download_headers,
        )
        song_info.cover_url = song_info.cover_url[-1]['url'] if isinstance(song_info.cover_url, (list, tuple)) else song_info.cover_url
        # return
        return song_info
    '''_parsewithgmpionapi'''
    def _parsewithgmpionapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source)
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        song_url, api_url = f"https://www.youtube.com/watch?v={song_id}", "https://api.ezsrv.net"
        base_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36", "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "Origin": "https://gmpion.pl", "Referer": "https://gmpion.pl/"}
        if not search_result.get('title'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        # --attest
        attest_headers = base_headers.copy(); attest_headers["Content-Type"] = "application/json"
        (resp := requests.post(f"{api_url}/api/attest", headers=attest_headers, json={"token": ""}, **request_overrides)).raise_for_status()
        attest_result = resp2json(resp=resp); captcha_token = attest_result.get('token')
        # --converter
        download_result, payload = {'attest': attest_result}, {"url": song_url, "format": "mp3", "quality": 320, "captchaToken": captcha_token}
        (resp := requests.post(f"{api_url}/api/convert", headers=attest_headers, json=payload, **request_overrides)).raise_for_status()
        download_result['converter'] = resp2json(resp=resp); job_id = download_result['converter'].get('jobId')
        if not job_id: raise RuntimeError(f"GMPion converter response has no jobId: {download_result['converter']}")
        # --poll status
        status_url = f"{api_url}/api/convert/status?jobId={job_id}"
        for _ in range(120):
            (resp := requests.get(status_url, headers=base_headers, **request_overrides)).raise_for_status(); download_result['status'] = resp2json(resp=resp)
            if download_result['status'].get('title') and not search_result.get('title'): search_result['title'] = download_result['status']['title']
            if download_result['status'].get('status') == 'done' and download_result['status'].get('downloadUrl'): break
            if download_result['status'].get('status') in {'failed', 'error', 'blocked'}: raise RuntimeError(f"GMPion convert failed: {download_result['status']}")
            time.sleep(2)
        else:
            raise TimeoutError(f"GMPion convert timeout: {download_result.get('status')}")
        download_url = download_result['status'].get('downloadUrl'); download_result['download_url'] = download_url
        if not download_url: raise RuntimeError(f"GMPion status response has no downloadUrl: {download_result['status']}")
        # --download
        download_headers = {"User-Agent": base_headers["User-Agent"], "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8", "Accept-Language": base_headers["Accept-Language"], "Referer": "https://gmpion.pl/"}
        (resp := requests.get(download_url, headers=download_headers, **request_overrides)).raise_for_status()
        download_url_status = {'file_size_bytes': resp.content.__sizeof__(), 'file_size': SongInfoUtils.byte2mb(resp.content.__sizeof__()), 'ok': True, 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content), 'download_url': download_url}
        # --song info
        duration_in_secs = int(float(search_result.get('duration_seconds', 0) or 0)) or to_seconds_func(search_result.get('duration') or search_result.get('length') or '0:00')
        assert download_url_status['file_size_bytes'] > (duration_in_secs or 1) * 96 * 1000 / 8
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or download_result['status'].get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None) or search_result.get('album')), ext=download_url_status['ext'],
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=download_headers,
        )
        song_info.cover_url = song_info.cover_url[-1]['url'] if isinstance(song_info.cover_url, (list, tuple)) else song_info.cover_url
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for parser_func in [self._parsewithy2mateapi, self._parsewithmediaytmp3api, self._parsewithgmpionapi, self._parsewith4kdownloadapi, self._parsewithyt2songapi, self._parsewithcnvmp3api, self._parsewithspotubedlapi, self._parsewithcutytapi, ]:
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_getsongmetainfo'''
    def _getsongmetainfo(self, song_id, request_overrides: dict = None):
        ytmusic = YTMusic(proxies=(request_overrides := request_overrides or {}).get('proxies') or self._autosetproxies())
        with suppress(Exception): data = {}; data = ytmusic.get_watch_playlist(videoId=song_id, limit=1)
        return safeextractfromdict(data, ['tracks', 0], {}) or {}
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('videoId'))): return song_info
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        codec_to_ext_func = lambda c: next((str(ext).removeprefix('.') for k, ext in {"mp4a": ".m4a", "flac": ".flac", "opus": ".opus", "vorbis": ".ogg", "mp3": ".mp3", "aac": ".aac", "alac": ".m4a", "pcm": ".wav", "wav": ".wav"}.items() if str((c[0] if isinstance(c, (list, tuple)) else c)).lower().startswith(k)), None)
        if not search_result.get('title'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            download_result = YouTubeAudioURLExtractor().extract(youtube_url=f"https://www.youtube.com/watch?v={search_result['videoId']}")
            duration_in_secs = download_result.get('duration_seconds') or search_result.get('duration_seconds') or to_seconds_func(search_result.get('duration') or search_result.get('length') or '0:00')
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or download_result.get('title')), singers=legalizestring(download_result.get('author') or search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None) or search_result.get('album')), 
                ext=codec_to_ext_func(download_result.get('audio_codec')), file_size_bytes=download_result.get('content_length'), file_size=SongInfoUtils.byte2mb(download_result.get('content_length')), identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=download_result.get('thumbnail') or search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_result.get('url'), download_url_status={'ok': True}, 
            )
            song_info.cover_url = song_info.cover_url[-1]['url'] if isinstance(song_info.cover_url, (list, tuple)) else song_info.cover_url
        # compare and select the best
        song_info = song_info_flac if song_info_flac.with_valid_download_url and (not song_info.with_valid_download_url or song_info_flac.largerthan(song_info)) else song_info
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        if not song_info.duration or song_info.duration in {'00:00:00', '-:-:-'}: song_info.duration_s = locals().get('duration_in_secs'); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # supplement lyric results
        lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        if not song_info.duration or song_info.duration in {'00:00:00', '-:-:-'}: song_info.duration_s = int(float(lyric_result.get('duration') or 0)); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = {}, request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, candidate_apis, page_no, search_result_idx = request_overrides or {}, copy.deepcopy(search_url)['candidate_apis'], 1, -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            ytmusicapi_candidate_api: dict = [c for c in candidate_apis if c['method'] in {'ytmusicapi'}][0]; rapidapi_candidate_api: dict = [c for c in candidate_apis if c['method'] in {'rapidapi'}][0]
            with suppress(Exception): search_results = None; resp = ytmusicapi_candidate_api['api'](**ytmusicapi_candidate_api['inputs']); search_results = [s for s in resp if s['resultType'] == 'song']
            if not search_results: resp = rapidapi_candidate_api['api'](**rapidapi_candidate_api['inputs']); search_results = resp2json(resp=resp)['result']
            for search_result_idx, search_result in enumerate(search_results or list()):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with third part apis
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=song_info_flac, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
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