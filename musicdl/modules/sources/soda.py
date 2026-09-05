'''
Function:
    Implementation of SodaMusicClient: https://www.douyin.com/qishui/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
import copy
import json
import uuid
import requests
import json_repair
from typing import Any
from pathlib import Path
from contextlib import suppress
from typing_extensions import Unpack
from collections.abc import Callable
from pathvalidate import sanitize_filepath
from ..utils.hosts import SODA_MUSIC_HOSTS
from urllib.parse import urlencode, urlparse, parse_qs
from .base import BaseMusicClient, BaseMusicClientKwargs
from ..utils.sodautils import AudioDecryptor, SodaTimedLyricsParser
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import extractdurationsecondsfromlrc, searchdictbykey, cookies2string, legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, usedownloadheaderscookies, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, SongInfoUtils, IOUtils


'''SodaMusicClient'''
class SodaMusicClient(BaseMusicClient):
    source = 'SodaMusicClient'
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(SodaMusicClient, self).__init__(**kwargs)
        self.soda_auth_info = self.default_search_cookies or self.default_parse_cookies or self.default_download_cookies
        self.device_id = self.soda_auth_info.get('device_id') or self.soda_auth_info.get('device-id') or "3753066532709850"
        self.auth_cookies = self.soda_auth_info.get('cookies') or self.soda_auth_info.get('cookie') or self.soda_auth_info.get('Cookies') or self.soda_auth_info.get('Cookie') or {}
        self.x_helios = self.soda_auth_info.get('x_helios') or self.soda_auth_info.get('x-helios') or self.soda_auth_info.get('X-Helios') or "SicAACJWDNiSHEX4DSBVXo3+TNXAHXt9Af6CkPaMTmSX1Jcg"
        self.x_medusa = self.soda_auth_info.get('x_medusa') or self.soda_auth_info.get('x-medusa') or self.soda_auth_info.get('X-Medusa') or "GBR+aez8IZPMw6JSzT62GUzbH3GODwMBg7ZESAAAAQk/GduVkAZWRUCTX0SGSLVDDQ/gYOFKM/adGsI29F3FyR/OAoj+AK7fOY1Pe1po0w3w850g3Y0xvZOEl35RaWIynTM+dvmKmsQLoBG2LPT9eoaLqF8pi6MjvRdIJK8PMnnwDYrreh4OQ85zqzZdCFytOf6cXPH4NImgdUgBceuFfUtCN8ZdI3bRTDD28J8OxDK8vsWjdzimSPNTIe6C2EKel/U+PcqXfkbs/ZWCvHyxmqgrLfu5tHAtnXuEbQf6J53G8I6wdY8JQ5wm8+7o37XUiWC8FCB6y+09/aB9q4LTwNEMOlv50fAQg/bT9RgB6+7jF+7RXZyIuNkXAuJb2uZeBSzfJVvw6VITls5AFSOdNu376GqKGm4T6M8V9HzT2L8cW8smYgNG6HJPjd3iVVcv8fjeJeAGolEPMBbBvbAjJCSQAOY6jo/RGbRvOUsDyZgJ6fEp8ncjXIcK6Nw1GSPOv7AXWILqyt5sBpFDvPlpJTqih5TWbmWSEBc52+OPX2DJKknmz4qBPrRdJ7QvtxA5nrLDBjc3doDJa2iv1FE/7nUQoGJ5njCFw2BYfT9LE3kxDVUtWzmYLtxzkFGpuhGdAuRYSSC2LiCgbGcaqIkDrUpa2yaVZNimFJi3s08+OCUllT5aQQIh/mv02EEXGXi1IV7UCWqTNEdzjZrat6P2rNQbG0DYXvj3sbTJX8+7mS/c6LD5sWZ4UjKiVo4PMRknYHv3syjwX4VuvF49u/+fHYWtv72Y+buTO0iuGDxIiOk6kNElV895F40J6WpZ59nPpg7Qum8ndQHko5xqtdAXIB/l//3/v+/3//8AAA=="
        self.default_search_headers = {"User-Agent": "LunaPC/3.5.1(408871041)", "Content-Type": "application/json; charset=utf-8"}
        if self.default_search_cookies: self.default_search_headers.update({'Cookie': cookies2string(self.auth_cookies), 'X-Helios': self.x_helios, 'X-Medusa': self.x_medusa})
        self.default_parse_headers = {"User-Agent": "LunaPC/3.5.1(408871041)", "Content-Type": "application/json; charset=utf-8"}
        if self.default_parse_cookies: self.default_parse_headers.update({'Cookie': cookies2string(self.auth_cookies), 'X-Helios': self.x_helios, 'X-Medusa': self.x_medusa})
        self.default_download_headers = {"User-Agent": "LunaPC/3.5.1(408871041)", "Content-Type": "application/json; charset=utf-8"}
        if self.default_download_cookies: self.default_download_headers.update({'Cookie': cookies2string(self.auth_cookies), 'X-Helios': self.x_helios, 'X-Medusa': self.x_medusa})
        self.default_headers = self.default_search_headers; self.default_cookies = {}; self.default_search_cookies = {}; self.default_download_cookies = {}; self.default_parse_cookies = {}
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0, auto_supplement_song: bool = True):
        if not song_info.raw_data.get('play_auth'): return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id, auto_supplement_song=auto_supplement_song)
        song_info = super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=[], progress=progress, song_progress_id=song_progress_id, auto_supplement_song=False)[0]
        output_filepath, file_data = (output_filepath := Path(song_info.save_path)).parent / f'{output_filepath.stem}.{song_info.ext}', bytearray(Path(song_info.save_path).read_bytes())
        AudioDecryptor.decrypt(file_data=file_data, play_auth=song_info.raw_data['play_auth'], output_filepath=str(output_filepath))
        if not os.path.samefile(song_info.save_path, str(output_filepath)): os.remove(song_info.save_path); song_info._save_path = str(output_filepath)
        downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(song_info, logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else song_info)
        return downloaded_song_infos
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, self.search_size_per_page = rule or {}, request_overrides or {}, min(self.search_size_per_page, 20)
        (default_rule := {'aid': '386088', 'app_name': 'luna_pc', 'region': 'cn', 'geo_region': 'cn', 'os_region': 'cn', 'sim_region': '', 'device_id': self.device_id, 'cdid': '', 'iid': '3753066532713946', 'version_name': '3.5.1', 'version_code': '30050100', 'channel': 'official', 'build_mode': 'master', 'network_carrier': '', 'ac': 'wifi', 'tz_name': 'Asia/Shanghai', 'resolution': '', 'device_platform': 'windows', 'device_type': 'Windows', 'os_version': 'Windows 10 Education', 'fp': self.device_id, 'q': keyword, 'cursor': 0, 'search_id': str(uuid.uuid4()), 'search_method': 'input', 'debug_params': '', 'from_search_id': '', 'search_scene': ''}).update(rule)
        # construct search urls
        base_url, search_urls, page_size, count = 'https://api.qishui.com/luna/pc/search/track?', [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['cursor'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithqiuyu520api'''
    def _parsewithqiuyu520api(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, safeextractfromdict(search_result, ['entity', 'track', 'id'], None)
        headers = {"Accept": "application/json, text/plain, */*", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Referer": "http://qiuyu520.fun/qishui/", "Origin": "http://qiuyu520.fun"}
        with suppress(Exception): download_result = {}; download_result = self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides)
        # parse
        (resp := requests.post(f"http://qiuyu520.fun/qishuiParse/api/track/v2", headers=headers, json={"track_id": song_id}, timeout=10, **request_overrides)).raise_for_status(); download_result['track'] = resp2json(resp=resp)
        download_url, play_auth = safeextractfromdict(download_result['track'], ['data', 'url'], ''), safeextractfromdict(download_result['track'], ['data', 'playAuth'], '')
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'play_auth': play_auth}, source=self.source, song_name=legalizestring(download_result.get('name') or safeextractfromdict(download_result['track'], ['data', 'title'], None)), singers=legalizestring(download_result.get('artist') or safeextractfromdict(download_result['track'], ['data', 'artist'], None)), album=legalizestring(download_result.get('album') or safeextractfromdict(download_result['track'], ['data', 'album'], None)), 
            ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=download_result.get('duration'), duration=SongInfoUtils.seconds2hms(download_result.get('duration')), lyric=download_result.get('lyric'), cover_url=download_result.get('cover') or safeextractfromdict(download_result['track'], ['data', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.soda_auth_info or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for parser_func in [self._parsewithqiuyu520api, ]:
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_getsongmetainfo'''
    def _getsongmetainfo(self, song_id: str, request_overrides: dict = None):
        # init
        headers, request_overrides = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}, request_overrides or {}
        to_lrc_func: Callable[[dict[str, Any]], str] = lambda sentence: f"[{(s:=int(sentence.get('startMs') or 0))//60000:02d}:{(s%60000)//1000:02d}.{s%1000:03d}]{''.join(w.get('text', '') for w in (sentence.get('words') or []) if isinstance(w, dict))}"
        # parse
        (resp := self.get(f"https://music.douyin.com/qishui/share/track?track_id={song_id}", headers=headers, **request_overrides)).raise_for_status()
        meta_info = json_repair.loads(re.search(r'_ROUTER_DATA\s*=\s*({.*?});', resp.text, re.S).group(1))
        audio_option = safeextractfromdict(meta_info, ['loaderData', 'track_page', 'audioWithLyricsOption'], {}) or {}
        track_info: dict = searchdictbykey(meta_info, 'trackInfo')[0]; assert str(track_info.get('id')) == str(song_id)
        sentences, lrc_list = safeextractfromdict(meta_info, ['loaderData', 'track_page', 'audioWithLyricsOption', 'lyrics', 'sentences'], []) or [], []
        lrc_list.extend(to_lrc_func(sentence) for sentence in sentences if isinstance(sentence, dict))
        track_info_organized = {
            'id': song_id, 'audition_url': (audio_option.get('url') or '').replace("\\u002F", "/").replace("%7C", "|").replace("%3D", "="), 'name': track_info.get('name'), 'artist': ', '.join([singer.get('name') for singer in (track_info.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]), 'album': safeextractfromdict(track_info, ['album', 'name'], None), 
            'duration': int(float(track_info.get('duration', '0') or '0')) / 1000., 'cover': str(safeextractfromdict(track_info, ['album', 'url_cover', 'urls', 0], '')) + str(safeextractfromdict(track_info, ['album', 'url_cover', 'uri'], '')) + '~c5_500x500.jpg', 'lyric': cleanlrc("\n".join(lrc_list)),
        }
        # return
        return track_info_organized
    '''_parsewithofficialnonvipapiv1'''
    def _parsewithofficialnonvipapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac', 'm4a'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := safeextractfromdict(search_result, ['entity', 'track', 'id'], None))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            download_result: dict = self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides)
            download_url_status: dict = self.audio_link_tester.test(url=download_result.get('audition_url'), request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('name') or safeextractfromdict(search_result, ['entity', 'track', 'name'], None)), singers=legalizestring(download_result.get('artist') or (', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['entity', 'track', 'artists'], []) or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(download_result.get('album') or safeextractfromdict(search_result, ['entity', 'track', 'album', 'name'], None)), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=download_result.get('duration'), duration=SongInfoUtils.seconds2hms(download_result.get('duration')), lyric=download_result.get('lyric'), cover_url=download_result.get('cover') or (str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'urls', 0], '')) + str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'uri'], '')) + '~c5_500x500.jpg'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        if song_info.duration in {'00:00:00', '-:-:-'}: song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_parsewithofficialvipapiv1'''
    def _parsewithofficialvipapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac', 'm4a'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := safeextractfromdict(search_result, ['entity', 'track', 'id'], None))): return song_info
        rank_audio_func = lambda video_list: sorted([v for v in video_list if isinstance(v, dict)], key=lambda x: (x.get('Size'), x.get('Bitrate')), reverse=True)
        default_query = {"aid": "386088", "app_name": "luna_pc", "region": "cn", "geo_region": "cn", "os_region": "cn", "sim_region": "", "device_id": self.device_id, "cdid": "", "iid": "3753066532713946", "version_name": "3.5.1", "version_code": "30050100", "channel": "official", "build_mode": "master", "network_carrier": "", "ac": "wifi", "tz_name": "Asia/Shanghai", "resolution": "", "device_platform": "windows", "device_type": "Windows", "os_version": "Windows 10 Education", "fp": self.device_id,}
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            body = {"media_type": "track", "queue_type": "search_one_track", "scene_name": "search", "track_id": song_id}
            with suppress(Exception): download_result = {}; download_result = self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides)
            (resp := self.post(f'https://api.qishui.com/luna/pc/track_v2?{urlencode(default_query)}', data=json.dumps(body, ensure_ascii=False, separators=(",", ":")), **request_overrides)).raise_for_status(); download_result['track'] = resp2json(resp)
            (resp := self.get(download_result['track']['track_player']['url_player_info'], **request_overrides)).raise_for_status(); download_result['url_player_info'] = resp2json(resp)
            audios_sorted: list[dict] = rank_audio_func(safeextractfromdict(download_result, ['url_player_info', 'Result', 'Data', 'PlayInfoList'], []) or [])
            for audio_sorted in [a for a in audios_sorted if (a.get('MainPlayUrl') or a.get('BackupPlayUrl'))]:
                download_url, play_auth = audio_sorted.get('MainPlayUrl') or audio_sorted.get('BackupPlayUrl'), safeextractfromdict(audio_sorted, ['PlayAuth'], '')
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'play_auth': play_auth}, source=self.source, song_name=legalizestring(download_result.get('name') or safeextractfromdict(search_result, ['entity', 'track', 'name'], None)), singers=legalizestring(download_result.get('artist') or (', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['entity', 'track', 'artists'], []) or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(download_result.get('album') or safeextractfromdict(search_result, ['entity', 'track', 'album', 'name'], None)), ext=download_url_status['ext'], 
                    file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=download_result.get('duration'), duration=SongInfoUtils.seconds2hms(download_result.get('duration')), lyric=download_result.get('lyric'), cover_url=download_result.get('cover') or (str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'urls', 0], '')) + str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'uri'], '')) + '~c5_500x500.jpg'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if not song_info.lyric or song_info.lyric in {'None', 'none', 'NULL', 'null'}: song_info.lyric = cleanlrc(SodaTimedLyricsParser.tolrclinelevel(SodaTimedLyricsParser.parsetimedlyrics(safeextractfromdict(download_result['track'], ['lyric', 'content'], '') or '')))
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        if song_info.duration in {'00:00:00', '-:-:-'}: song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        page_no, search_result_idx, lossless_quality_is_sufficient = int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('cursor')[0]) / self.search_size_per_page) + 1, -1, False if self.soda_auth_info or request_overrides.get('cookies') else True
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **(request_overrides := request_overrides or {}))).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp)['result_groups'][0]['data']):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with third part apis
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialvipapiv1(search_result=search_result, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides) if (self.soda_auth_info or request_overrides.get('cookies')) else self._parsewithofficialnonvipapiv1(search_result=search_result, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
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
        with suppress(Exception): playlist_id, song_infos = parse_qs(urlparse(playlist_url).query, keep_blank_values=False).get('playlist_id')[0], []
        if not playlist_id: playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, SODA_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, page_size, playlist_result_first = [], 1, 20, {}
        while True:
            params = {'playlist_id': playlist_id, 'cursor': str(page_size * (page - 1)), 'cnt': str(page_size), 'aid': '386088', 'device_platform': 'web', 'channel': 'pc_web'}
            with suppress(Exception): (resp := self.get(f"https://api.qishui.com/luna/pc/playlist/detail?", params=params, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['media_resources'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['media_resources'], [])); page += 1; del resp
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['playlist', 'count_tracks'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["id"]: d for d in tracks_in_playlist}.values())
        for track in tracks_in_playlist: track['entity'].__setitem__('track', safeextractfromdict(track, ['entity', 'track_wrapper', 'track'], {})) if isinstance(track, dict) and isinstance(track.get('entity'), dict) else None
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}})
                song_info_flac = self._parsewiththirdpartapis(search_result=track_info, request_overrides=request_overrides)
                lossless_quality_is_sufficient = False if self.soda_auth_info or request_overrides.get('cookies') else True
                with suppress(Exception): song_info = self._parsewithofficialvipapiv1(search_result=track_info, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides) if (self.soda_auth_info or request_overrides.get('cookies')) else self._parsewithofficialnonvipapiv1(search_result=track_info, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                if (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse track info {track_info}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['playlist', 'title'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos