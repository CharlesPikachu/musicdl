'''
Function:
    Implementation of JioSaavnMusicClient: https://www.jiosaavn.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import base64
from functools import reduce
from itertools import product
from bs4 import BeautifulSoup
from contextlib import suppress
from Cryptodome.Cipher import DES
from typing_extensions import Unpack
from Cryptodome.Util.Padding import unpad
from pathvalidate import sanitize_filepath
from ..utils.hosts import JIOSAAVN_MUSIC_HOSTS
from urllib.parse import urlencode, urlparse, parse_qs
from .base import BaseMusicClient, BaseMusicClientKwargs
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, hostmatchessuffix, obtainhostname, useparseheaderscookies, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils


'''JioSaavnMusicClient'''
class JioSaavnMusicClient(BaseMusicClient):
    source = 'JioSaavnMusicClient'
    MUSIC_QUALITIES = ('320', '160', '96', '48', '12')
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(JioSaavnMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "Accept": "application/json", "Content-Type": "application/json"}
        self.default_parse_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "Accept": "application/json", "Content-Type": "application/json"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"p": '1', 'q': keyword, '_format': 'json', '_marker': '0', 'api_version': '4', 'ctx': 'web6dot0', 'n': '20', '__call': 'search.getResults'}).update(rule)
        # construct search urls
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'https://www.jiosaavn.com/api.php?'
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['n'] = str(page_size)
            page_rule['p'] = str(int(count // page_size) + 1)
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_decrypturl'''
    def _decrypturl(self, enc_url: str, key: bytes = b"38346591"):
        if not enc_url or not isinstance(enc_url, str): return None
        decrypted_url = DES.new(key, DES.MODE_ECB).decrypt(base64.b64decode(enc_url.strip()))
        try: decrypted_url = unpad(decrypted_url, DES.block_size)
        except ValueError: decrypted_url = decrypted_url.rstrip(b"\x00")
        return decrypted_url.decode("utf-8", errors="ignore").strip().replace("http://", "https://")
    '''_normalizemediaurl'''
    def _normalizemediaurl(self, url: str, quality: str):
        return reduce(lambda s, qe: s.replace(f"_{qe[0]}.{qe[1]}", f"_{quality}.{qe[1]}"), product(("12", "48", "96", "160", "320"), ("mp4", "mp3", "m4a")), url.replace("http://", "https://")) if url else None
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            (resp := self.get('https://www.jiosaavn.com/api.php', params={"__call": "song.getDetails", "cc": "in", "_format": "json", "_marker": "0", "pids": song_id}, **request_overrides)).raise_for_status()
            base_download_url = safeextractfromdict((download_result := resp2json(resp=resp)), [song_id, 'media_url'], None) or self._decrypturl(safeextractfromdict(download_result, [song_id, 'encrypted_media_url'], None)) or self._decrypturl(safeextractfromdict(download_result, [song_id, 'encrypted_drm_media_url'], None)) or safeextractfromdict(download_result, [song_id, 'media_preview_url'], None)
            for music_quality in JioSaavnMusicClient.MUSIC_QUALITIES:
                download_url = self._normalizemediaurl(base_download_url, quality=music_quality)
                duration_in_secs = int(float(safeextractfromdict(download_result, [song_id, 'duration'], 0) or 0))
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, [song_id, 'song'], None)), singers=legalizestring(safeextractfromdict(download_result, [song_id, 'singers'], None) or safeextractfromdict(download_result, [song_id, 'primary_artists'], None)), album=legalizestring(safeextractfromdict(download_result, [song_id, 'album'], None)), 
                    ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, [song_id, 'image'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        lyric_url, lyric_result, lyric = f"https://www.jiosaavn.com/api.php?__call=lyrics.getLyrics&ctx=web6dot0&api_version=4&_format=json&_marker=0%3F_marker%3D0&lyrics_id={song_id}", {}, 'NULL'
        with suppress(Exception): (resp := self.get(lyric_url, **request_overrides)).raise_for_status(); lyric_result = resp2json(resp=resp); lyric = BeautifulSoup(lyric_result.get('lyrics'), "lxml").get_text("\n")
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, page_no, search_result_idx = request_overrides or {}, int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('p')[0])), -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp)['results']):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
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
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, JIOSAAVN_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, playlist_result_first = [], 1, {}
        while True:
            params = {"__call": "webapi.get", "type": "playlist", "p": page, "n": "100", "includeMetaTags": "0", "ctx": "web6dot0", "api_version": "4", "_format": "json", "_marker": "0", "token": playlist_id}
            with suppress(Exception): (resp := self.get("https://www.jiosaavn.com/api.php", params=params, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['list'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['list'], [])); page += 1; del resp
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['list_count'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["id"]: d for d in tracks_in_playlist}.values())
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}})
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                if song_info.with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse track info {track_info}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['title'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos