'''
Function:
    Implementation of NeteaseMusicClient: https://music.163.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import hmac
import json
import copy
import time
import base64
import random
import hashlib
import requests
import warnings
import json_repair
from contextlib import suppress
from typing_extensions import Unpack
from pathvalidate import sanitize_filepath
from urllib.parse import urlparse, parse_qs
from .base import BaseMusicClient, BaseMusicClientKwargs
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from ..utils.hosts import NETEASE_MUSIC_HOSTS, hostmatchessuffix, obtainhostname
from ..utils.neteaseutils import EapiCryptoUtils, MUSIC_QUALITIES, DEFAULT_COOKIES
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import resp2json, legalizestring, safeextractfromdict, usesearchheaderscookies, extractdurationsecondsfromlrc, useparseheaderscookies, cleanlrc, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils, RandomIPGenerator
warnings.filterwarnings('ignore')


'''NeteaseMusicClient'''
class NeteaseMusicClient(BaseMusicClient):
    source = 'NeteaseMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(NeteaseMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36', 'Referer': 'https://music.163.com/'}
        self.default_parse_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36', 'Referer': 'https://music.163.com/'}
        self.default_download_headers = {}
        self.default_headers = self.default_search_headers
        self.default_search_cookies = self.default_search_cookies or DEFAULT_COOKIES
        self.default_parse_cookies = self.default_parse_cookies or DEFAULT_COOKIES
        self.default_download_cookies = self.default_download_cookies or DEFAULT_COOKIES
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'s': keyword, 'type': 1, 'limit': 10, 'offset': 0}).update(rule)
        # construct search urls
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'https://music.163.com/api/cloudsearch/pc'
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['limit'] = page_size
            page_rule['offset'] = int(count // page_size) * page_size
            search_urls.append({'url': base_url, 'data': page_rule, 'page': int(count // page_size) + 1})
            count += page_size
        # return
        return search_urls
    '''_parsewithxiaoqinapi'''
    def _parsewithxiaoqinapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = dict(request_overrides or {}), search_result['id'], {"Accept": "*/*", "Origin": "https://wyapi.toubiec.cn", "Referer": "https://wyapi.toubiec.cn/", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        (resp := requests.post("https://nextmusic.toubiec.cn/api/ip", headers=headers, json={"timestamp": int(time.time() * 1000)}, verify=False, timeout=10, **request_overrides)).raise_for_status(); ip_address = resp2json(resp=resp)['data']['ip']
        # parse download result
        for music_quality in MUSIC_QUALITIES:
            # --download url
            payload = {"id": str(song_id), "level": music_quality, "timestamp": int(time.time() * 1000), "ip": ip_address} 
            with suppress(Exception): resp = None; (resp := requests.post("https://nextmusic.toubiec.cn/api/getSongUrl", headers=headers, json=payload, verify=False, timeout=10, **request_overrides)).raise_for_status()
            if safeextractfromdict(resp2json(resp=resp), ['data', 'url'], 'level') != music_quality:
                with suppress(Exception): (resp := requests.post("https://nextmusic.toubiec.cn/api/getMusicUrl", headers=headers, json=payload, verify=False, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            # --song info
            (resp := requests.post("https://nextmusic.toubiec.cn/api/getSongInfo", headers=headers, json={"id": str(song_id), "timestamp": int(time.time() * 1000), "ip": ip_address}, verify=False, timeout=10, **request_overrides)).raise_for_status()
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            download_result['song_info'] = resp2json(resp=resp); duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['song_info', 'data', 'duration'], '') or '')
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['song_info', 'data', 'name'], None)), singers=legalizestring((safeextractfromdict(download_result, ['song_info', 'data', 'singer'], '') or '').replace('/', ',')), album=legalizestring(safeextractfromdict(download_result, ['song_info', 'data', 'album'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['song_info', 'data', 'picimg'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        with suppress(Exception): resp = None; (resp := requests.post("https://nextmusic.toubiec.cn/api/getSongLyric", json={"id": str(song_id), "timestamp": int(time.time() * 1000), "ip": ip_address}, headers=headers, verify=False, timeout=10, **request_overrides)).raise_for_status()
        lyric = cleanlrc(safeextractfromdict((lyric_result := resp2json(resp=resp)), ['data', 'lrc'], '') or '')
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_parsewithhaitangwapi'''
    def _parsewithhaitangwapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(url=f'https://musicapi.haitangw.net/music/wy.php?id={song_id}&level={music_quality}&type=json', timeout=10, headers=headers, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['data', 'duration'], 0))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithrrvennapi'''
    def _parsewithrrvennapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", "Referer": "https://music.rrvenn.cn/"}
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.post(url=f'https://music.rrvenn.cn/Song_V1', json={"url": str(song_id), "level": music_quality, "type": "json"}, timeout=10, headers=headers, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or '')))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring((safeextractfromdict(download_result, ['data', 'ar_name'], None) or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'al_name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithznnuapi'''
    def _parsewithznnuapi(self, search_result: dict, request_overrides: dict = None):
        # init
        HMAC_SECRET_KEY, BASE_URL = b"a09d0f3700a279584e1515354fbe08a7ee1c617f919543142fa625b82f1b5ad0", "https://music.znnu.com"
        request_overrides, song_id, random_ip = request_overrides or {}, search_result['id'], RandomIPGenerator().ipv4()
        generate_signature_func = lambda params, timestamp, domain="music.znnu.com": hmac.new(HMAC_SECRET_KEY, (str(timestamp) + domain + "".join(f"{k}={v}" for k, v in sorted(((k, v) for k, v in params.items() if k not in {'signature', 'timestamp', 'domain', 'ver'}), key=lambda item: item[0]))).encode("utf-8"), hashlib.sha256).hexdigest()
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        (resp := requests.get(f"{BASE_URL}/api/key", timeout=10, headers=headers, **request_overrides)).raise_for_status()
        key_token, b64_key = resp2json(resp=resp)['data']['keyToken'], resp2json(resp=resp)['data']['key']
        headers = {"X-Key-Token": key_token, "X-Referer": "musicParser", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": f"{BASE_URL}/", "Origin": BASE_URL, "Content-Type": "application/x-www-form-urlencoded",}
        # parse
        for music_quality in MUSIC_QUALITIES:
            timestamp, domain, params = int(time.time()), "music.znnu.com", {"act": "song", "id": str(song_id), "level": music_quality, "rawInput": f"https://music.163.com/#/song?id={song_id}", "ip": random_ip}
            (payload := params.copy()).update({"timestamp": timestamp, "domain": domain, "signature": generate_signature_func(params, timestamp, domain)})
            (resp := requests.post(f"{BASE_URL}/api/song", headers=headers, data=payload, **request_overrides)).raise_for_status()
            iv, ciphertext, tag, key = base64.b64decode((enc_data := (download_result := resp2json(resp=resp))['data'])['iv']), base64.b64decode(enc_data['ciphertext']), base64.b64decode(enc_data['tag']), base64.b64decode(b64_key)
            download_result = json_repair.loads(AESGCM(key).decrypt(nonce=iv, data=ciphertext + tag, associated_data=None).decode('utf-8'))
            if not (download_url := safeextractfromdict(download_result, ['url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(str(download_result.get('artist', '') or '').replace('/', ', ')), album=legalizestring(download_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=song_id, duration_s=extractdurationsecondsfromlrc(download_result.get('lrc') or ''), duration=SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(download_result.get('lrc') or '')), lyric=cleanlrc(download_result.get('lrc') or ''), cover_url=download_result.get('cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithxuanluogeapi'''
    def _parsewithxuanluogeapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse download result
        for music_quality in MUSIC_QUALITIES:
            params = {"route": "/music/url", "id": song_id, "level": music_quality, "use": "play", "source": "netease",}
            (resp := requests.get(url="https://music.qinglvai.top/api/index.php", params=params, headers=headers, timeout=10, verify=False, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'song', 'url'], '')) or not str(download_url).startswith('http'): break
            with suppress(Exception): (resp := requests.get(url='https://music.qinglvai.top/api/index.php?', params={'route': '/music/detail', 'id': song_id, 'source': 'netease'}, headers=headers, timeout=10, verify=False, **request_overrides)).raise_for_status(); download_result['songDetail'] = resp2json(resp=resp)
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['songDetail', 'data', 'dt'], 0)) / 1000
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['songDetail', 'data', 'name'], None)), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(download_result, ['songDetail', 'data', 'ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(download_result, ['songDetail', 'data', 'al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['songDetail', 'data', 'al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        with suppress(Exception): resp = None; (resp := requests.get(url='https://music.qinglvai.top/api/index.php?', params={'route': '/music/lyric', 'id': song_id, 'source': 'netease'}, headers=headers, timeout=10, verify=False, **request_overrides)).raise_for_status()
        lyric_result, lyric = ({}, 'NULL') if (not locals().get('resp') or not hasattr(locals().get('resp'), 'text')) else ((lyric_result := resp2json(resp=resp)), cleanlrc(safeextractfromdict(lyric_result, ['data', 'lrc'], '') or ''))
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_parsewithbugpkapi'''
    def _parsewithbugpkapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(f'https://api.bugpk.com/api/163_music?ids={song_id}&level={music_quality}&type=json', headers=headers, timeout=10, verify=False, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')) or not str(download_url).startswith('http') or download_url.startswith('https://music.163.com/song/media/outer/url?id='): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(download_result.get('lyric') or '')))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(str(download_result.get('ar_name') or '').replace('/', ', ')), album=legalizestring(download_result.get('al_name') or safeextractfromdict(search_result, ['al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=download_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithtmetuapi'''
    def _parsewithtmetuapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", "Referer": "https://music.tmetu.cn/"}
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get("https://music.tmetu.cn/api/?miss=songAll", params={"id": song_id, "level": music_quality, "withLyric": "true"}, headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'audioUrl'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = (safeextractfromdict(download_result, ['data', 'duration'], 0) or 0) / 1000.
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring((safeextractfromdict(download_result, ['data', 'artists'], '') or '').replace('/', ',')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or ''), cover_url=safeextractfromdict(download_result, ['data', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithffapi'''
    def _parsewithffapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"}
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get("https://ffapi.cn/int/v1/netease_url", params={"id": song_id, "quality": music_quality}, headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithbileizhenapi'''
    def _parsewithbileizhenapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        decrypt_func, REQUEST_KEYS = lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8'), ['charlespikachubHpfM2NlZmEwYTFiZGE3NTA4NjE4NWM3NWQxNTZmMWNiMDQ0ZGM3NDY3MDEzNjMxYTQ1', 'charlespikachubHpfYzBkYzE5ZTI0ZGRkMTYxNjFjOWU4Yjg0MTZiYTYzYzExY2UxNzE5OGJlMTkzZGJh']
        headers.update({'X-Api-Key': decrypt_func(random.choice(REQUEST_KEYS))})
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(f'https://api.bileizhen.top/api/netease?id={song_id}&level={music_quality}', headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'artists'], None) or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithchkszapi'''
    def _parsewithchkszapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", "Referer": "https://cp.chksz.top/", "Origin": "https://cp.chksz.top", "Accept": "*/*"}
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(f'https://api.chksz.com/api/163_music?id={song_id}&level={music_quality}', headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'artist'], None) or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithxingmianapi'''
    def _parsewithxingmianapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, music_quality_mapper = request_overrides or {}, search_result['id'], {'jymaster': '超清母带', 'dolby': '杜比全景声', 'sky': '沉浸环绕声', 'jyeffect': '高清环绕声', 'hires': 'Hi-Res', 'lossless': '无损', 'exhigh': '高音质', 'standard': '低音质'}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        decrypt_func, REQUEST_KEYS = lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8'), ['charlespikachuYzY2OWY2MTI3ODAzMDEwZTQ3ZjI0ZjI2ZGEyY2Q4Y2ZkY2JkNjdiOWIzNzVjZmZhZjNjMzk1MjQ1N2Y4MTMzZA==', ]
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(f'https://api.xingmian.bbroot.com/API/netease_music_api.php?id={song_id}&quality={music_quality_mapper[music_quality]}&apikey={decrypt_func(random.choice(REQUEST_KEYS))}', timeout=10, headers=headers, verify=False, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['data', 'duration'], None))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'author'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or ''), cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithjfjtapi'''
    def _parsewithjfjtapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", 'Referer': 'https://dm.jfjt.cc/'}
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.post('https://dm.jfjt.cc/Song_V1', headers=headers, data={'url': song_id, 'level': music_quality, 'type': 'json'}, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(download_result['data']['duration']) / 1000
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'ar_name'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'al_name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=safeextractfromdict(download_result, ['data', 'lyric'], None), cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithkangqiovoapi'''
    def _parsewithkangqiovoapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", 'Referer': 'https://ncm.kangqiovo.com/'}
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.post('https://ncm.kangqiovo.com/Song_V1', headers=headers, data={'url': song_id, 'level': music_quality, 'type': 'json'}, timeout=10, verify=False, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = extractdurationsecondsfromlrc(download_result['data']['lyric'])
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'ar_name'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'al_name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=safeextractfromdict(download_result, ['data', 'lyric'], None), cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithyutangxiaowuapi'''
    def _parsewithyutangxiaowuapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(f'https://api.yutangxiaowu.cn/api/music/Song_V1?url={song_id}&level={music_quality}&type=json', headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(download_result.get('lyric') or '')))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(str(download_result.get('ar_name') or '').replace('/', ', ')), album=legalizestring(download_result.get('al_name') or safeextractfromdict(search_result, ['al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=download_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithbyfunsapi'''
    def _parsewithbyfunsapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        download_url = requests.get(f'https://api.byfuns.top/1/?id={song_id}&level=hires', headers=headers, timeout=10, **request_overrides).text.strip()
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': {}, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithcocodownloaderapi'''
    def _parsewithcocodownloaderapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        resp = requests.get(f'https://cocodownloader.markqq.com/api/url?id={song_id}&provider=netease&quality=jymaster', headers=headers, timeout=10, **request_overrides)
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithcunyuapi'''
    def _parsewithcunyuapi(self, search_result: dict, request_overrides: dict = None):
        # init
        REQUEST_KEYS, decrypt_func = ['charlespikachueXRqSm9kYkttWkMyek1qSm5NaTRudGEybXR2SHpNbkw=', ], lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8')
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(url=f'https://www.cunyuapi.top/163music_play?id={song_id}&quality={music_quality}&api_token={decrypt_func(random.choice(REQUEST_KEYS))}', timeout=10, headers=headers, verify=False, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['song_file_url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(download_result.get('lyric') or '')))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(str(download_result.get('ar_name') or '').replace('/', ', ')), album=legalizestring(download_result.get('al_name') or safeextractfromdict(search_result, ['al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=download_result.get('img'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithqjqqapi'''
    def _parsewithqjqqapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.post(url=f'https://metings.qjqq.cn/Song_V1', data={'url': song_id, 'level': music_quality, 'type': 'json'}, timeout=10, headers=headers, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or '')))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'ar_name'], None) or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'al_name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithxunjinluapi'''
    def _parsewithxunjinluapi(self, search_result: dict, request_overrides: dict = None):
        # init
        REQUEST_KEYS, headers = ['charlespikachuc2tfZDFhMzFkMDczMzYxNzE3NmY1MzZkNzBlMjI3NGVhN2Y=',], {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        decrypt_func, request_overrides, song_id = lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8'), request_overrides or {}, search_result['id']
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(f'https://api.xunjinlu.fun/apis/wymusic?action=song&id={song_id}&key={decrypt_func(random.choice(REQUEST_KEYS))}&level={music_quality}', timeout=10, headers=headers, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'data', 'url', 'url'], '')) or not str(download_url).startswith('http'): break
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['data', 'data', 'info', 'duration'], '0:00') or '0:00')
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithmanshuoapi'''
    def _parsewithmanshuoapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, headers = request_overrides or {}, search_result['id'], {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Accept": "*/*", "Origin": "https://api.manshuo.ink", "Referer": "https://api.manshuo.ink/wyy", "Content-Type": "application/x-www-form-urlencoded"}
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        (resp := requests.post(url=f'https://api.manshuo.ink/wyy/Download', data={'id': song_id, 'quality': MUSIC_QUALITIES[0]}, headers=headers, **request_overrides)).raise_for_status()
        if "audio" not in (content_type := resp.headers.get("content-type", "")) and "octet-stream" not in content_type: raise RuntimeError('No audio files returned')
        download_url_status = {'ok': True, 'download_url': {'url': 'https://api.manshuo.ink/wyy/Download', 'data': {'id': song_id, 'quality': MUSIC_QUALITIES[0]}}, 'file_size_bytes': resp.content.__sizeof__(), 'file_size': SongInfoUtils.byte2mb(resp.content.__sizeof__()), 'ext': SongInfoUtils.naiveguessextfromaudiobytes(resp.content)}
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': {}, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=None, download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content
        )
        song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithxianyuwapi'''
    def _parsewithxianyuwapi(self, search_result: dict, request_overrides: dict = None):
        # init
        decrypt_func, REQUEST_KEYS = lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8'), ['charlespikachuc2stODRiMzc5N2Y5MTg0ODFmZGE0ZDkxMWMwZjYzYjc0MzE=']
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        (resp := requests.get(f'https://apii.xianyuw.cn/api/v1/163-music-search?id={song_id}&key={decrypt_func(random.choice(REQUEST_KEYS))}&no_url=0&br=hires', headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['data']['url']) or not str(download_url).startswith('http'): return song_info
        duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(safeextractfromdict(download_result, ['data', 'lrc'], '') or '')))
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'title'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'author'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None) or safeextractfromdict(search_result, ['al', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithceseetapi'''
    def _parsewithceseetapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        headers = {"Content-Type": "application/json", "User-Agent": "lx-music-request/2.6.0", "X-Request-Key": ""}
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        (resp := requests.get(f'https://m-api.ceseet.me/url/wy/{song_id}/hires', headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['data']) or not str(download_url).startswith('http'): return song_info
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithguyueiapi'''
    def _parsewithguyueiapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36'}
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        decrypt_final_url_func = lambda encrypted_str, key=b"nsh": (lambda dec_bytes: "http" + "".join(chr(dec_bytes[i] ^ key[(i - 1) % len(key)]) for i in range(1, len(dec_bytes))).rstrip("\x00"))(base64.b64decode((lambda s: s + "=" * ((4 - len(s) % 4) % 4))("A" + encrypted_str[9:])))
        # parse
        (resp := requests.get(f'https://www.guyuei.com/music/163.php?', params={'url': f'https://music.163.com/song?id={song_id}', 'yinzhi': 'hns'}, headers=headers, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['url']) or not str(download_url := decrypt_final_url_func(download_url)).startswith('http'): return song_info
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': MUSIC_QUALITIES[0]}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithxiaotapi'''
    def _parsewithxiaotapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        (resp := requests.get(f'https://api.s0o1.com/API/wyy_music/?id={song_id}&yz=7', headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['data']['url']) or not str(download_url).startswith('http'): return song_info
        duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or '')))
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'artists'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None) or safeextractfromdict(search_result, ['al', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithxcvtsapi'''
    def _parsewithxcvtsapi(self, search_result: dict, request_overrides: dict = None):
        # init
        REQUEST_KEYS, decrypt_func = ['charlespikachuZTA5NDg3ZjVlYjNiZjJmYjIzODQyMDRlNjI3OTYyMWI=', 'charlespikachuMTQ5NThjZGYxOTVlZDc2ODY1YWRhNDM4NzZjMzcxNGM='], lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8')
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        (resp := requests.get(f"https://api.xcvts.cn/api/music/163music?apiKey={decrypt_func(random.choice(REQUEST_KEYS))}&id={song_id}&br=999000", timeout=10, headers=headers, **request_overrides)).raise_for_status()
        if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'music'], None)) or not str(download_url).startswith('http'): return song_info
        lyric = cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or 'NULL')
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'song'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'singer'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album_name'], None)), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=extractdurationsecondsfromlrc(lyric), duration=SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(lyric)), lyric=lyric, cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithgdstudioapi'''
    def _parsewithgdstudioapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        (resp := requests.get(f"https://music-api.gdstudio.xyz/api.php?types=url&id={song_id}&source=netease&br=999", timeout=10, headers=headers, **request_overrides)).raise_for_status()
        if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], None)) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithrxtoolapi'''
    def _parsewithrxtoolapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", "Referer": "https://api.rxtool.top/"}
        # parse
        (resp := requests.get(f"https://api.rxtool.top/api/meteasecloudmusic.php?id={song_id}&level=hires", timeout=10, headers=headers, **request_overrides)).raise_for_status()
        if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], None)) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(download_result.get('lyric') or '')))
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring((download_result.get('artist') or '').replace('/', ',')), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), ext=download_url_status['ext'], 
            file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=download_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithvincentzyu233api'''
    def _parsewithvincentzyu233api(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        (resp := requests.get(f"http://xwl.vincentzyu233.cn:51217/v2/music/netease?id={song_id}&quality=9", headers=headers, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], None)) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewithnanorockyapi'''
    def _parsewithnanorockyapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
        # parse
        download_url = f"https://metingapi.nanorocky.top/?server=netease&type=url&id={song_id}&br=2000"
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': {}, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if (cookies := self.default_cookies or (request_overrides := request_overrides or {}).get('cookies')) and (cookies != DEFAULT_COOKIES): return SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        l1_parser_funcs = [self._parsewithtmetuapi, self._parsewithxuanluogeapi, self._parsewithbugpkapi, self._parsewithkangqiovoapi, self._parsewithchkszapi, self._parsewithxunjinluapi, self._parsewithxingmianapi, self._parsewithznnuapi, self._parsewithxiaoqinapi, self._parsewithvincentzyu233api, self._parsewithbileizhenapi, ] # svip
        l2_parser_funcs = [self._parsewithrrvennapi, self._parsewithhaitangwapi, self._parsewithguyueiapi, self._parsewithcunyuapi, ] # svip, but unstable accounts
        l3_parser_funcs = [self._parsewithnanorockyapi, self._parsewithyutangxiaowuapi, self._parsewithqjqqapi, self._parsewithcocodownloaderapi, self._parsewithffapi, self._parsewithgdstudioapi, self._parsewithbyfunsapi, self._parsewithxiaotapi, self._parsewithxcvtsapi, self._parsewithxianyuwapi, self._parsewithjfjtapi, ] # vip
        l4_parser_funcs = [self._parsewithrxtoolapi, self._parsewithceseetapi, self._parsewithmanshuoapi, ] # vip, but unstable accounts
        for parser_func in (l1_parser_funcs + l2_parser_funcs + l3_parser_funcs + l4_parser_funcs):
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}, 'quality': MUSIC_QUALITIES[-1]})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_getsongmetainfo'''
    def _getsongmetainfo(self, song_id, request_overrides: dict = None):
        request_overrides, resp = request_overrides or {}, None
        with suppress(Exception): (resp := self.post("https://interface3.music.163.com/api/v3/song/detail", data={'c': json.dumps([{"id": song_id, "v": 0}])}, **request_overrides)).raise_for_status()
        return (safeextractfromdict(resp2json(resp=resp), ['songs', 0], {}) or {})
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac', 'm4a'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}), request_overrides or {}, song_info_flac or SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
            for music_quality in MUSIC_QUALITIES:
                if song_info_flac.with_valid_download_url and MUSIC_QUALITIES.index(music_quality) >= MUSIC_QUALITIES.index(song_info_flac.raw_data.get('quality', MUSIC_QUALITIES[-1])): song_info = song_info_flac; break
                params = {'ids': [song_id], 'level': music_quality, 'encodeType': ('mp4' if music_quality == 'dolby' else 'flac'), 'header': json.dumps({"os": "pc", "appver": "", "osver": "", "deviceId": "pyncm!", "requestId": str(random.randrange(20000000, 30000000))}), **({'immerseType': 'c51'} if music_quality == 'sky' else {})}
                params = EapiCryptoUtils.encryptparams(url='https://interface3.music.163.com/eapi/song/enhance/player/url/v1', payload=params)
                (cookies := {"os": "pc", "appver": "", "osver": "", "deviceId": "pyncm!"}).update(copy.deepcopy(self.default_cookies))
                with suppress(Exception): resp = None; (resp := self.post('https://interface3.music.163.com/eapi/song/enhance/player/url/v1', data={"params": params}, cookies=cookies, **request_overrides)).raise_for_status()
                if not (download_url := safeextractfromdict((download_result := resp2json(resp)), ['data', 0, 'url'], '')) or not str(download_url).startswith('http'): continue
                with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
                    ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        data, resp = {'id': song_id, 'cp': 'false', 'tv': '0', 'lv': '0', 'rv': '0', 'kv': '0', 'yv': '0', 'ytv': '0', 'yrv': '0'}, None
        with suppress(Exception): (resp := self.post('https://interface3.music.163.com/api/song/lyric', data=data, **request_overrides)).raise_for_status()
        lyric = cleanlrc(safeextractfromdict((lyric_result := resp2json(resp)), ['lrc', 'lyric'], '') or '')
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = {}, request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, lossless_quality_is_sufficient = request_overrides or {}, False if (cookies := self.default_cookies or request_overrides.get('cookies')) and (cookies != DEFAULT_COOKIES) else True
        search_meta, search_result_idx = copy.deepcopy(search_url), -1; search_url, page_no = search_meta.pop('url'), search_meta.pop('page')
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.post(search_url, **search_meta, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp)['result']['songs']):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}, 'quality': MUSIC_QUALITIES[-1]})
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
        with suppress(Exception): playlist_id, song_infos = parse_qs(urlparse(urlparse(playlist_url).fragment).query, keep_blank_values=True).get('id')[0], []
        if not playlist_id: playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, NETEASE_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        (resp := self.post('https://music.163.com/api/v6/playlist/detail', data={'id': playlist_id}, **request_overrides)).raise_for_status()
        tracks_in_playlist = (safeextractfromdict((playlist_result := resp2json(resp=resp)), ['playlist', 'trackIds'], []) or [])
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}, 'quality': MUSIC_QUALITIES[-1]})
                song_info_flac = self._parsewiththirdpartapis(search_result=track_info, request_overrides=request_overrides)
                lossless_quality_is_sufficient = False if (cookies := self.default_cookies or request_overrides.get('cookies')) and (cookies != DEFAULT_COOKIES) else True
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                if (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse track info {track_info}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result, ['playlist', 'name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos