'''
Function:
    Implementation of SoundCloudMusicClient: https://soundcloud.com/discover
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import subprocess
from contextlib import suppress
from .base import BaseMusicClient
from platformdirs import user_log_dir
from urllib.parse import urlencode, urlparse
from ..utils.hosts import SOUNDCLOUD_MUSIC_HOSTS
from pathvalidate import sanitize_filepath, sanitize_filename
from ..utils.soundcloudutils import SoundCloudMusicClientUtils
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, hostmatchessuffix, obtainhostname, useparseheaderscookies, usedownloadheaderscookies, SongInfo, AudioLinkTester, LyricSearchClient, IOUtils, SongInfoUtils, NM3U8DLREDownloadCommand


'''SoundCloudMusicClient'''
class SoundCloudMusicClient(BaseMusicClient):
    source = 'SoundCloudMusicClient'
    CLIENT_ID = None
    def __init__(self, **kwargs):
        super(SoundCloudMusicClient, self).__init__(**kwargs)
        if self.default_search_cookies: assert ("oauth_token" in self.default_search_cookies), '"oauth_token" should be configured, refer to https://musicdl.readthedocs.io/en/latest/Quickstart.html#soundcloud-music-download'
        if self.default_parse_cookies: assert ("oauth_token" in self.default_parse_cookies), '"oauth_token" should be configured, refer to https://musicdl.readthedocs.io/en/latest/Quickstart.html#soundcloud-music-download'
        if self.default_download_cookies: assert ("oauth_token" in self.default_download_cookies), '"oauth_token" should be configured, refer to https://musicdl.readthedocs.io/en/latest/Quickstart.html#soundcloud-music-download'
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
        self.default_parse_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
        if self.default_search_cookies: self.default_search_headers.update({'Authorization': self.default_search_cookies["oauth_token"]})
        if self.default_parse_cookies: self.default_parse_headers.update({'Authorization': self.default_parse_cookies["oauth_token"]})
        if self.default_download_cookies: self.default_download_headers.update({'Authorization': self.default_download_cookies["oauth_token"]})
        SoundCloudMusicClient.CLIENT_ID = self.default_search_cookies.get('client_id') or self.default_parse_cookies.get('client_id') or self.default_download_cookies.get('client_id')
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0, auto_supplement_song: bool = True):
        # fallback to general music download method
        if not song_info.raw_data.get('enable_nm3u8dlre', False): return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id, auto_supplement_song=auto_supplement_song)
        # deal with hls streams
        song_info, request_overrides = copy.deepcopy(song_info), copy.deepcopy(request_overrides or {})
        song_info._save_path = sanitize_filepath(song_info.save_path); song_info.work_dir = os.path.dirname(song_info.save_path); IOUtils.touchdir(song_info.work_dir)
        try:
            keys = SoundCloudMusicClientUtils.getwidevinekeys(song_info.download_url, request_overrides=request_overrides) if str(song_info.raw_data["stream"]["protocol"]).startswith(('ctr-', 'cbc-')) else []
            log_file_path = os.path.join(user_log_dir(appname='musicdl', appauthor='zcjin'), f"musicdl_{sanitize_filename(str(song_info.identifier))}.log")
            cmd = NM3U8DLREDownloadCommand().build(song_info.download_url, song_info.save_path, log_file_path=log_file_path, mods=({"__add__": [("--key", k) for k in keys]} if keys else None))
            print(cmd)
            progress.update(song_progress_id, total=None, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Downloading)")
            subprocess.run(cmd, check=True, capture_output=self.disable_print, text=True, encoding='utf-8', errors='ignore')
            progress.update(song_progress_id, total=os.path.getsize(song_info.save_path), advance=os.path.getsize(song_info.save_path), description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Success)")
            downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(song_info, logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else song_info)
        except Exception as err:
            progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})")
            self.logger_handle.error(f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})", disable_print=self.disable_print)
        # return
        return downloaded_song_infos
    '''_setclientid'''
    def _setclientid(self, request_overrides: dict = None):
        if SoundCloudMusicClient.CLIENT_ID is not None: return SoundCloudMusicClient.CLIENT_ID
        try: (resp := self.session.get('https://soundcloud.com/', **(request_overrides := request_overrides or {}))).raise_for_status()
        except Exception: SoundCloudMusicClient.CLIENT_ID = '9jZvetLfDs6An08euQgJ0lYlHkKdGFzV'; return SoundCloudMusicClient.CLIENT_ID
        for url in reversed(re.findall(r'<script[^>]+src="([^"]+)"', resp.text)):
            with suppress(Exception): resp = None; (resp := self.session.get(url, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
            if (m := re.search(r'client_id\s*:\s*"([0-9a-zA-Z]{32})"', resp.text)): SoundCloudMusicClient.CLIENT_ID = m.group(1); return SoundCloudMusicClient.CLIENT_ID
        SoundCloudMusicClient.CLIENT_ID = '9jZvetLfDs6An08euQgJ0lYlHkKdGFzV'; return SoundCloudMusicClient.CLIENT_ID
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}; self._setclientid(request_overrides=request_overrides)
        (default_rule := {'q': keyword, 'sc_a_id': 'ab15798461680579b387acf67441b40149e528cd', 'facet': 'genre', 'user_id': '704923-225181-486085-807554', 'client_id': SoundCloudMusicClient.CLIENT_ID, 'limit': '20', 'offset': '0', 'linked_partitioning': '1', 'app_version': '1769771069', 'app_locale': 'en'}).update(rule)
        # construct search urls
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'https://api-v2.soundcloud.com/search/tracks?'
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['limit'] = page_size
            page_rule['offset'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source); self._setclientid(request_overrides=request_overrides)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        infer_ext_func = lambda mime_type, preset: ((lambda mime_type, preset: 'opus' if 'opus' in mime_type or 'opus' in preset else 'm4a' if 'mp4' in mime_type or 'm4a' in mime_type or 'aac' in preset else 'mp3' if 'mpeg' in mime_type or 'mp3' in preset else 'wav' if 'wav' in mime_type else 'flac' if 'flac' in mime_type else 'm4a' if 'alac' in mime_type else 'm4a')(str(mime_type).lower(), str(preset).lower()))
        sort_key_func = lambda stream: ((100, 0, 0) if dict(stream).get('is_original', False) else (0, {"hq": 2, "sq": 1}.get(str(dict(stream).get('quality', 'sq') or 'sq').lower(), 0), 3 if dict(stream).get('ext', '') == 'opus' else (2 if dict(stream).get('ext', '') == 'm4a' else 1)))
        # supplement incomplete tracks
        if not safeextractfromdict(search_result, ['media', 'transcodings'], []): search_result = resp2json(self.get(f"https://api-v2.soundcloud.com/tracks/{song_id}", params={"client_id": SoundCloudMusicClient.CLIENT_ID}, **request_overrides))
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            with suppress(Exception): resp = None; (resp := self.get(f'https://api-v2.soundcloud.com/tracks/{song_id}/download', params={'client_id': SoundCloudMusicClient.CLIENT_ID}, **request_overrides)).raise_for_status() if search_result.get("downloadable") and search_result.get("has_downloads_left") else None
            streams = [{"is_original": True, "url": original_url, "ext": "orig", "protocol": "http", "snipped": False}] if (original_url := (download_result := resp2json(resp=resp)).get('redirectUri')) and str(original_url).startswith('http') else []
            for transcoding in sorted((safeextractfromdict(search_result, ['media', 'transcodings'], []) or []), key=sort_key_func, reverse=True):
                if not (download_url := safeextractfromdict(transcoding, ['url'], '')) or not str(download_url).startswith('http'): continue
                protocol = (safeextractfromdict(transcoding, ['format', 'protocol'], '') or '').lower()
                ext = infer_ext_func((mime_type := (safeextractfromdict(transcoding, ['format', 'mime_type'], '') or '').lower()), (preset := (safeextractfromdict(transcoding, ['preset'], '') or '').lower()))
                with suppress(Exception): resp = None; (resp := self.get(download_url, params={'client_id': SoundCloudMusicClient.CLIENT_ID}, **request_overrides)).raise_for_status()
                download_result[str(download_url)] = resp2json(resp=resp); download_url = resp2json(resp=resp).get('url')
                if not download_url or not str(download_url).startswith('http'): continue
                streams.append({"is_original": False, "quality": dict(transcoding).get("quality", "sq"), "protocol": protocol, "mime_type": mime_type, "preset": preset, "ext": ext, "snipped": dict(transcoding).get("snipped", False), "url": download_url})
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = int(float(safeextractfromdict(search_result, ['duration'], 0) or 0) / 1000)
            for stream in sorted(streams, key=sort_key_func, reverse=True):
                download_url, protocol, ext, is_original = stream["url"], stream["protocol"], stream["ext"], stream.get("is_original", False)
                if is_original or protocol in {'progressive'}:
                    download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                else:
                    with suppress(Exception): resp = None; (resp := self.get(download_url, allow_redirects=True, **request_overrides)).raise_for_status()
                    if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                    download_url_status = {'ok': True, 'ext': ext, 'file_size_bytes': 'HLS', 'file_size': 'HLS', 'download_url': download_url}
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'stream': stream, 'enable_nm3u8dlre': (False if (is_original or protocol in {'progressive'}) else True)}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['publisher_metadata', 'artist'], None) or safeextractfromdict(search_result, ['user', 'username'], None)), album=legalizestring(safeextractfromdict(search_result, ['publisher_metadata', 'album_title'], None)), 
                    ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('artwork_url'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers
                )
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
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
        request_overrides = request_overrides or {}; self._setclientid(request_overrides=request_overrides)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp)['collection']:
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
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **dict(request_overrides := request_overrides or {})).url
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, SOUNDCLOUD_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        assert (self._setclientid(request_overrides=request_overrides) is not None), 'fail to init client id'
        (resp := self.get("https://api-v2.soundcloud.com/resolve", params={"url": playlist_url, "client_id": SoundCloudMusicClient.CLIENT_ID}, **request_overrides)).raise_for_status()
        tracks_in_playlist = (playlist_result := resp2json(resp=resp))['tracks']; playlist_id = playlist_result['id']
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
        playlist_name = legalizestring(safeextractfromdict(playlist_result, ['title'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos