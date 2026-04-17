'''
Function:
    Implementation of JamendoMusicClient: https://www.jamendo.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
import copy
import random
import hashlib
from contextlib import suppress
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from ..utils.hosts import JAMENDO_MUSIC_HOSTS
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, LyricSearchClient, IOUtils, SongInfoUtils


'''JamendoMusicClient'''
class JamendoMusicClient(BaseMusicClient):
    source = 'JamendoMusicClient'
    def __init__(self, **kwargs):
        super(JamendoMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "referer": "https://www.jamendo.com/search?q=musicdl", "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "x-jam-version": "4rkl5f", "x-jam-call": "$536ab7feabd2404af7b6e54b4db74039734b58b3*0.5310391483096057~", "x-requested-with": "XMLHttpRequest",
        }
        self.default_parse_headers = {
            "referer": "https://www.jamendo.com/search?q=musicdl", "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "x-jam-version": "4rkl5f", "x-jam-call": "$536ab7feabd2404af7b6e54b4db74039734b58b3*0.5310391483096057~", "x-requested-with": "XMLHttpRequest",
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'query': keyword, 'type': 'track', 'limit': self.search_size_per_source, 'identities': 'www', 'offset': 0}).update(rule)
        # construct search urls
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'https://www.jamendo.com/api/search?'
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['offset'] = count
            page_rule['limit'] = page_size
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        make_xjam_call_func = lambda path='/api/tracks': f"${hashlib.sha1((path + (rand := str(random.random()))).encode('utf-8')).hexdigest()}*{rand}~"
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            (headers := copy.deepcopy(self.default_headers))['x-jam-call'], download_result = make_xjam_call_func(path='/api/tracks'), {}
            with suppress(Exception): (resp := self.get('https://www.jamendo.com/api/tracks?', headers=headers, params={'id[]': song_id}, **request_overrides)).raise_for_status(); download_result = resp2json(resp=resp)[0]
            (headers := copy.deepcopy(self.default_headers))['x-jam-call'] = make_xjam_call_func(path='/api/artists')
            artist_id = safeextractfromdict(search_result, ['artist', 'id'], None) or search_result.get('artistId') or download_result.get('artistId')
            with suppress(Exception): download_result['artist'] = resp2json(self.get('https://www.jamendo.com/api/artists?', headers=headers, params={'id[]': artist_id}, **request_overrides))[0] if not safeextractfromdict(search_result, ['artist', 'name'], None) else download_result.get('artist')
            (headers := copy.deepcopy(self.default_headers))['x-jam-call'] = make_xjam_call_func(path='/api/albums')
            album_id = safeextractfromdict(search_result, ['album', 'id'], None) or search_result.get('albumId') or download_result.get('albumId')
            with suppress(Exception): download_result['album'] = resp2json(self.get('https://www.jamendo.com/api/albums?', headers=headers, params={'id[]': album_id}, **request_overrides))[0] if not safeextractfromdict(search_result, ['album', 'name'], None) else download_result.get('album')
            candidate_urls = [safeextractfromdict(download_result, list(path), None) for path in [('stream', 'flac'), ('download', 'flac'), ('stream', 'mp33'), ('stream', 'mp32'), ('download', 'mp3'), ('stream', 'mp3'), ('stream', 'ogg'), ('download', 'ogg')]]
            if (candidate_urls := [c for c in candidate_urls if c and str(c).startswith('http')]): candidate_urls = [urlunsplit((*urlsplit(candidate_urls[0])[:3], urlencode([(k, 'flac' if k == 'format' else v) for k, v in parse_qsl(urlsplit(str(candidate_urls[0])).query, keep_blank_values=True)]), urlsplit(str(candidate_urls[0])).fragment))] + candidate_urls
            if not candidate_urls: candidate_urls = [url for path in [('download', 'mp3'), ('stream', 'mp3'), ('download', 'ogg'), ('stream', 'ogg')] if (url := safeextractfromdict(search_result, list(path), None)) and str(url).startswith('http')]
            for download_url in ([f"https://prod-1.storage.jamendo.com/download/track/{song_id}/flac/"] + candidate_urls):
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name') or download_result.get('name')), singers=legalizestring(safeextractfromdict(search_result, ['artist', 'name'], None) or safeextractfromdict(download_result, ['artist', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None) or safeextractfromdict(download_result, ['album', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                    file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration') or download_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('duration') or download_result.get('duration') or 0))), lyric=download_result.get('lyrics'), cover_url=f"https://usercontent.jamendo.com?type=album&id={album_id}&width=300&trackid={song_id}", download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info.lyric and song_info.lyric not in {'NULL'}: song_info.lyric = cleanlrc(song_info.lyric.replace('<br />', '\n'))
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, make_xjam_call_func = request_overrides or {}, lambda path='/api/search': f"${hashlib.sha1((path + (rand := str(random.random()))).encode('utf-8')).hexdigest()}*{rand}~"
        # successful
        try:
            # --search results
            (headers := copy.deepcopy(self.default_headers))['x-jam-call'] = make_xjam_call_func(path='/api/search')
            (resp := self.get(search_url, headers=headers, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp):
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
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
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **(request_overrides := dict(request_overrides or {}))).url
        playlist_id, song_infos = re.search(r'/playlist/([^/]+)', playlist_url).group(1) if re.search(r'/playlist/([^/]+)', playlist_url) else None, []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, JAMENDO_MUSIC_HOSTS)): return song_infos
        make_xjam_call_func = lambda path='/api/playlists': f"${hashlib.sha1((path + (rand := str(random.random()))).encode('utf-8')).hexdigest()}*{rand}~"
        # get tracks in playlist
        (headers := copy.deepcopy(self.default_headers))['x-jam-call'] = make_xjam_call_func(path='/api/playlists')
        (resp := self.get('https://www.jamendo.com/api/playlists?', headers=headers, params={'id[]': playlist_id}, **request_overrides)).raise_for_status()
        tracks_in_playlist = (playlist_result := resp2json(resp=resp)[0])['tracks']
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}})
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                if song_info.with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse song id {song_info.identifier} >>> {song_info.album} {song_info.song_name} {song_info.singers} {song_info.download_url}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result, ['name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos