'''
Function:
    Implementation of KugouMusicClient: http://www.kugou.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import time
import random
import base64
import hashlib
import requests
import warnings
import json_repair
from contextlib import suppress
from urllib.parse import urlencode
from typing_extensions import Unpack
from pathvalidate import sanitize_filepath
from ..utils.hosts import KUGOU_MUSIC_HOSTS
from urllib.parse import urlparse, parse_qs, urljoin
from .base import BaseMusicClient, BaseMusicClientKwargs
from ..utils.kugouutils import KugouMusicClientUtils, MUSIC_QUALITIES
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils
warnings.filterwarnings('ignore')


'''KugouMusicClient'''
class KugouMusicClient(BaseMusicClient):
    source = 'KugouMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(KugouMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_parse_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_download_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"format": "json", "keyword": keyword, "platform": "WebFilter", "page": 1, "pagesize": 30}).update(rule)
        # construct search urls
        base_url, search_urls, page_size, count = 'https://songsearch.kugou.com/song_search_v2?', [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['pagesize'] = page_size
            page_rule['page'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithhaitangwapi'''
    def _parsewithhaitangwapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, file_hash, MUSIC_QUALITIES = request_overrides or {}, search_result.get('hash') or search_result.get('FileHash'), ['hires', 'lossless', 'exhigh']
        if not (search_result.get('duration') or search_result.get('Duration') or search_result.get('timelen')): search_result.update(self._getsongmetainfo(song_id=file_hash, request_overrides=request_overrides))
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := requests.get(f"https://musicapi.haitangw.net/kgqq/kg.php?type=json&id={file_hash}&level={music_quality}", timeout=10, headers=headers, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): (resp := requests.get(f"https://music.haitangw.cc/kgqq/kg.php?type=json&id={file_hash}&level={music_quality}", headers=headers, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := json_repair.loads(resp.text)), ['data', 'url'], '')) or not str(download_url).startswith('http'): break
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or search_result.get('Duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('songname') or search_result.get('SongName') or search_result.get('songname_original') or search_result.get('OriSongName') or search_result.get('filename') or search_result.get('FileName') or search_result.get('name') or search_result.get('Name')), singers=legalizestring(search_result.get('singername') or search_result.get('SingerName') or ', '.join([singer.get('name') for singer in (search_result.get('singerinfo') or search_result.get('Singers') or []) if isinstance(singer, dict) and singer.get('name')])), 
                album=legalizestring(search_result.get('album_name') or search_result.get('AlbumName') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=file_hash, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['trans_param', 'union_cover'], None) or search_result.get('cover_url') or search_result.get('Image'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.cover_url and isinstance(song_info.cover_url, str) and ('{size}' in song_info.cover_url): song_info.cover_url = song_info.cover_url.format(size=300)
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': download_result, 'lyric': {}}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithcocodownloaderapi'''
    def _parsewithcocodownloaderapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, file_hash = request_overrides or {}, search_result.get('hash') or search_result.get('FileHash')
        if not (search_result.get('duration') or search_result.get('Duration') or search_result.get('timelen')): search_result.update(self._getsongmetainfo(song_id=file_hash, request_overrides=request_overrides))
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        (resp := requests.get(f"https://cocodownloader.markqq.com/api/url?id={file_hash}&provider=kugou", timeout=10, headers=headers, **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], '')
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or search_result.get('Duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('songname') or search_result.get('SongName') or search_result.get('songname_original') or search_result.get('OriSongName') or search_result.get('filename') or search_result.get('FileName') or search_result.get('name') or search_result.get('Name')), singers=legalizestring(search_result.get('singername') or search_result.get('SingerName') or ', '.join([singer.get('name') for singer in (search_result.get('singerinfo') or search_result.get('Singers') or []) if isinstance(singer, dict) and singer.get('name')])), 
            album=legalizestring(search_result.get('album_name') or search_result.get('AlbumName') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=file_hash, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['trans_param', 'union_cover'], None) or search_result.get('cover_url') or search_result.get('Image'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        if song_info.cover_url and isinstance(song_info.cover_url, str) and ('{size}' in song_info.cover_url): song_info.cover_url = song_info.cover_url.format(size=300)
        # return
        return song_info
    '''_parsewithbakaapi'''
    def _parsewithbakaapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, file_hash = {'verify': False, **(request_overrides or {})}, search_result.get('hash') or search_result.get('FileHash')
        if not (search_result.get('duration') or search_result.get('Duration') or search_result.get('timelen')): search_result.update(self._getsongmetainfo(song_id=file_hash, request_overrides=request_overrides))
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",}
        # parse
        download_url = requests.get(f"https://api.baka.plus/meting/?server=kugou&type=url&id={file_hash}&br=2000", headers=headers, allow_redirects=True, stream=True, **request_overrides).url
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or search_result.get('Duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('songname') or search_result.get('SongName') or search_result.get('songname_original') or search_result.get('OriSongName') or search_result.get('filename') or search_result.get('FileName') or search_result.get('name') or search_result.get('Name')), singers=legalizestring(search_result.get('singername') or search_result.get('SingerName') or ', '.join([singer.get('name') for singer in (search_result.get('singerinfo') or search_result.get('Singers') or []) if isinstance(singer, dict) and singer.get('name')])), 
            album=legalizestring(search_result.get('album_name') or search_result.get('AlbumName') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=file_hash, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['trans_param', 'union_cover'], None) or search_result.get('cover_url') or search_result.get('Image'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        if song_info.cover_url and isinstance(song_info.cover_url, str) and ('{size}' in song_info.cover_url): song_info.cover_url = song_info.cover_url.format(size=300)
        # return
        return song_info
    '''_parsewithlzmhhhapi'''
    def _parsewithlzmhhhapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, file_hash = request_overrides or {}, search_result.get('hash') or search_result.get('FileHash')
        if not (search_result.get('duration') or search_result.get('Duration') or search_result.get('timelen')): search_result.update(self._getsongmetainfo(song_id=file_hash, request_overrides=request_overrides))
        # parse
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36", "Referer": "https://music.lzmhhh.com/", "Origin": "https://music.lzmhhh.com"}
        (resp := requests.post('https://music.lzmhhh.com/api/music/url', headers=headers, data={'id': file_hash, 'type': 'kg'}, timeout=10, **request_overrides)).raise_for_status()
        if not (download_url := (download_result := resp2json(resp=resp))['data']) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or search_result.get('Duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('songname') or search_result.get('SongName') or search_result.get('songname_original') or search_result.get('OriSongName') or search_result.get('filename') or search_result.get('FileName') or search_result.get('name') or search_result.get('Name')), singers=legalizestring(search_result.get('singername') or search_result.get('SingerName') or ', '.join([singer.get('name') for singer in (search_result.get('singerinfo') or search_result.get('Singers') or []) if isinstance(singer, dict) and singer.get('name')])), 
            album=legalizestring(search_result.get('album_name') or search_result.get('AlbumName') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=file_hash, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['trans_param', 'union_cover'], None) or search_result.get('cover_url') or search_result.get('Image'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        if song_info.cover_url and isinstance(song_info.cover_url, str) and ('{size}' in song_info.cover_url): song_info.cover_url = song_info.cover_url.format(size=300)
        # return
        return song_info
    '''_parsewith317akapi'''
    def _parsewith317akapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, file_hash, MUSIC_QUALITIES = request_overrides or {}, search_result.get('hash') or search_result.get('FileHash'), ['6', '5', '4', '3', '2', '1']
        if not (search_result.get('duration') or search_result.get('Duration') or search_result.get('timelen')): search_result.update(self._getsongmetainfo(song_id=file_hash, request_overrides=request_overrides))
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"}
        REQUEST_KEYS, decrypt_func = ['charlespikachuUE9WTUhLSklYOEE3SUdIMkZNMVA=', 'charlespikachuWE1VS0lBSjNQOExQWDNQOTcxS1U=', 'charlespikachuN0tUSTUyVDdWTE9EUjZTVDM3UFQ='], lambda t: base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8')
        # parse
        for music_quality in MUSIC_QUALITIES:
            (resp := requests.get(f"https://api.317ak.com/api/yinyue/kugougl?ckey={decrypt_func(random.choice(REQUEST_KEYS))}&i={file_hash}&br={music_quality}&type=json&lrc=1", headers=headers, timeout=10, verify=False, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['url'], None)) or not str(download_url).startswith('http'): break
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or search_result.get('Duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('songName')), singers=legalizestring(download_result.get('artistName')), album=legalizestring(download_result.get('albumName')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=file_hash, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(download_result.get('lyric') or ''), cover_url=download_result.get('cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': download_result, 'lyric': {}}) if (song_info.file_size_bytes * 8 < 320000 * song_info.duration_s) else song_info
        # return
        return song_info
    '''_parsewithjbsouapi'''
    def _parsewithjbsouapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, file_hash, base_url, session = request_overrides or {}, search_result.get('hash') or search_result.get('FileHash'), 'https://www.jbsou.cn/', requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"})
        headers = {"Origin": "https://www.jbsou.cn", "X-Requested-With": "XMLHttpRequest", "Referer": "https://www.jbsou.cn/", "Accept": "application/json, text/javascript, */*; q=0.01", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Accept-Encoding": "gzip, deflate, br, zstd", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"}
        if not (search_result.get('duration') or search_result.get('Duration') or search_result.get('timelen')): search_result.update(self._getsongmetainfo(song_id=file_hash, request_overrides=request_overrides))
        # init session
        (resp := session.get(base_url, headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "Accept-Encoding": "gzip, deflate, br, zstd", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"}, **request_overrides)).raise_for_status()
        # parse download result
        (resp := session.post(base_url, data={'input': file_hash, 'filter': 'id', 'type': 'kugou', 'page': '1'}, headers=headers, verify=False, timeout=30, **request_overrides)).raise_for_status()
        download_url = urljoin(base_url, safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 0, 'url'], '') or '')
        cover_url = urljoin(base_url, safeextractfromdict(download_result, ['data', 0, 'cover'], '') or '')
        lyric_url = urljoin(base_url, safeextractfromdict(download_result, ['data', 0, 'lrc'], '') or '')
        with suppress(Exception): download_url = session.head(download_url, allow_redirects=True, **request_overrides).url
        with suppress(Exception): cover_url = session.head(cover_url, timeout=10, allow_redirects=True, **request_overrides).url
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or search_result.get('Duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 0, 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 0, 'artist'], None)), album=legalizestring(search_result.get('album_name') or search_result.get('AlbumName') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)),
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=file_hash, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=cover_url, download_url=download_url_status['download_url'], download_url_status=download_url_status,
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        with suppress(Exception): (resp := session.get(lyric_url, allow_redirects=True, **request_overrides)).raise_for_status(); song_info.lyric = cleanlrc(resp.text.split('</script>', 1)[-1])
        # return
        return song_info
    '''_parsewith90svipapi'''
    def _parsewith90svipapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, file_hash, base_url = request_overrides or {}, search_result.get('hash') or search_result.get('FileHash'), 'https://music.90svip.cn/'
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", "Referer": "https://music.90svip.cn/", "Accept": "application/json, text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest"}
        if not (search_result.get('duration') or search_result.get('Duration') or search_result.get('timelen')): search_result.update(self._getsongmetainfo(song_id=file_hash, request_overrides=request_overrides))
        # parse download result
        (resp := requests.post('https://music.90svip.cn/', data={'input': file_hash, 'filter': 'id', 'type': 'kugou', 'page': '1'}, headers=headers, **request_overrides)).raise_for_status()
        download_url = urljoin(base_url, safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 0, 'url'], ''))
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or search_result.get('Duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
        cover_url = urljoin(base_url, safeextractfromdict(download_result, ['data', 0, 'cover'], '') or '')
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 0, 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 0, 'artist'], None)), album=legalizestring(search_result.get('album_name') or search_result.get('AlbumName') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=file_hash, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=cover_url, download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        lyric_url = urljoin(base_url, safeextractfromdict(download_result, ['data', 0, 'lrc'], '') or '')
        with suppress(Exception): (resp := requests.get(lyric_url, headers=headers, allow_redirects=True, **request_overrides)).raise_for_status(); song_info.lyric = cleanlrc(resp.text)
        # return
        return song_info
    '''_parsewithtomapi'''
    def _parsewithtomapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, file_hash, base_url = request_overrides or {}, search_result.get('hash') or search_result.get('FileHash'), 'https://music.tom.moe/'
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36", "Referer": "https://music.tom.moe/", "Accept": "application/json, text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest"}
        if not (search_result.get('duration') or search_result.get('Duration') or search_result.get('timelen')): search_result.update(self._getsongmetainfo(song_id=file_hash, request_overrides=request_overrides))
        # parse download result
        (resp := requests.post('https://music.tom.moe/', data={'input': file_hash, 'filter': 'id', 'type': 'kugou', 'page': '1'}, headers=headers, **request_overrides)).raise_for_status()
        download_url = urljoin(base_url, safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 0, 'url'], ''))
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or search_result.get('Duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
        cover_url = urljoin(base_url, safeextractfromdict(download_result, ['data', 0, 'cover'], '') or '')
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 0, 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 0, 'artist'], None)), album=legalizestring(search_result.get('album_name') or search_result.get('AlbumName') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=file_hash, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=cover_url, download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        lyric_url = urljoin(base_url, safeextractfromdict(download_result, ['data', 0, 'lrc'], '') or '')
        with suppress(Exception): (resp := requests.get(lyric_url, headers=headers, allow_redirects=True, **request_overrides)).raise_for_status(); song_info.lyric = cleanlrc(resp.text)
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        l1_parser_funcs = [self._parsewith317akapi, ] # svip
        l2_parser_funcs = [self._parsewithlzmhhhapi, self._parsewith90svipapi, self._parsewithtomapi, self._parsewithjbsouapi, ] # vip
        l3_parser_funcs = [self._parsewithbakaapi, self._parsewithcocodownloaderapi, self._parsewithhaitangwapi, ] # invalid or unstable accounts
        for parser_func in (l1_parser_funcs + l2_parser_funcs + l3_parser_funcs):
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_getsongmetainfo'''
    def _getsongmetainfo(self, song_id, request_overrides: dict = None):
        request_overrides, song_id, resp = request_overrides or {}, str(song_id).strip().upper(), None
        with suppress(Exception): (resp := self.get("https://m.kugou.com/app/i/getSongInfo.php", params={"cmd": "playInfo", "hash": song_id}, **request_overrides)).raise_for_status()
        if not (song_detail := resp2json(resp=resp)): return song_detail
        duration = float(song_detail.get("timeLength") or safeextractfromdict(song_detail, ["extra", "128timelength"], 0) or 0) / 1000
        with suppress(Exception): (resp := self.get("http://mobilecdnbj.kugou.com/api/v3/album/info", params={"albumid": song_detail["albumid"], "version": "9108", "plat": "0"}, **request_overrides)).raise_for_status()
        cover_url = ((album_info := (resp2json(resp=resp).get('data') or {})).get("imgurl") or song_detail.get("album_img") or "").replace("{size}", "400")
        return {"songname": song_detail.get("songName"), "singername": song_detail.get("singerName"), "album_name": album_info.get("albumname"), "duration": duration, "cover_url": cover_url, "song_detail": song_detail, "album_info": album_info}
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('hash') or search_result.get('FileHash'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or search_result.get('Duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
            for music_quality in MUSIC_QUALITIES:
                if ('impersonate' not in (per_request_overrides := copy.deepcopy(request_overrides))) and self.enable_curl_cffi: per_request_overrides['impersonate'] = random.choice(self.cc_impersonates)
                per_request_overrides['proxies'] = per_request_overrides.pop('proxies', None) or self._autosetproxies()
                with suppress(Exception): download_result = None; download_result: dict = KugouMusicClientUtils.getsongurl(self.session, hash_value=song_id, quality=music_quality, request_overrides=per_request_overrides, cookies=copy.deepcopy(per_request_overrides.pop('cookies', None) or self.default_cookies))
                download_url = safeextractfromdict(download_result, ['url'], '') or safeextractfromdict(download_result, ['backupUrl'], '')
                download_url, md5_hex = list(download_url)[0] if download_url and isinstance(download_url, (list, tuple)) else download_url, hashlib.md5((str(song_id) + 'kgcloudv2').encode("utf-8")).hexdigest()
                if not download_url or not str(download_url).startswith('http'): (resp := self.get(f"https://trackercdn.kugou.com/i/v2/?cdnBackup=1&behavior=download&pid=1&cmd=21&appid=1001&hash={song_id}&key={md5_hex}", **request_overrides)).raise_for_status(); download_result: dict = resp2json(resp=resp)
                download_url_kgcloudv2 = safeextractfromdict(download_result, ['url'], '') or safeextractfromdict(download_result, ['backup_url'], '') or safeextractfromdict(download_result, ['backupUrl'], '') or safeextractfromdict(download_result, ['mp3Url'], '') or safeextractfromdict(download_result, ['backupMp3Url'], '')
                download_url_kgcloudv2 = list(download_url_kgcloudv2)[0] if download_url_kgcloudv2 and isinstance(download_url_kgcloudv2, (list, tuple)) else download_url_kgcloudv2
                if not (download_url := download_url if download_url and str(download_url).startswith('http') else download_url_kgcloudv2) or not str(download_url).startswith('http'): break
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('songname') or search_result.get('SongName') or search_result.get('songname_original') or search_result.get('OriSongName') or search_result.get('filename') or search_result.get('FileName') or search_result.get('name') or search_result.get('Name')), singers=legalizestring(search_result.get('singername') or search_result.get('SingerName') or ', '.join([singer.get('name') for singer in (search_result.get('singerinfo') or search_result.get('Singers') or []) if isinstance(singer, dict) and singer.get('name')])), 
                    album=legalizestring(search_result.get('album_name') or search_result.get('AlbumName') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['trans_param', 'union_cover'], None) or search_result.get('cover_url') or search_result.get('Image'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info.cover_url and isinstance(song_info.cover_url, str) and ('{size}' in song_info.cover_url): song_info.cover_url = song_info.cover_url.format(size=300)
                if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        params, lyric_result, lyric = {'keyword': search_result.get('filename') or search_result.get('FileName') or '', 'duration': search_result.get('duration') or search_result.get('Duration') or '-1', 'hash': song_id}, {}, 'NULL'
        with suppress(Exception): (resp := self.get('http://lyrics.kugou.com/search', params=params, **request_overrides)).raise_for_status(); lyric_result = resp2json(resp=resp); (resp := self.get(f"http://lyrics.kugou.com/download?ver=1&client=pc&id={lyric_result['candidates'][0]['id']}&accesskey={lyric_result['candidates'][0]['accesskey']}&fmt=lrc&charset=utf8", **request_overrides)).raise_for_status(); lyric_result['lyrics.kugou.com/download'] = resp2json(resp=resp); lyric = cleanlrc(base64.b64decode(lyric_result['lyrics.kugou.com/download']['content']).decode('utf-8') or '')
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, lossless_quality_is_sufficient = request_overrides or {}, False if self.default_cookies or request_overrides.get('cookies') else True
        page_no, search_result_idx = int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('page')[0])), -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp)['data']['lists']):
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
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, KUGOU_MUSIC_HOSTS)): return song_infos
        assert 'special/single/' in urlparse(playlist_url).path, 'kugou playlist link must look like "https://www.kugou.com/yy/special/single/6914288.html"'
        headers = {'User-Agent': 'Android9-AndroidPhone-11239-18-0-playlist-wifi', 'Host': 'gatewayretry.kugou.com', 'x-router': 'pubsongscdn.kugou.com', 'mid': '239526275778893399526700786998289824956', 'dfid': '-', 'clienttime': str(time.time()).split('.')[0]}
        # get tracks in playlist
        tracks_in_playlist, page, playlist_result_first = [], 1, {}
        kugou_signature_func = lambda api_url: hashlib.md5(("OIlwieks28dk2k092lksi2UIkp" + "".join(sorted(str(api_url).split("?", 1)[1].split("&"))) + "OIlwieks28dk2k092lksi2UIkp").encode("utf-8")).hexdigest()
        while True:
            api_url = f'http://gatewayretry.kugou.com/v2/get_other_list_file?specialid={playlist_id}&need_sort=1&module=CloudMusic&clientver=11239&pagesize=300&specalidpgc={playlist_id}&userid=0&page={page}&type=0&area_code=1&appid=1005'
            with suppress(Exception): (resp := self.get(api_url + '&signature=' + kugou_signature_func(api_url), headers=headers, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['data', 'info'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['data', 'info'], [])); page += 1; del resp
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['data', 'count'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["hash"]: d for d in tracks_in_playlist}.values())
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
        with suppress(Exception): playlist_name = None; (resp := self.get(playlist_url, headers={'referer': 'https://www.kugou.com/songlist/'}, **request_overrides)).raise_for_status(); playlist_name = json_repair.loads(re.search(r'var\s+specialInfo\s*=\s*(\{.*?\});', resp.text, re.S).group(1))['name']
        playlist_name = legalizestring(playlist_name or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos