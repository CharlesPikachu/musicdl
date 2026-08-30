'''
Function:
    Implementation of XimalayaMusicClient: https://www.ximalaya.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import time
import math
import copy
import base64
import binascii
from Crypto.Cipher import AES
from contextlib import suppress
from rich.progress import Progress
from typing_extensions import Unpack
from urllib.parse import urlencode, urlparse, parse_qs
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import resp2json, legalizestring, usesearchheaderscookies, safeextractfromdict, SongInfo, SongInfoUtils, AudioLinkTester


'''XimalayaMusicClient'''
class XimalayaMusicClient(BaseMusicClient):
    source = 'XimalayaMusicClient'
    ALLOWED_SEARCH_TYPES = ['album', 'track']
    QUALITY_ORDER = ['M4A_128', 'MP3_64', 'MP3_32']
    KEY_A = [204, 53, 135, 197, 39, 73, 58, 160, 79, 24, 12, 83, 180, 250, 101, 60, 206, 30, 10, 227, 36, 95, 161, 16, 135, 150, 235, 116, 242, 116, 165, 171]
    SBOX_O = [
        183, 174, 108, 16, 131, 159, 250, 5, 239, 110, 193, 202, 153, 137, 251, 176, 119, 150, 47, 204, 97, 237, 1, 71, 177, 42, 88, 218, 166, 82, 87, 94, 14, 195, 69, 127, 215, 240, 225, 197, 238, 142, 123, 44, 219, 50, 190, 29,
        181, 186, 169, 98, 139, 185, 152, 13, 141, 76, 6, 157, 200, 132, 182, 49, 20, 116, 136, 43, 155, 194, 101, 231, 162, 242, 151, 213, 53, 60, 26, 134, 211, 56, 28, 223, 107, 161, 199, 15, 229, 61, 96, 41, 66, 158, 254, 21, 165,
        253, 103, 89, 3, 168, 40, 246, 81, 95, 58, 31, 172, 78, 99, 45, 148, 187, 222, 124, 55, 203, 235, 64, 68, 149, 180, 35, 113, 207, 118, 111, 91, 38, 247, 214, 7, 212, 209, 189, 241, 18, 115, 173, 25, 236, 121, 249, 75, 57,
        216, 10, 175, 112, 234, 164, 70, 206, 198, 255, 140, 230, 12, 32, 83, 46, 245, 0, 62, 227, 72, 191, 156, 138, 248, 114, 220, 90, 84, 170, 128, 19, 24, 122, 146, 80, 39, 37, 8, 34, 22, 11, 93, 130, 63, 154, 244, 160, 144, 79,
        23, 133, 92, 54, 102, 210, 65, 67, 27, 196, 201, 106, 143, 52, 74, 100, 217, 179, 48, 233, 126, 117, 184, 226, 85, 171, 167, 86, 2, 147, 17, 135, 228, 252, 105, 30, 192, 129, 178, 120, 36, 145, 51, 163, 77, 205, 73, 4, 188,
        125, 232, 33, 243, 109, 224, 104, 208, 221, 59, 9,
    ]
    def __init__(self, allowed_search_types: list = None, **kwargs: Unpack[BaseMusicClientKwargs]):
        self.allowed_search_types = list(set(allowed_search_types or XimalayaMusicClient.ALLOWED_SEARCH_TYPES))
        super(XimalayaMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36', 'Accept': 'application/json, text/plain, */*'}
        self.default_download_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'core': None, 'kw': keyword, 'page': 1, 'rows': self.search_size_per_page, 'spellchecker': 'true', 'condition': 'relation', 'device': 'web'}).update(rule)
        # construct search urls
        page_size, search_urls, base_url = self.search_size_per_page, [], 'https://www.ximalaya.com/revision/search?'
        for search_type in XimalayaMusicClient.ALLOWED_SEARCH_TYPES:
            if search_type not in self.allowed_search_types: continue
            (default_rule_search_type := copy.deepcopy(default_rule))['core'], count = search_type, 0
            while self.search_size_per_source > count:
                (page_rule := copy.deepcopy(default_rule_search_type))['rows'] = str(page_size)
                page_rule['page'] = str(int(count // page_size) + 1)
                search_urls.append(base_url + urlencode(page_rule))
                count += page_size
        return search_urls
    '''base62'''
    @staticmethod
    def base62(num: int):
        chars, out = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', ''
        while ((out := chars[num % 62] + out), (num := num // 62))[1] > 0: pass
        return out.rjust(8, '0')
    '''getxmsign'''
    @staticmethod
    def getxmsign(now: int = None):
        head = f'{os.urandom(4).hex()}{os.urandom(2).hex()}{XimalayaMusicClient.base62(int(time.time() * 1000) if now is None else int(now))}0202'
        crc, key = f'{binascii.crc32(head.encode()) & 0xffffffff:08x}', b'y3hbnr8d4s2ztjbc'
        raw = (head + crc).encode(); padding = 16 - len(raw) % 16; raw += bytes([padding]) * padding
        sid = base64.urlsafe_b64encode(AES.new(key, AES.MODE_CBC, iv=key).encrypt(raw)).decode().rstrip('=')
        return f'&&{sid}_2'
    '''decryptplayurl'''
    @staticmethod
    def decryptplayurl(encrypted_url: str):
        if not encrypted_url or not isinstance(encrypted_url, str): return ''
        if len((encrypted_data := base64.b64decode(encrypted_url.replace('_', '/').replace('-', '+') + '=' * ((4 - len(encrypted_url) % 4) % 4)))) < 16: return encrypted_url
        data, iv = encrypted_data[:-16], encrypted_data[-16:]
        out = bytearray(XimalayaMusicClient.SBOX_O[x] for x in data)
        for i in range(len(out)): out[i] ^= iv[i % 16]
        for i in range(len(out)): out[i] ^= XimalayaMusicClient.KEY_A[i % 32]
        return bytes(out).decode('utf-8', errors='ignore')
    '''_parsewithtelecomapi'''
    def _parsewithtelecomapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('id') or search_result.get('trackId'), SongInfo(source=self.source)
        # parse
        (resp := self.get(f"https://api.telecom.ac.cn/ximalaya?all=0&trackid={song_id}", timeout=10, **request_overrides)).raise_for_status()
        audio_candidates: list[dict] = safeextractfromdict((download_result := resp2json(resp=resp)), ['AudioUrls'], []) or []
        for audio_candidate in audio_candidates:
            download_url_status: dict = self.audio_link_tester.test(url=audio_candidate.get('url'), request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('AudioName') or search_result.get('title') or search_result.get('trackName')), singers=legalizestring(search_result.get('nickname') or search_result.get('anchorName')), album=legalizestring(search_result.get('album_title') or search_result.get('albumTitle') or search_result.get('albumName')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=song_id, duration_s=int(float(download_result.get('AudioLen', 0) or search_result.get('duration', 0) or 0)), duration=SongInfoUtils.seconds2hms(download_result.get('AudioLen', 0) or search_result.get('duration', 0) or 0), lyric=None, cover_url=search_result.get('cover_path') or search_result.get('coverMiddle') or search_result.get('coverLarge') or search_result.get('coverSmall') or search_result.get('trackCoverPath'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and (song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): break
        # return
        return song_info
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('id') or search_result.get('trackId'), SongInfo(source=self.source)
        headers = {'User-Agent': 'ting_6.7.9(GM1900,Android29)', 'Referer': f'https://www.ximalaya.com/sound/{song_id}', 'xm-sign': XimalayaMusicClient.getxmsign()}
        # parse
        (resp := self.get(f'https://www.ximalaya.com/mobile-playpage/track/v3/baseInfo/{int(time.time() * 1000)}', params={'device': 'www2', 'trackQualityLevel': '2', 'trackId': song_id}, headers=headers, **request_overrides)).raise_for_status()
        if ((download_result := resp2json(resp=resp)).get('ret') != 0) or (not isinstance((track_info := download_result.get('trackInfo')), dict)) or (not track_info.get('isAuthorized')): return song_info
        play_url_list = [item for item in (track_info.get('playUrlList') or []) if isinstance(item, dict) and item.get('url')]
        play_url_list = sorted(play_url_list, key=lambda item: XimalayaMusicClient.QUALITY_ORDER.index(item.get('type')) if item.get('type') in XimalayaMusicClient.QUALITY_ORDER else len(XimalayaMusicClient.QUALITY_ORDER))
        for encrypted_url in play_url_list:
            if not (download_url := XimalayaMusicClient.decryptplayurl(encrypted_url.get('url'))) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or search_result.get('trackName') or track_info.get('title')), singers=legalizestring(search_result.get('nickname') or search_result.get('anchorName')), album=legalizestring(search_result.get('album_title') or search_result.get('albumTitle') or search_result.get('albumName')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=song_id, duration_s=int(float(search_result.get('duration', 0) or track_info.get('duration', 0) or 0)), duration=SongInfoUtils.seconds2hms(search_result.get('duration', 0) or track_info.get('duration', 0) or 0), lyric=None, cover_url=search_result.get('cover_path') or search_result.get('coverMiddle') or search_result.get('coverLarge') or search_result.get('coverSmall') or search_result.get('trackCoverPath'), download_url=download_url_status['download_url'], download_url_status=download_url_status,
            )
            if song_info.with_valid_download_url and (song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): break
        # return
        return song_info
    '''_parsewithofficialapiv2'''
    def _parsewithofficialapiv2(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('id') or search_result.get('trackId'), SongInfo(source=self.source)
        headers = {'Referer': f'https://m.ximalaya.com/sound/{song_id}', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'}
        # parse
        (resp := self.get(f'https://m.ximalaya.com/tracks/{song_id}.json', headers=headers, **request_overrides)).raise_for_status()
        if (download_result := resp2json(resp=resp)).get('ret') not in (None, 0, 200): return song_info
        if not (download_url := download_result.get('play_path_64') or download_result.get('play_path_32') or download_result.get('play_path')) or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or search_result.get('trackName') or download_result.get('title')), singers=legalizestring(search_result.get('nickname') or search_result.get('anchorName') or download_result.get('nickname')), album=legalizestring(search_result.get('album_title') or search_result.get('albumTitle') or search_result.get('albumName') or download_result.get('album_title') or download_result.get('albumTitle')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'],
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration', 0) or download_result.get('duration', 0) or 0)), duration=SongInfoUtils.seconds2hms(search_result.get('duration', 0) or download_result.get('duration', 0) or 0), lyric=None, cover_url=search_result.get('cover_path') or search_result.get('coverMiddle') or search_result.get('coverLarge') or search_result.get('coverSmall') or search_result.get('trackCoverPath') or download_result.get('coverLarge') or download_result.get('coverMiddle'), download_url=download_url_status['download_url'], download_url_status=download_url_status,
        )
        # return
        return song_info
    '''_parsebytrack'''
    def _parsebytrack(self, search_results: dict, song_infos: list = [], request_overrides: dict = None, progress: Progress = None, main_page_no: int = 1):
        # init
        search_result_per_track_idx, request_overrides = -1, dict(request_overrides or {})
        candidate_track_parsers = [self._parsewithofficialapiv1, self._parsewithtelecomapi, self._parsewithofficialapiv2] if (self.default_cookies or request_overrides.get('cookies')) else [self._parsewithtelecomapi, self._parsewithofficialapiv2]
        task_id = progress.add_task(f"{self.source}.p{main_page_no}._parsebytrack >>> Start to process the 0th search result", total=None, completed=0)
        # parse tracks one by one
        for search_result_per_track_idx, search_result_per_track in enumerate(search_results.get('docs', [])):
            # --update progress
            progress.update(task_id, description=f'{self.source}.p{main_page_no}._parsebytrack >>> Start to process the {search_result_per_track_idx+1}th search result', completed=search_result_per_track_idx+1, total=search_result_per_track_idx+1)
            # --pass invalid items
            if (not isinstance(search_result_per_track, dict)) or (not (song_id := search_result_per_track.get('id') or search_result_per_track.get('trackId'))): continue
            # --init song info
            song_info = SongInfo(source=self.source, raw_data={'search': search_result_per_track, 'download': {}, 'lyric': {}}, identifier=song_id)
            # --parse with official apis
            for parser in candidate_track_parsers:
                with suppress(Exception): song_info = parser(search_result=search_result_per_track, request_overrides=request_overrides)
                if song_info.with_valid_download_url and (song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): break
            if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
            # --append to song_infos
            if song_info.with_valid_download_url and (song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): song_infos.append(song_info)
            # --judgement for search_size
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        # update progress
        progress.update(task_id, description=f'{self.source}.p{main_page_no}._parsebytrack >>> {search_result_per_track_idx+1} search results processed')
        # return
        return song_infos
    '''_parsebyalbum'''
    def _parsebyalbum(self, search_results: dict, song_infos: list = [], request_overrides: dict = None, progress: Progress = None, main_page_no: int = 1):
        # init
        candidate_track_parsers = [self._parsewithofficialapiv1, self._parsewithtelecomapi, self._parsewithofficialapiv2] if (self.default_cookies or request_overrides.get('cookies')) else [self._parsewithtelecomapi, self._parsewithofficialapiv2]
        # parse albums one by one
        for search_result_per_track in search_results.get('docs', []):
            if (not isinstance(search_result_per_track, dict)) or (not (album_id := search_result_per_track.get('id'))): continue
            # --basic song info class
            download_results, page_size, tracks, unique_track_ids, request_overrides, page_num = [], 50, [], set(), request_overrides or {}, 1
            num_pages = max(1, math.ceil(total_tracks / page_size)) if (total_tracks := int(search_result_per_track.get('tracks', 0) or 0)) else 1
            song_info = SongInfo(
                raw_data={'search': search_result_per_track, 'download': download_results, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result_per_track.get('title')), singers=legalizestring(search_result_per_track.get('nickname')), album=f'{total_tracks} Episodes', 
                ext=None, file_size_bytes=None, file_size=None, identifier=album_id, duration_s=None, duration='-:-:-', lyric=None, cover_url=search_result_per_track.get('cover_path'), download_url=None, download_url_status={}, episodes=[],
            )
            # --download all pages for further processing
            download_album_pid = progress.add_task(f'{self.source}.p{main_page_no}._parsebyalbum >>> (0/{num_pages}) pages downloaded in album {album_id}', total=num_pages)
            while page_num <= num_pages:
                download_result, page_tracks, max_page_id = {}, [], page_num
                with suppress(Exception):
                    (resp := self.get(f'https://mobile.ximalaya.com/mobile/v1/album/track/?albumId={album_id}&pageSize={page_size}&pageId={page_num}', headers={'Referer': f'https://www.ximalaya.com/album/{album_id}'}, **request_overrides)).raise_for_status()
                    data = (download_result := resp2json(resp=resp)).get('data') or {}
                    if download_result.get('ret') == 0: page_tracks = data.get('list') if isinstance(data.get('list'), list) else []; max_page_id = int(data.get('maxPageId') or page_num) if page_tracks else max_page_id
                if not page_tracks:
                    with suppress(Exception):
                        (resp := self.get(f'https://www.ximalaya.com/revision/play/v1/show?id={album_id}&num={page_num}&sort=0&size={page_size}&ptype=0', headers={'Referer': f'https://www.ximalaya.com/album/{album_id}', 'xm-sign': XimalayaMusicClient.getxmsign()}, **request_overrides)).raise_for_status()
                        data = (download_result := resp2json(resp=resp)).get('data') or {}
                        if download_result.get('ret') == 200: page_tracks = data.get('tracksAudioPlay') if isinstance(data.get('tracksAudioPlay'), list) else []; max_page_id = page_num + 1 if data.get('hasMore') else page_num
                if not page_tracks: break
                download_results.append(download_result)
                for track in page_tracks:
                    if (not isinstance(track, dict)) or (not (track_id := track.get('trackId') or track.get('id'))) or (track_id in unique_track_ids): continue
                    unique_track_ids.add(track_id); tracks.append(track)
                num_pages = max(num_pages, max_page_id); progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f'{self.source}.p{main_page_no}._parsebyalbum >>> ({page_num}/{num_pages}) pages downloaded in album {album_id}', total=num_pages); page_num += 1
            # --parse tracks one by one
            download_album_pid = progress.add_task(f'{self.source}.p{main_page_no}._parsebyalbum >>> (0/{len(tracks)}) episodes completed in album {album_id}', total=len(tracks))
            for track_idx, track in enumerate(tracks):
                if track_idx > 0: progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f'{self.source}.p{main_page_no}._parsebyalbum >>> ({track_idx}/{len(tracks)}) episodes completed in album {album_id}')
                eps_info = SongInfo(source=self.source, raw_data={'search': track, 'download': {}, 'lyric': {}})
                for parser in candidate_track_parsers:
                    with suppress(Exception): eps_info = parser(search_result=track, request_overrides=request_overrides)
                    if eps_info.with_valid_download_url and (eps_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): break
                if not eps_info.with_valid_download_url or eps_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                if eps_info.with_valid_download_url and (eps_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): song_info.episodes.append(eps_info)
            progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f'{self.source}.p{main_page_no}._parsebyalbum >>> ({len(tracks)}/{len(tracks)}) episodes completed in album {album_id}')
            if len(song_info.episodes) == 0 or not song_info.with_valid_download_url: continue
            # --post processing
            with suppress(Exception): song_info.duration_s = sum(float(eps.duration_s) for eps in song_info.episodes); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
            with suppress(Exception): song_info.file_size_bytes = sum(float(eps.file_size_bytes) for eps in song_info.episodes); song_info.file_size = SongInfoUtils.byte2mb(song_info.file_size_bytes)
            if song_info.with_valid_download_url: song_info.album = f'{len(song_info.episodes)} Episodes'; song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        # return
        return song_infos
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, queries = request_overrides or {}, parse_qs(urlparse(url=str(search_url)).query, keep_blank_values=True)
        page_no, search_type = int(float(queries.get('page', ['1'])[0])), queries.get('core', ['track'])[0]
        task_id = progress.add_task(f"{self.source}.{search_type}._search >>> Start to process search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            search_results = (((resp2json(resp=resp).get('data') or {}).get('result') or {}).get('response') or {})
            # --parse based on search type
            parsers = {'album': self._parsebyalbum, 'track': self._parsebytrack, }
            parsers[search_type](search_results, song_infos=song_infos, request_overrides=request_overrides, progress=progress, main_page_no=page_no)
            # --update progress
            progress.update(task_id, description=f'{self.source}.{search_type}._search >>> All search results processed on page {page_no}', total=len(song_infos), completed=len(song_infos))
        # failure
        except Exception as err:
            progress.update(task_id, description=f'{self.source}.{search_type}._search >>> {keyword} on page {page_no} (Error: {err})')
            self.logger_handle.error(f'{self.source}.{search_type}._search >>> {keyword} on page {page_no} (Error: {err})', disable_print=self.disable_print)
        # return
        return song_infos