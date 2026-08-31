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
import requests
from contextlib import suppress
from typing_extensions import Unpack
from ..utils.hosts import QQ_MUSIC_HOSTS
from pathvalidate import sanitize_filepath
from urllib.parse import urlparse, parse_qs, urljoin
from .base import BaseMusicClient, BaseMusicClientKwargs
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils.qqutils import QQMusicClientUtils, SearchType, Credential, ThirdPartVKeysAPISongFileType, SongFileType, EncryptedSongFileType
from ..utils import resp2json, legalizestring, safeextractfromdict, usesearchheaderscookies, extractdurationsecondsfromlrc, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils


'''QQMusicClient'''
class QQMusicClient(BaseMusicClient):
    source = 'QQMusicClient'
    def __init__(self, use_encrypted_endpoint: bool = False, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(QQMusicClient, self).__init__(**kwargs)
        self.use_encrypted_endpoint = use_encrypted_endpoint
        self.default_search_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36', 'Referer': 'https://y.qq.com/', 'Origin': 'https://y.qq.com/',}
        self.default_parse_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36', 'Referer': 'https://y.qq.com/', 'Origin': 'https://y.qq.com/',}
        self.default_download_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36', 'Referer': 'http://y.qq.com',}
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
            search_urls.append({'url': base_url, 'data': json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 'page_no': int(count // page_size) + 1})
            if self.use_encrypted_endpoint: search_urls[-1]['params'] = {"sign": QQMusicClientUtils.sign(payload)}
            count += page_size
        # return
        return search_urls
    '''_parsewithvkeysapi'''
    def _parsewithvkeysapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result.get('mid') or search_result.get('songmid')
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse download result
        for music_quality in list(ThirdPartVKeysAPISongFileType.ID_TO_NAME.value.keys())[::-1][2: 8]:
            (resp := requests.get(f"https://api.vkeys.cn/music/tencent/song/link?mid={song_id}&quality={music_quality}", headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], None)) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or search_result.get('songname')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=int(float(search_result.get('interval', 0) or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('interval', 0) or 0))), lyric=None, cover_url=f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{safeextractfromdict(search_result, ['album', 'mid'], '') or search_result.get('albummid')}.jpg", download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': download_result, 'lyric': {}}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        with suppress(Exception): resp = None; (resp := requests.get(f"https://api.vkeys.cn/v2/music/tencent/lyric?mid={song_id}", headers=headers, timeout=10, **request_overrides)).raise_for_status()
        lyric_result, lyric = ({}, 'NULL') if (not locals().get('resp') or not hasattr(locals().get('resp'), 'text')) else ((lyric_result := resp2json(resp=resp)), cleanlrc(safeextractfromdict(lyric_result, ['data', 'lrc'], '')))
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_parsewithxingmianapi'''
    def _parsewithxingmianapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, candidate_music_qualities = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), ['超清母带', 'Hi-Res', '无损', '高音质', '低音质']
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        decrypt_func, REQUEST_KEYS = lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8'), ['charlespikachuYjJmMjU1ODA2MmJmODIzNDcwNjUyNjgwODZmMGMwOTBmYjMwYTg5MTZiMjIyNzEwM2VkMTQwZWQzZTNkMjU5ZA==', ]
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        for music_quality in candidate_music_qualities:
            (resp := requests.get(f'https://api.xingmian.bbroot.com/API/qqmusicparse.php?id={song_id}&apikey={decrypt_func(random.choice(REQUEST_KEYS))}&quality={music_quality}', timeout=10, headers=headers, verify=False, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = int(float(safeextractfromdict(download_result, ['data', 'duration'], 0) or 0))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring((safeextractfromdict(download_result, ['data', 'author'], None) or '').replace('/', ',')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or ''), cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': download_result, 'lyric': {}}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithxcvtsapi'''
    def _parsewithxcvtsapi(self, search_result: dict, request_overrides: dict = None):
        # init
        REQUEST_KEYS, decrypt_func = ['charlespikachuNzg5OTMzNDRiOWJmMTEwNTY1NTU5OTAwOWNkYmEzZDI=', 'charlespikachuY2U3NzhlYjBkMTg1OGVkZmI0YjIwNzFhMTE1ZjFlZGY=', 'charlespikachuNzRhNjdhZjM3ZjUyODg4MjYxNmRkMzU1OTdlYTc0MGQ='], lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8')
        MUSIC_QUALITIES = ["臻品母带", "臻品全景声", "臻品2.0", "SQ无损", "HQ高品质", "中品质", "普通", "低品质", "试听"]
        request_overrides, song_id, headers = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        for music_quality in MUSIC_QUALITIES[:4]:
            (resp := requests.get(f"https://api.xcvts.cn/api/music/qq?apiKey={decrypt_func(random.choice(REQUEST_KEYS))}&mid={song_id}&type={music_quality}", timeout=10, headers=headers, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'music'], None)) or not str(download_url).startswith('http'): break
            lyric = cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or 'NULL')
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'title'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'singer'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album_name'], None)), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=extractdurationsecondsfromlrc(lyric), duration=SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(lyric)), lyric=lyric, cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': download_result, 'lyric': {}}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # return
        return song_info
    '''_parsewith317akapi'''
    def _parsewith317akapi(self, search_result: dict, request_overrides: dict = None):
        # init
        MUSIC_QUALITIES, headers = ["7", "9", "10", "8", "6", "5"], {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"}
        request_overrides, song_id = request_overrides or {}, search_result.get('mid') or search_result.get('songmid')
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        REQUEST_KEYS, decrypt_func = ['charlespikachuWk83NlFKQ0lINVBQSUNKT09YVUg='], lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8')
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(f"https://api.317ak.com/api/yinyue/qqyinyue?ckey={decrypt_func(random.choice(REQUEST_KEYS))}&i={song_id}&br={music_quality}&type=json&lrc=1", headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], None)) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('songName')), singers=legalizestring(download_result.get('artistName')), album=legalizestring(download_result.get('albumName')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=str(song_id), duration_s=int(float(search_result.get('interval', 0) or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('interval', 0) or 0))), lyric=cleanlrc(download_result.get('lyric') or ''), cover_url=download_result.get('cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': download_result, 'lyric': {}}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # return
        return song_info
    '''_parsewithlxmusicapi'''
    def _parsewithlxmusicapi(self, search_result: dict, request_overrides: dict = None):
        # init
        MUSIC_QUALITIES, request_overrides, song_id = ["flac24bit", "hires", "flac", "320k"], request_overrides or {}, search_result.get('mid') or search_result.get('songmid')
        headers = {"Content-Type": "application/json", "User-Agent": "lx-music-request/2.12.2", "X-Request-Key": "share-v3"}
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(f"https://lxmusicapi.onrender.com/url/tx/{song_id}/{music_quality}", headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], None)) or not str(download_url).startswith('http'): break
            if '无法获取' in str(download_result.get('msg')) or 'http://panspace.kuwo.cn/' in download_url: break 
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
        request_overrides, song_id, song_info, decrypt_func = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source), lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Chromium\";v=\"148\", \"Google Chrome\";v=\"148\", \"Not/A)Brand\";v=\"99\"", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "document", "sec-fetch-mode": "navigate", "sec-fetch-site": "none", "sec-fetch-user": "?1", "upgrade-insecure-requests": "1",
        }
        (resp := requests.get(f'https://api.nki.pw/API/music_open_api.php?mid={song_id}&apikey={decrypt_func(random.choice(REQUEST_KEYS))}', headers=headers, timeout=20, verify=False, **request_overrides)).raise_for_status()
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
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        (resp := requests.get(f'https://tang.api.s01s.cn/music_open_api.php?mid={song_id}', headers=headers, timeout=10, **request_overrides)).raise_for_status()
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
    '''_parsewithhk0ccapi'''
    def _parsewithhk0ccapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", "Content-Type": "application/json"}
        (resp := requests.get(f'https://api.hk0.cc/api/qqmusic?mid={song_id}', headers=headers, **request_overrides)).raise_for_status()
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
        decrypt_func, REQUEST_KEYS = lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8'), ['charlespikachuc2stNTc2ZmFkZTQxNjI2M2I3ZmY3MjZhZjM1NGQ5ZDkzNzM=', 'charlespikachuc2stMDE4YjlmOGQ4MGRjMTg5OGEyOTI3ZTgwMjA2NjNkODY=']
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        (resp := requests.get(f'https://apii.xianyuw.cn/api/v1/qq-music-search?id={song_id}&key={decrypt_func(random.choice(REQUEST_KEYS))}&no_url=0&br=hires', headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['data']['url']) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        lyric = cleanlrc(safeextractfromdict(download_result, ['data', 'lrc'], '') or 'NULL')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'title'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'author'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None) or safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=extractdurationsecondsfromlrc(lyric), duration=SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(lyric)), lyric=lyric, cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status,
        )
        # return
        return song_info
    '''_parsewithxunhuisiapi'''
    def _parsewithxunhuisiapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        (resp := requests.get(f'https://api.xunhuisi.store/API/QQMusic/Song.php?mid={song_id}&type=json', headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['music_url']) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        lyric = cleanlrc(safeextractfromdict(download_result, ['lyric'], '') or 'NULL')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['title'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['singer'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=extractdurationsecondsfromlrc(lyric), duration=SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(lyric)), lyric=lyric, cover_url=safeextractfromdict(download_result, ['cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status,
        )
        # return
        return song_info
    '''_parsewithyutangxiaowuapi'''
    def _parsewithyutangxiaowuapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        (resp := requests.get(f'https://api.yutangxiaowu.cn/api/v1/qqmusic/music?songmid={song_id}', headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['url']) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        lyric, duration_in_secs = cleanlrc(safeextractfromdict(download_result, ['lyric'], '') or 'NULL'), to_seconds_func(safeextractfromdict(download_result, ['detail', 'duration'], '') or '00:00:00')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['detail', 'songName'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['detail', 'singer'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['detail', 'album'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{safeextractfromdict(search_result, ['album', 'mid'], '') or search_result.get('albummid')}.jpg", download_url=download_url_status['download_url'], download_url_status=download_url_status,
        )
        # return
        return song_info
    '''_parsewithlpzapi'''
    def _parsewithlpzapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        (resp := requests.get(f'https://lpz.chatc.vip/apiqq.php?songmid={song_id}&type=json&br=1', headers=headers, timeout=10, verify=False, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['data']['music_url']) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        lyric = cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or 'NULL').replace('\\n', '\n')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'song_name'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'song_singer'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=extractdurationsecondsfromlrc(lyric), duration=SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(lyric)), lyric=lyric, cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status,
        )
        # return
        return song_info
    '''_parsewithcyapi'''
    def _parsewithcyapi(self, search_result: dict, request_overrides: dict = None):
        # init
        REQUEST_KEYS = ["1ffdf5733f5d538760e63d7e46ba17438d9f7b9dfc18c51be1109386fd74c3a1", "2baf39266d8ef0580aba937245d5bb569fe376f230ff508f1faa0922dc320fe4"]
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        (resp := requests.get(f'https://cyapi.top/API/qq_music.php', params={"apikey": random.choice(REQUEST_KEYS), "type": "json", "mid": song_id, "quality": "lossless"}, headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['url']) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        lyric = cleanlrc(safeextractfromdict(download_result, ['lyric', 'text'], '') or 'NULL')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (download_result.get('artists', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(download_result, ['album', 'name'], None)), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=extractdurationsecondsfromlrc(lyric), duration=SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(lyric)), lyric=lyric, cover_url=safeextractfromdict(download_result, ['cover', 'large'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status,
        )
        # return
        return song_info
    '''_parsewithlzmhhhapi'''
    def _parsewithlzmhhhapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36", "Referer": "https://music.lzmhhh.com/", "Origin": "https://music.lzmhhh.com"}
        (resp := requests.post('https://music.lzmhhh.com/api/music/url', headers=headers, data={'id': song_id, 'type': 'qq'}, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['data']) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or search_result.get('songname')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=int(float(search_result.get('interval', 0) or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('interval', 0) or 0))), lyric=None, cover_url=f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{safeextractfromdict(search_result, ['album', 'mid'], '') or search_result.get('albummid')}.jpg", download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithchkszapi'''
    def _parsewithchkszapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", "Referer": "https://cp.chksz.top/", "Origin": "https://cp.chksz.top", "Accept": "*/*"}
        (resp := requests.get(f'https://api.chksz.com/api/qq_music?mid={song_id}&size=master', headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or search_result.get('songname')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=str(song_id), duration_s=int(float(search_result.get('interval', 0) or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('interval', 0) or 0))), lyric=None, cover_url=f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{safeextractfromdict(search_result, ['album', 'mid'], '') or search_result.get('albummid')}.jpg", download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or (request_overrides := request_overrides or {}).get('cookies'): return SongInfo(source=self.source)
        l1_parser_funcs = [self._parsewithvkeysapi, self._parsewith317akapi, self._parsewithxingmianapi, self._parsewithchkszapi, self._parsewithxcvtsapi, ] # svip
        l2_parser_funcs = [self._parsewithnkiapi, self._parsewithtangapi, self._parsewithhk0ccapi, ] # vip
        l3_parser_funcs = [self._parsewithcyapi, self._parsewithlzmhhhapi, self._parsewithxunhuisiapi, ] # vip account but only mp3 or m4a files can be requested
        l4_parser_funcs = [self._parsewithxianyuwapi, self._parsewithyutangxiaowuapi, self._parsewithlxmusicapi, self._parsewithlpzapi, ] # invalid or unstable accounts
        for parser_func in (l1_parser_funcs + l2_parser_funcs + l3_parser_funcs + l4_parser_funcs):
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_getsongmetainfo'''
    def _getsongmetainfo(self, song_id, request_overrides: dict = None):
        request_overrides, resp, url = request_overrides or {}, None, "https://u.y.qq.com/cgi-bin/musicu.fcg"
        payload = {"songinfo": {"method": "get_song_detail_yqq", "module": "music.pf_song_detail_svr", "param": {"song_mid": song_id}}}
        with suppress(Exception): (resp := self.post(url, json=payload, **request_overrides)).raise_for_status()
        return (safeextractfromdict(resp2json(resp=resp), ['songinfo', 'data', 'track_info'], {}) or {})
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac', 'ogg'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('mid') or search_result.get('songmid'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            if not (safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
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
    def _search(self, keyword: str = '', search_url: dict = {}, request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, lossless_quality_is_sufficient = request_overrides or {}, False if self.default_cookies or request_overrides.get('cookies') else True
        search_meta, search_result_idx = copy.deepcopy(search_url), -1; search_url, page_no = search_meta.pop('url'), search_meta.pop('page_no')
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.post(search_url, **search_meta, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp)['music.search.SearchCgiService.DoSearchForQQMusicMobile']['data']['body']['item_song']):
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
                self.logger_handle.warning(f'Fail to parse track info {track_info}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result, ['cdlist', 0, 'dissname'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos