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
import warnings
import json_repair
from contextlib import suppress
from typing import TYPE_CHECKING
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from pathvalidate import sanitize_filepath
from ..utils.hosts import KUGOU_MUSIC_HOSTS
from urllib.parse import urlparse, parse_qs, urljoin
from ..utils.kugouutils import KugouMusicClientUtils, MUSIC_QUALITIES
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, optionalimport, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils
warnings.filterwarnings('ignore')


'''KugouMusicClient'''
class KugouMusicClient(BaseMusicClient):
    source = 'KugouMusicClient'
    def __init__(self, **kwargs):
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
        (default_rule := {"format": "json", "keyword": keyword, "showtype": 1, "page": 1, "pagesize": 10}).update(rule)
        # construct search urls
        base_url, search_urls, page_size, count = 'http://mobilecdn.kugou.com/api/v3/search/song?', [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['pagesize'] = page_size
            page_rule['page'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithcggapi'''
    def _parsewithcggapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        curl_cffi, request_overrides, file_hash, MUSIC_QUALITIES = optionalimport('curl_cffi'), request_overrides or {}, search_result['hash'], ['lossless', 'exhigh', 'standard']
        if TYPE_CHECKING and curl_cffi is not None: import curl_cffi as curl_cffi
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := curl_cffi.requests.get(f"https://music-api2.cenguigui.cn/?kg=&id={file_hash}&type=song&format=json&level={music_quality}", timeout=10, impersonate="chrome131", verify=False, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := json_repair.loads(resp.text)), ['data', 'url'], '')) or not str(download_url).startswith('http'): continue
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(search_result.get('album_name') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=file_hash, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.ext.startswith('m'): continue # encrypted format like mgg, skip by default
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithchangqingapi'''
    def _parsewithchangqingapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, file_hash, MUSIC_QUALITIES = request_overrides or {}, search_result['hash'], ['hires', 'lossless', 'exhigh', 'standard']
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.get(f"http://175.27.166.236/kgqq/kg.php?type=json&id={file_hash}&level={music_quality}", timeout=10, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): break
            if not (download_url := safeextractfromdict((download_result := json_repair.loads(resp.text)), ['data', 'url'], '')) or not str(download_url).startswith('http'): continue
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = to_seconds_func(safeextractfromdict(download_result, ['data', 'duration'], None))
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=file_hash, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lrc'], '') or ''), cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.ext.startswith('m'): continue # encrypted format like mgg, skip by default
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithjbsouapi'''
    def _parsewithjbsouapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, file_hash, base_url = request_overrides or {}, search_result['hash'], 'https://www.jbsou.cn/'
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "content-type": "application/x-www-form-urlencoded; charset=UTF-8", "origin": "https://www.jbsou.cn", 
            "priority": "u=1, i", "referer": "https://www.jbsou.cn/", "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"', "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"', "sec-fetch-dest": "empty", "x-requested-with": "XMLHttpRequest", 
            "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36", 
        }
        # parse download result
        (resp := self.post('https://www.jbsou.cn/', data={'input': file_hash, 'filter': 'id', 'type': 'kugou', 'page': '1'}, headers=headers, **request_overrides)).raise_for_status()
        download_url = urljoin(base_url, safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 0, 'url'], ''))
        with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
        cover_url = urljoin(base_url, safeextractfromdict(download_result, ['data', 0, 'cover'], '') or '')
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 0, 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 0, 'artist'], None)), album=legalizestring(search_result.get('album_name') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=file_hash, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=cover_url, download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        lyric_url = urljoin(base_url, safeextractfromdict(download_result, ['data', 0, 'lrc'], '') or '')
        with suppress(Exception): (resp := self.get(lyric_url, headers=headers, allow_redirects=True, **request_overrides)).raise_for_status(); song_info.lyric = cleanlrc(resp.text)
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for parser_func in [self._parsewithchangqingapi, self._parsewithcggapi, self._parsewithjbsouapi]:
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('hash'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(search_result.get('duration', 0) or 0) or (float(search_result.get('timelen', 0) or 0) / 1000)
            for music_quality in MUSIC_QUALITIES:
                if ('impersonate' not in (per_request_overrides := copy.deepcopy(request_overrides))) and self.enable_curl_cffi: per_request_overrides['impersonate'] = random.choice(self.cc_impersonates)
                per_request_overrides['proxies'] = per_request_overrides.pop('proxies', None) or self._autosetproxies()
                with suppress(Exception): download_result = None; download_result: dict = KugouMusicClientUtils.getsongurl(self.session, hash_value=song_id, quality=music_quality, request_overrides=per_request_overrides, cookies=copy.deepcopy(per_request_overrides.pop('cookies', None) or self.default_cookies))
                download_url = safeextractfromdict(download_result, ['url'], '') or safeextractfromdict(download_result, ['backupUrl'], '')
                download_url, md5_hex = list(download_url)[0] if download_url and isinstance(download_url, (list, tuple)) else download_url, hashlib.md5((str(song_id) + 'kgcloudv2').encode("utf-8")).hexdigest()
                if not download_url or not str(download_url).startswith('http'): (resp := self.get(f"https://trackercdn.kugou.com/i/v2/?cdnBackup=1&behavior=download&pid=1&cmd=21&appid=1001&hash={song_id}&key={md5_hex}", **request_overrides)).raise_for_status(); download_result: dict = resp2json(resp=resp)
                download_url_kgcloudv2 = safeextractfromdict(download_result, ['url'], '') or safeextractfromdict(download_result, ['backup_url'], '') or safeextractfromdict(download_result, ['backupUrl'], '') or safeextractfromdict(download_result, ['mp3Url'], '') or safeextractfromdict(download_result, ['backupMp3Url'], '')
                download_url_kgcloudv2 = list(download_url_kgcloudv2)[0] if download_url_kgcloudv2 and isinstance(download_url_kgcloudv2, (list, tuple)) else download_url_kgcloudv2
                if not (download_url := download_url if download_url and str(download_url).startswith('http') else download_url_kgcloudv2) or not str(download_url).startswith('http'): continue
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('songname') or search_result.get('songname_original') or search_result.get('filename') or search_result.get('name')), singers=legalizestring(search_result.get('singername') or ', '.join([singer.get('name') for singer in (search_result.get('singerinfo') or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(search_result.get('album_name') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), 
                    ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['trans_param', 'union_cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info.cover_url and isinstance(song_info.cover_url, str) and ('{size}' in song_info.cover_url): song_info.cover_url = song_info.cover_url.format(size=300)
                if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        params, lyric_result, lyric = {'keyword': search_result.get('filename', ''), 'duration': search_result.get('duration', '99999'), 'hash': song_id}, {}, 'NULL'
        with suppress(Exception): (resp := self.get('http://lyrics.kugou.com/search', params=params, **request_overrides)).raise_for_status(); lyric_result = resp2json(resp=resp); (resp := self.get(f"http://lyrics.kugou.com/download?ver=1&client=pc&id={lyric_result['candidates'][0]['id']}&accesskey={lyric_result['candidates'][0]['accesskey']}&fmt=lrc&charset=utf8", **request_overrides)).raise_for_status(); lyric_result['lyrics.kugou.com/download'] = resp2json(resp=resp); lyric = cleanlrc(base64.b64decode(lyric_result['lyrics.kugou.com/download']['content']).decode('utf-8') or '')
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, lossless_quality_is_sufficient = request_overrides or {}, False if self.default_cookies or request_overrides.get('cookies') else True
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp)['data']['info']:
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
                self.logger_handle.warning(f'Fail to parse song id {song_info.identifier} >>> {song_info.album} {song_info.song_name} {song_info.singers} {song_info.download_url}', disable_print=self.disable_print)
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