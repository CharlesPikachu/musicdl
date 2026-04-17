'''
Function:
    Implementation of AppleMusicClient: https://music.apple.com/{geo}/new
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import shutil
from contextlib import suppress
from types import SimpleNamespace
from .base import BaseMusicClient
from ..utils.hosts import APPLE_MUSIC_HOSTS
from urllib.parse import urlencode, urlparse
from pathvalidate import sanitize_filepath, sanitize_filename
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils.appleutils import AppleMusicClientDownloadSongUtils, AppleMusicClientAPIUtils, AppleMusicClientItunesApiUtils, DownloadItem, SongCodec, RemuxMode
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, usedownloadheaderscookies, useparseheaderscookies, hostmatchessuffix, obtainhostname, cleanlrc, SongInfo, SongInfoUtils, AudioLinkTester, IOUtils


'''AppleMusicClient'''
class AppleMusicClient(BaseMusicClient):
    source = 'AppleMusicClient'
    def __init__(self, use_wrapper: bool = False, wrapper_account_url: str = "http://127.0.0.1:30020/", language: str = "en-US", codec: str = None, wrapper_decrypt_ip: str = "127.0.0.1:10020", **kwargs):
        super(AppleMusicClient, self).__init__(**kwargs)
        self.apple_music_api, self.itunes_api, self.use_wrapper, self.wrapper_account_url, self.language, self.account_info, self.codec, self.wrapper_decrypt_ip = None, None, use_wrapper, wrapper_account_url, language, {}, codec, wrapper_decrypt_ip
        if self.codec is None: self.codec = SongCodec.ALAC if use_wrapper else SongCodec.AAC_LEGACY
        self.default_search_headers = {
            "accept": "*/*", "accept-language": "en-US", "origin": "https://music.apple.com", "priority": "u=1, i", "sec-fetch-site": "same-site", "sec-ch-ua-platform": '"Windows"', 
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"', "sec-ch-ua-mobile": "?0", "sec-fetch-mode": "cors", "referer": "https://music.apple.com", 
            "sec-fetch-dest": "empty", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }
        self.default_parse_headers = {
            "accept": "*/*", "accept-language": "en-US", "origin": "https://music.apple.com", "priority": "u=1, i", "sec-fetch-site": "same-site", "sec-ch-ua-platform": '"Windows"', 
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"', "sec-ch-ua-mobile": "?0", "sec-fetch-mode": "cors", "referer": "https://music.apple.com", 
            "sec-fetch-dest": "empty", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0, auto_supplement_song: bool = True):
        # fallback to general music download method
        if isinstance(song_info.download_url, str): return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id, auto_supplement_song=auto_supplement_song)
        # deal with apple stream object
        song_info, request_overrides = copy.deepcopy(song_info), copy.deepcopy(request_overrides or {}); assert isinstance(song_info.download_url, DownloadItem)
        song_info._save_path = sanitize_filepath(song_info.save_path); song_info.work_dir = os.path.dirname(song_info.save_path); IOUtils.touchdir(song_info.work_dir)
        tmp_work_dir, download_item = sanitize_filename(f'apple_id_{str(song_info.identifier)}'), song_info.download_url; IOUtils.touchdir(tmp_work_dir)
        try:
            progress.update(song_progress_id, total=None, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Downloading)")
            AppleMusicClientDownloadSongUtils.download(download_item=download_item, work_dir=tmp_work_dir, silent=self.disable_print, codec=self.codec, wrapper_decrypt_ip=self.wrapper_decrypt_ip, artist=song_info.singers, use_wrapper=self.use_wrapper, remux_mode=RemuxMode.FFMPEG); shutil.move(download_item.staged_path, song_info.save_path)
            progress.update(song_progress_id, total=os.path.getsize(song_info.save_path), advance=os.path.getsize(song_info.save_path), description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Success)")
            downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(song_info, logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else song_info); shutil.rmtree(tmp_work_dir, ignore_errors=True)
        except Exception as err:
            progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})")
            self.logger_handle.error(f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})", disable_print=self.disable_print)
        # return
        return downloaded_song_infos
    '''_initapifunctions'''
    def _initapifunctions(self, mode: str = 'search', request_overrides: dict = None):
        self.apple_music_api = (self.apple_music_api or (AppleMusicClientAPIUtils.createfromwrapper(wrapper_account_url=self.wrapper_account_url, request_overrides=request_overrides, language=self.language) if self.use_wrapper else AppleMusicClientAPIUtils.createfromnetscapecookies(cookies=self.default_cookies, request_overrides=request_overrides, language=self.language) if self.default_cookies and ('media-user-token' in self.default_cookies) else None))
        if self.apple_music_api and (not self.itunes_api): self.itunes_api = AppleMusicClientItunesApiUtils(storefront=self.apple_music_api.storefront, language=self.apple_music_api.language)
        self.account_info = self.apple_music_api.account_info if self.apple_music_api else self.account_info
        if 'authorization' not in self.default_headers: self.default_headers = (copy.deepcopy(self.apple_music_api.client.headers) if self.apple_music_api else {**self.default_headers, "authorization": f"Bearer {AppleMusicClientAPIUtils.gettoken(SimpleNamespace(client=self.session, language=self.language), request_overrides=request_overrides)}"})
        (mode == 'search') and ('authorization' not in self.default_search_headers) and setattr(self, 'default_search_headers', self.default_headers)
        (mode == 'parse') and ('authorization' not in self.default_parse_headers) and setattr(self, 'default_parse_headers', self.default_headers)
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        if (not self.default_cookies or 'media-user-token' not in self.default_cookies) and (not self.use_wrapper): self.logger_handle.warning(f'{self.source}._constructsearchurls >>> both "media-user-token" and "use_wrapper" are not configured, so song downloads are restricted and only the preview portion of the track can be downloaded.')
        rule, request_overrides = rule or {}, request_overrides or {}; self._initapifunctions(mode='search', request_overrides=request_overrides); self._initsession()
        (default_rule := {"groups": "song", "l": "en-US", "offset": "0", "term": keyword, "types": "activities,albums,apple-curators,artists,curators,editorial-items,music-movies,music-videos,playlists,record-labels,songs,stations,tv-episodes,uploaded-videos", "art[url]": "f", "extend": "artistUrl", "fields[albums]": "artistName,artistUrl,artwork,contentRating,editorialArtwork,editorialNotes,name,playParams,releaseDate,url,trackCount", "fields[artists]": "url,name,artwork", "format[resources]": "map", "include[editorial-items]": "contents", "include[songs]": "artists", "limit": "10", "omit[resource]": "autos", "platform": "web", "relate[albums]": "artists", "relate[editorial-items]": "contents", "relate[songs]": "albums", "types": "activities,albums,apple-curators,artists,curators,music-movies,music-videos,playlists,songs,stations,tv-episodes,uploaded-videos", "with": "lyrics,serverBubbles"}).update(rule)
        geo = safeextractfromdict(self.account_info, ['meta', 'subscription', 'storefront'], 'us')
        # construct search urls
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, f'https://amp-api-edge.music.apple.com/v1/catalog/{geo}/search?'
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['limit'] = page_size
            page_rule['offset'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithnonvipofficialapiv1'''
    def _parsewithnonvipofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))) or (search_result.get('type') not in {'songs'}): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            if not (download_url := safeextractfromdict(search_result, ['attributes', 'previews', 0, 'url'], '')) or not str(download_url).startswith('http'): return song_info
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(search_result, ['attributes', 'durationInMillis'], 0) or 0) / 1000
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['attributes', 'name'], None)), singers=legalizestring(safeextractfromdict(search_result, ['attributes', 'artistName'], None)), album=legalizestring(safeextractfromdict(search_result, ['attributes', 'albumName'], None)), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['attributes', 'artwork', 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.cover_url and song_info.cover_url.startswith('http'): song_info.cover_url = song_info.cover_url.format(w=600, h=600, f='jpg')
        # return
        return song_info
    '''_parsewithvipofficialapiv1'''
    def _parsewithvipofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac, codec = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source), self.codec
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))) or (search_result.get('type') not in {'songs'}): return song_info
        geo = safeextractfromdict(self.account_info, ['meta', 'subscription', 'storefront'], 'us')
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            (resp := self.get(f'https://amp-api.music.apple.com/v1/catalog/{geo}/songs/{song_id}', params={"extend": "extendedAssetUrls", "include": "lyrics,albums"}, **request_overrides)).raise_for_status()
            download_item: DownloadItem = AppleMusicClientDownloadSongUtils.getdownloaditem(song_metadata=(download_result := resp2json(resp=resp))['data'][0], playlist_metadata=None, codec=codec, apple_music_api=self.apple_music_api, itunes_api=self.itunes_api, request_overrides=request_overrides, use_wrapper=self.use_wrapper)
            with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(safeextractfromdict(search_result, ['attributes', 'durationInMillis'], 0) or 0) / 1000
            download_url_status: dict = self.audio_link_tester.test(url=download_item.stream_info.audio_track.stream_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['attributes', 'name'], None)), singers=legalizestring(safeextractfromdict(search_result, ['attributes', 'artistName'], None)), album=legalizestring(safeextractfromdict(search_result, ['attributes', 'albumName'], None)), ext=download_item.stream_info.file_format.value, 
                file_size_bytes='HLS', file_size='HLS', identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(str(download_item.lyrics.synced) or ''), cover_url=safeextractfromdict(search_result, ['attributes', 'artwork', 'url'], None), download_url=download_item, download_url_status=download_url_status,
            )
            if song_info.cover_url and song_info.cover_url.startswith('http'): song_info.cover_url = song_info.cover_url.format(w=600, h=600, f='jpg')
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for song_key, search_result in dict(resp2json(resp)['resources']['songs']).items():
                # --init song info
                song_info, search_result['song_key'] = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}}), song_key
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithnonvipofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides) if (not self.default_cookies or 'media-user-token' not in self.default_cookies) and (not self.use_wrapper) else self._parsewithvipofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
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
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, APPLE_MUSIC_HOSTS)): return song_infos
        if (not self.default_cookies or 'media-user-token' not in self.default_cookies) and (not self.use_wrapper): raise PermissionError(f'{self.source}.parseplaylist >>> both "media-user-token" and "use_wrapper" are not configured, so musicdl does not have permission to parse Apple Music playlists.')
        self._initapifunctions(mode='parse', request_overrides=request_overrides); self._initsession()
        # get tracks in playlist
        playlist_result = self.apple_music_api.getplaylist(playlist_id, request_overrides=request_overrides)
        tracks_in_playlist = safeextractfromdict(playlist_result, ['data', 0, 'relationships', 'tracks', 'data'], []) or []
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}})
                with suppress(Exception): song_info = self._parsewithvipofficialapiv1(search_result=track_info, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                if song_info.with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse song id {song_info.identifier} >>> {song_info.album} {song_info.song_name} {song_info.singers} {song_info.download_url}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result, ['data', 0, 'attributes', 'name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos