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
import sys
import ssl
import hmac
import json
import copy
import time
import socket
import base64
import random
import hashlib
import warnings
import json_repair
from contextlib import suppress
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from ..utils.hosts import NETEASE_MUSIC_HOSTS, hostmatchessuffix, obtainhostname
from ..utils.neteaseutils import EapiCryptoUtils, MUSIC_QUALITIES, DEFAULT_COOKIES
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import resp2json, legalizestring, safeextractfromdict, usesearchheaderscookies, extractdurationsecondsfromlrc, useparseheaderscookies, cleanlrc, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils, RandomIPGenerator
warnings.filterwarnings('ignore')


'''NeteaseMusicClient'''
class NeteaseMusicClient(BaseMusicClient):
    source = 'NeteaseMusicClient'
    def __init__(self, **kwargs):
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
            search_urls.append({'url': base_url, 'data': page_rule})
            count += page_size
        # return
        return search_urls
    '''_parsewithxiaoqinapi'''
    def _parsewithxiaoqinapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, token = dict(request_overrides or {}), search_result['id'], hashlib.md5(f"suxiaoqings:{int(time.time() // 60)}".encode()).hexdigest()
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse download result
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.post('https://nextmusic.toubiec.cn/api/getSongUrl', json={'id': song_id, 'level': music_quality, 'token': token}, timeout=10, verify=False, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): continue
            with suppress(Exception): (resp := self.post('https://nextmusic.toubiec.cn/api/getSongInfo', json={'id': song_id, 'token': token}, timeout=10, verify=False, **request_overrides)).raise_for_status(); download_result['song_info'] = resp2json(resp=resp)
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['song_info', 'data', 'duration'], '') or '')
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['song_info', 'data', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['song_info', 'data', 'singer'], None)), album=legalizestring(safeextractfromdict(download_result, ['song_info', 'data', 'album'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['song_info', 'data', 'picimg'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        with suppress(Exception): resp = None; (resp := self.post("https://nextmusic.toubiec.cn/api/getSongLyric", json={'id': song_id, 'token': token}, timeout=10, **request_overrides)).raise_for_status()
        lyric_result, lyric = ({}, 'NULL') if (not locals().get('resp') or not hasattr(locals().get('resp'), 'text')) else ((lyric_result := resp2json(resp=resp)), cleanlrc(safeextractfromdict(lyric_result, ['data', 'lrc'], '') or ''))
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_parsewithcggapi'''
    def _parsewithcggapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result['id']
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(url=f'https://api-v2.cenguigui.cn/api/netease/music_v1.php?id={song_id}&type=json&level={music_quality}', timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['data', 'duration'], '') or '')
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or ''), cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithtmetuapi (maybe invalid)'''
    def _parsewithtmetuapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result['id']
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(url=f'https://www.tmetu.cn/api/music/api.php?miss=songAll&id={song_id}&level={music_quality}&withLyric=true', timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'audioUrl'], '')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['data', 'duration'], 0)) / 1000
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'artists'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '') or ''), cover_url=safeextractfromdict(download_result, ['data', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithrrvennapi'''
    def _parsewithrrvennapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result['id']
        # parse
        for music_quality in MUSIC_QUALITIES:
            signature = hashlib.md5(((timestamp_str := str(int(time.time()))) + 'kxz_163music_secret_key_2024').encode('utf-8')).hexdigest()
            params = {"action": "music", "url": str(song_id), "level": music_quality, "type": "json", "timestamp": timestamp_str, "signature": signature}
            with suppress(Exception): resp = None; (resp := self.get(url=f'https://music.rrvenn.cn/api/api.php', params=params, timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(str(download_result.get('ar_name', '') or '').replace('/', ', ')), album=legalizestring(download_result.get('al_name')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=song_id, duration_s=extractdurationsecondsfromlrc(download_result.get('lyric') or ''), duration=SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(download_result.get('lyric') or '')), lyric=cleanlrc(download_result.get('lyric') or ''), cover_url=download_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithznnuapi'''
    def _parsewithznnuapi(self, search_result: dict, request_overrides: dict = None):
        # init
        HMAC_SECRET_KEY, BASE_URL = b"a09d0f3700a279584e1515354fbe08a7ee1c617f919543142fa625b82f1b5ad0", "https://music.znnu.com"
        request_overrides, song_id, random_ip = request_overrides or {}, search_result['id'], RandomIPGenerator().ipv4()
        generate_signature_func = lambda params, timestamp, domain="music.znnu.com": hmac.new(HMAC_SECRET_KEY, (str(timestamp) + domain + "".join(f"{k}={v}" for k, v in sorted(((k, v) for k, v in params.items() if k not in {'signature', 'timestamp', 'domain', 'ver'}), key=lambda item: item[0]))).encode("utf-8"), hashlib.sha256).hexdigest()
        (resp := self.get(f"{BASE_URL}/api/key", timeout=10, **request_overrides)).raise_for_status()
        key_token, b64_key = resp2json(resp=resp)['data']['keyToken'], resp2json(resp=resp)['data']['key']
        headers = {"x-key-token": key_token, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": f"{BASE_URL}/"}
        # parse
        for music_quality in MUSIC_QUALITIES:
            timestamp, domain, params = int(time.time()), "music.znnu.com", {"act": "song", "id": str(song_id), "level": music_quality, "ip": random_ip}
            (payload := params.copy()).update({"timestamp": timestamp, "domain": domain, "signature": generate_signature_func(params, timestamp, domain)})
            (resp := self.post(f"{BASE_URL}/api/song", headers=headers, data=payload, **request_overrides)).raise_for_status()
            iv, ciphertext, tag, key = base64.b64decode((enc_data := (download_result := resp2json(resp=resp))['data'])['iv']), base64.b64decode(enc_data['ciphertext']), base64.b64decode(enc_data['tag']), base64.b64decode(b64_key)
            download_result = json_repair.loads(AESGCM(key).decrypt(nonce=iv, data=ciphertext + tag, associated_data=None).decode('utf-8'))
            if not (download_url := safeextractfromdict(download_result, ['url'], '')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(str(download_result.get('artist', '') or '').replace('/', ', ')), album=legalizestring(download_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=song_id, duration_s=extractdurationsecondsfromlrc(download_result.get('lrc') or ''), duration=SongInfoUtils.seconds2hms(extractdurationsecondsfromlrc(download_result.get('lrc') or '')), lyric=cleanlrc(download_result.get('lrc') or ''), cover_url=download_result.get('cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithxuanluogeapi'''
    def _parsewithxuanluogeapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result['id']
        # parse download result
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(url=f'https://music.xuanluoge.top/api.php?miss=getMusicUrl&id={song_id}&level={music_quality}', timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 0, 'url'], '')) or not str(download_url).startswith('http'): continue
            with suppress(Exception): (resp := self.get(url=f'https://music.xuanluoge.top/api.php?miss=songDetail&id={song_id}', timeout=10, **request_overrides)).raise_for_status(); download_result['songDetail'] = resp2json(resp=resp)
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['songDetail', 'data', 'dt'], 0)) / 1000
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['songDetail', 'data', 'name'], None)), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(download_result, ['songDetail', 'data', 'ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(download_result, ['songDetail', 'data', 'al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['songDetail', 'data', 'al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        with suppress(Exception): resp = None; (resp := self.get(url=f'https://music.xuanluoge.top/api.php?miss=lyric&id={song_id}', timeout=10, **request_overrides)).raise_for_status()
        lyric_result, lyric = ({}, 'NULL') if (not locals().get('resp') or not hasattr(locals().get('resp'), 'text')) else ((lyric_result := resp2json(resp=resp)), cleanlrc(safeextractfromdict(lyric_result, ['data', 'lrc'], '') or ''))
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_parsewithbugpkapi'''
    def _parsewithbugpkapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result['id']
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(f'https://api.bugpk.com/api/163_music?ids={song_id}&level={music_quality}&type=json', timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(download_result.get('lyric') or '')))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(str(download_result.get('ar_name') or '').replace('/', ', ')), album=legalizestring(download_result.get('al_name') or safeextractfromdict(search_result, ['al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=download_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithyutangxiaowuapi'''
    def _parsewithyutangxiaowuapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result['id']
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(f'https://yutangxiaowu.cn:4000/Song_V1?url={song_id}&level={music_quality}&type=json', timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(download_result.get('lyric') or '')))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(str(download_result.get('ar_name') or '').replace('/', ', ')), album=legalizestring(download_result.get('al_name') or safeextractfromdict(search_result, ['al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=download_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithnycnmbyfunsapi'''
    def _parsewithnycnmbyfunsapi(self, search_result: dict, request_overrides: dict = None):
        # init
        REQUEST_KEYS = ['OTJiMWE4ZWQyMjg5ZmI4ZTk4NTAxZWMyYzE2Yzk4MWRmMWI1NzliMjhhM2Y2ZjIyMDFiYmJlNDc2YmI3Njc0MA==']
        decrypt_func, request_overrides, song_id = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8'), request_overrides or {}, search_result['id']
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(f'https://api.nycnm.cn/API/163music.php?ids={song_id}&level={music_quality}&type=json&apikey={decrypt_func(random.choice(REQUEST_KEYS))}', timeout=10, **request_overrides)).raise_for_status(); download_result = resp2json(resp=resp)
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            with suppress(Exception): download_url = None; download_url = self.get(f'https://api.byfuns.top/1/?id={song_id}&level={music_quality}', timeout=10, **request_overrides).text.strip()
            if not download_url or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(download_result.get('lyric') or '')))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(str(download_result.get('ar_name') or '').replace('/', ', ')), album=legalizestring(download_result.get('al_name') or safeextractfromdict(search_result, ['al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=download_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithcunyuapi'''
    def _parsewithcunyuapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result['id']
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(url=f'https://www.cunyuapi.top/163music_play?id={song_id}&quality={music_quality}', timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['song_file_url'], '')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = extractdurationsecondsfromlrc((lyric := cleanlrc(download_result.get('lyric') or '')))
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(str(download_result.get('ar_name') or '').replace('/', ', ')), album=legalizestring(download_result.get('al_name') or safeextractfromdict(search_result, ['al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=lyric, cover_url=download_result.get('img'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithcyruiapi (maybe invalid)'''
    def _parsewithcyruiapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, download_result = request_overrides or {}, search_result['id'], {}
        with suppress(Exception): (resp := self.get(f'https://blog.cyrui.cn/netease/api/getSongDetail.php?id={song_id}', **request_overrides)).raise_for_status(); download_result = resp2json(resp=resp)
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(url=f'https://blog.cyrui.cn/netease/api/getMusicUrl.php?id={song_id}&level={music_quality}', timeout=10, **request_overrides)).raise_for_status(); download_result['getMusicUrl'] = resp2json(resp=resp)
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict(download_result, ['getMusicUrl', 'data', 0, 'url'], '')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(download_result, ['songs', 0, 'dt'], 0)) / 1000
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': music_quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['songs', 0, 'name'], None)), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(download_result, ['songs', 0, 'ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(download_result, ['songs', 0, 'al', 'name'], None)), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['songs', 0, 'al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithxianyuwapi'''
    def _parsewithxianyuwapi(self, search_result: dict, request_overrides: dict = None):
        # init
        decrypt_func, REQUEST_KEYS = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8'), ['c2stNTI3OWY0MGQ3ODQxZDVmZDFlODEyZWRkMzRhODg4OTQ=', 'c2stNTVkNjE0MDY2NTk1NGU4ZjY2NTFmODNhMmQ2ZWYyNmU=']
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        # parse
        (resp := self.get(f'https://apii.xianyuw.cn/api/v1/163-music-search?id={song_id}&key={decrypt_func(random.choice(REQUEST_KEYS))}&no_url=0&br=hires', **request_overrides)).raise_for_status()
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
        (resp := self.get(f'https://m-api.ceseet.me/url/wy/{song_id}/hires', headers=headers, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['data']) or not str(download_url).startswith('http'): return song_info
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('dt', 0) or 0) / 1000
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if (cookies := self.default_cookies or request_overrides.get('cookies')) and (cookies != DEFAULT_COOKIES): return SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        for parser_func in [self._parsewithcggapi, self._parsewithxiaoqinapi, self._parsewithrrvennapi, self._parsewithxuanluogeapi, self._parsewithbugpkapi, self._parsewithznnuapi, self._parsewithcunyuapi, self._parsewithyutangxiaowuapi, self._parsewithnycnmbyfunsapi, self._parsewithceseetapi, self._parsewithxianyuwapi, self._parsewithcyruiapi, self._parsewithtmetuapi]:
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
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]}), request_overrides or {}, song_info_flac or SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            if not search_result.get('name'): search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
            for music_quality in MUSIC_QUALITIES:
                if song_info_flac.with_valid_download_url and MUSIC_QUALITIES.index(music_quality) >= MUSIC_QUALITIES.index(song_info_flac.raw_data.get('quality', MUSIC_QUALITIES[-1])): song_info = song_info_flac; break
                params = {'ids': [song_id], 'level': music_quality, 'encodeType': 'flac', 'header': json.dumps({"os": "pc", "appver": "", "osver": "", "deviceId": "pyncm!", "requestId": str(random.randrange(20000000, 30000000))}), **({'immerseType': 'c51'} if music_quality == 'sky' else {})}
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

    '''_process_search_result'''
    def _process_search_result(self, search_result, request_overrides):
        if not isinstance(search_result, dict) or ('id' not in search_result): return None
        # --parse with third part apis
        song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
        # --parse with official apis
        lossless_quality_is_sufficient = False if (cookies := self.default_cookies or request_overrides.get('cookies')) and (cookies != DEFAULT_COOKIES) else True
        try:
            song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
        except Exception:
            song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        # --check valid
        if not song_info.with_valid_download_url: song_info = song_info_flac
        if not song_info.with_valid_download_url: return None
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = {}, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}; lossless_quality_is_sufficient = False if (cookies := self.default_cookies or request_overrides.get('cookies')) and (cookies != DEFAULT_COOKIES) else True
        search_meta = copy.deepcopy(search_url)
        search_url = search_meta.pop('url')
        timeout = 60
        # successful
        try:
            # --search results
            (resp := self.post(search_url, **search_meta, **request_overrides)).raise_for_status()
            search_results = resp2json(resp)['result']['songs']
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_song = {executor.submit(self._process_search_result, result, request_overrides): result for result in search_results}
                for future in as_completed(future_to_song):
                    if time.time() - start_time > timeout:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    try:
                        song_info = future.result()
                        if song_info:
                            song_infos.append(song_info)
                            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page:
                                executor.shutdown(wait=False, cancel_futures=True)
                                break
                    except Exception as e:
                        continue
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
        is_frozen = getattr(sys, 'frozen', False)
        request_overrides = request_overrides or {}
        # Debug: Log frozen mode status
        self.logger_handle.info(f'{self.source}.parseplaylist >>> Frozen mode: {is_frozen}', disable_print=self.disable_print)
        self.logger_handle.info(f'{self.source}.parseplaylist >>> Python version: {sys.version}', disable_print=self.disable_print)
        self.logger_handle.info(f'{self.source}.parseplaylist >>> SSL version: {ssl.OPENSSL_VERSION}', disable_print=self.disable_print)
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **request_overrides).url
        hostname = obtainhostname(url=playlist_url)
        if not hostname or not hostmatchessuffix(hostname, NETEASE_MUSIC_HOSTS):
            self.logger_handle.error(f'{self.source}.parseplaylist >>> Invalid hostname: {hostname}', disable_print=self.disable_print)
            return []
        try:
            playlist_id = parse_qs(urlparse(urlparse(playlist_url).fragment).query, keep_blank_values=True).get('id')[0]
            self.logger_handle.info(f'{self.source}.parseplaylist >>> Parsed playlist ID: {playlist_id}', disable_print=self.disable_print)
        except Exception as err:
            try: playlist_id = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'); assert playlist_id
            except:
                self.logger_handle.error(f'{self.source}.parseplaylist >>> Failed to parse playlist URL (Error: {err})', disable_print=self.disable_print)
                return []
        # Debug: Test basic connectivity
        try:
            socket.setdefaulttimeout(10)
            test_sock = socket.create_connection(("music.163.com", 443), timeout=10)
            test_sock.close()
            self.logger_handle.info(f'{self.source}.parseplaylist >>> Socket connectivity to music.163.com: OK', disable_print=self.disable_print)
        except Exception as sock_err:
            self.logger_handle.error(f'{self.source}.parseplaylist >>> Socket connectivity test failed: {sock_err}', disable_print=self.disable_print)
        try:
            self.logger_handle.info(f'{self.source}.parseplaylist >>> Fetching playlist detail from API...', disable_print=self.disable_print)
            resp = self.post('https://music.163.com/api/v6/playlist/detail', data={'id': playlist_id}, timeout=30, **request_overrides)
            resp.raise_for_status()
            playlist_results = resp2json(resp=resp)
            self.logger_handle.info(f'{self.source}.parseplaylist >>> Playlist detail fetched successfully', disable_print=self.disable_print)
        except Exception as err:
            self.logger_handle.error(f'{self.source}.parseplaylist >>> Failed to fetch playlist detail (Error: {err})', disable_print=self.disable_print)
            return []
        track_ids = [str(t['id']) for t in (safeextractfromdict(playlist_results, ['playlist', 'trackIds'], []) or [])]
        song_infos = []
        if not track_ids:
            self.logger_handle.error(f'{self.source}.parseplaylist >>> No track IDs found in playlist', disable_print=self.disable_print)
            return []
        self.logger_handle.info(f'{self.source}.parseplaylist >>> Found {len(track_ids)} tracks, starting to parse...', disable_print=self.disable_print)
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(track_ids)} songs found in playlist {playlist_id} >>> completed (0/{len(track_ids)})", total=len(track_ids))
            for idx, track_id in enumerate(track_ids):
                if idx > 0: main_process_context.advance(main_progress_id, 1)
                main_process_context.update(main_progress_id, description=f"{len(track_ids)} songs found in playlist {playlist_id} >>> completed ({idx}/{len(track_ids)})")
                track_info = {'id': track_id}
                song_info_flac = self._parsewiththirdpartapis(search_result=track_info, request_overrides=request_overrides)
                lossless_quality_is_sufficient = False if (cookies := self.default_cookies or request_overrides.get('cookies')) and (cookies != DEFAULT_COOKIES) else True
                try:
                    song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                except Exception:
                    song_info = song_info_flac
                if not song_info.with_valid_download_url: song_info = song_info_flac
                if song_info.with_valid_download_url: song_infos.append(song_info)
            main_process_context.advance(main_progress_id, 1)
            main_process_context.update(main_progress_id, description=f"{len(track_ids)} songs found in playlist {playlist_id} >>> completed ({idx+1}/{len(track_ids)})")
        self.logger_handle.info(f'{self.source}.parseplaylist >>> Parsing complete. Successfully parsed {len(song_infos)}/{len(track_ids)} tracks', disable_print=self.disable_print)
        playlist_name = safeextractfromdict(playlist_results, ['playlist', 'name'], None)
        song_infos = self._removeduplicates(song_infos=song_infos)
        work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos
