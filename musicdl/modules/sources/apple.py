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
from types import SimpleNamespace
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from ..utils.hosts import APPLE_MUSIC_HOSTS
from urllib.parse import urlencode, urlparse
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils.appleutils import AppleMusicClientDownloadSongUtils, AppleMusicClientAPIUtils, AppleMusicClientItunesApiUtils, DownloadItem, SongCodec, RemuxMode
from ..utils import touchdir, legalizestring, resp2json, seconds2hms, usesearchheaderscookies, safeextractfromdict, usedownloadheaderscookies, useparseheaderscookies, hostmatchessuffix, obtainhostname, cleanlrc, SongInfo, SongInfoUtils, AudioLinkTester


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
        request_overrides = request_overrides or {}
        if isinstance(song_info.download_url, str): return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id, auto_supplement_song=auto_supplement_song)
        try:
            touchdir(song_info.work_dir); tmp_dir = f'apple_id_{str(song_info.identifier)}'; touchdir(tmp_dir); download_item: DownloadItem = song_info.download_url
            progress.update(song_progress_id, total=1, kind='overall'); progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Downloading)")
            AppleMusicClientDownloadSongUtils.download(download_item=download_item, work_dir=tmp_dir, silent=self.disable_print, codec=self.codec, wrapper_decrypt_ip=self.wrapper_decrypt_ip, artist=song_info.singers, use_wrapper=self.use_wrapper, remux_mode=RemuxMode.FFMPEG); shutil.move(download_item.staged_path, song_info.save_path)
            progress.update(song_progress_id, total=os.path.getsize(song_info.save_path), kind='download'); progress.advance(song_progress_id, os.path.getsize(song_info.save_path))
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Success)")
            downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(copy.deepcopy(song_info), logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else copy.deepcopy(song_info)); shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception as err:
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Error: {err})")
        return downloaded_song_infos
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        if (not self.default_cookies or 'media-user-token' not in self.default_cookies) and (not self.use_wrapper): self.logger_handle.warning(f'{self.source}._constructsearchurls >>> both "media-user-token" and "use_wrapper" are not configured, so song downloads are restricted and only the preview portion of the track can be downloaded.')
        if self.use_wrapper and (not self.apple_music_api): self.apple_music_api = AppleMusicClientAPIUtils.createfromwrapper(wrapper_account_url=self.wrapper_account_url, request_overrides=request_overrides, language=self.language)
        elif self.default_cookies and ('media-user-token' in self.default_cookies) and (not self.apple_music_api): self.apple_music_api = AppleMusicClientAPIUtils.createfromnetscapecookies(cookies=self.default_cookies, request_overrides=request_overrides, language=self.language)
        if self.apple_music_api and (not self.itunes_api): self.itunes_api = AppleMusicClientItunesApiUtils(storefront=self.apple_music_api.storefront, language=self.apple_music_api.language)
        if self.apple_music_api and ('authorization' not in self.default_headers): self.default_search_headers = copy.deepcopy(self.apple_music_api.client.headers); self.default_headers = self.default_search_headers; self._initsession(); self.account_info = self.apple_music_api.account_info
        elif ('authorization' not in self.default_headers): virtual_client = SimpleNamespace(client=self.session, language=self.language); self.default_search_headers.update({"authorization": f"Bearer {AppleMusicClientAPIUtils.gettoken(virtual_client, request_overrides=request_overrides)}"}); self.default_headers = self.default_search_headers; self._initsession()
        # search rules
        default_rule = {
            "groups": "song", "l": "en-US", "offset": "0", "term": keyword, "types": "activities,albums,apple-curators,artists,curators,editorial-items,music-movies,music-videos,playlists,record-labels,songs,stations,tv-episodes,uploaded-videos", "art[url]": "f", "extend": "artistUrl", "fields[albums]": "artistName,artistUrl,artwork,contentRating,editorialArtwork,editorialNotes,name,playParams,releaseDate,url,trackCount", "fields[artists]": "url,name,artwork",
            "format[resources]": "map", "include[editorial-items]": "contents", "include[songs]": "artists", "limit": "10", "omit[resource]": "autos", "platform": "web", "relate[albums]": "artists", "relate[editorial-items]": "contents", "relate[songs]": "albums", "types": "activities,albums,apple-curators,artists,curators,music-movies,music-videos,playlists,songs,stations,tv-episodes,uploaded-videos", "with": "lyrics,serverBubbles", 
        }
        default_rule.update(rule)
        geo = safeextractfromdict(self.account_info, ['meta', 'subscription', 'storefront'], 'us')
        # construct search urls based on search rules
        base_url = f'https://amp-api-edge.music.apple.com/v1/catalog/{geo}/search?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['limit'] = page_size
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
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            if not (download_url := safeextractfromdict(search_result, ['attributes', 'previews', 0, 'url'], '')) or not str(download_url).startswith('http'): return song_info
            try: duration_in_secs = float(safeextractfromdict(search_result, ['attributes', 'durationInMillis'], 0)) / 1000
            except Exception: duration_in_secs = 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['attributes', 'name'], None)), singers=legalizestring(safeextractfromdict(search_result, ['attributes', 'artistName'], None)), album=legalizestring(safeextractfromdict(search_result, ['attributes', 'albumName'], None)), 
                ext=str(download_url).split('?')[0].split('.')[-1], file_size=None, identifier=song_id, duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['attributes', 'artwork', 'url'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
            elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
            if song_info.cover_url and song_info.cover_url.startswith('http'): song_info.cover_url = song_info.cover_url.format(w=600, h=600, f='jpg')
        # return
        return song_info
    '''_parsewithvipofficialapiv1'''
    def _parsewithvipofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac, codec = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source), self.codec
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))) or (search_result.get('type') not in {'songs'}): return song_info
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            geo = safeextractfromdict(self.account_info, ['meta', 'subscription', 'storefront'], 'us')
            (resp := self.get(f'https://amp-api.music.apple.com/v1/catalog/{geo}/songs/{song_id}', params={"extend": "extendedAssetUrls", "include": "lyrics,albums"}, **request_overrides)).raise_for_status()
            download_item: DownloadItem = AppleMusicClientDownloadSongUtils.getdownloaditem(song_metadata=(download_result := resp2json(resp=resp))['data'][0], playlist_metadata=None, codec=codec, apple_music_api=self.apple_music_api, itunes_api=self.itunes_api, request_overrides=request_overrides, use_wrapper=self.use_wrapper)
            (resp := self.get(download_item.stream_info.audio_track.stream_url, **request_overrides)).raise_for_status()
            try: duration_in_secs = float(safeextractfromdict(search_result, ['attributes', 'durationInMillis'], 0)) / 1000
            except Exception: duration_in_secs = 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['attributes', 'name'], None)), singers=legalizestring(safeextractfromdict(search_result, ['attributes', 'artistName'], None)), album=legalizestring(safeextractfromdict(search_result, ['attributes', 'albumName'], None)),
                ext=download_item.stream_info.file_format.value, file_size='HLS', identifier=song_id, duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric=cleanlrc(str(download_item.lyrics.synced)) or 'NULL', cover_url=safeextractfromdict(search_result, ['attributes', 'artwork', 'url'], None), download_url=download_item, download_url_status={'ok': True},
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
                search_result['song_key'] = song_key
                # --parse with non-vip official apis
                if (not self.default_cookies or 'media-user-token' not in self.default_cookies) and (not self.use_wrapper):
                    try: song_info = self._parsewithnonvipofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                    except Exception: continue
                # --parse with vip official apis
                else:
                    try: song_info = self._parsewithvipofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                    except Exception: continue
                # --append to song_infos
                if not song_info.with_valid_download_url: continue
                song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
            # --update progress
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Error: {err})")
        # return
        return song_infos
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        # init
        request_overrides = request_overrides or {}
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **request_overrides).url
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, APPLE_MUSIC_HOSTS)): return song_infos
        if (not self.default_cookies or 'media-user-token' not in self.default_cookies) and (not self.use_wrapper): raise PermissionError(f'{self.source}.parseplaylist >>> both "media-user-token" and "use_wrapper" are not configured, so musicdl does not have permission to parse Apple Music playlists.')
        if self.use_wrapper and (not self.apple_music_api): self.apple_music_api = AppleMusicClientAPIUtils.createfromwrapper(wrapper_account_url=self.wrapper_account_url, request_overrides=request_overrides, language=self.language)
        elif self.default_cookies and ('media-user-token' in self.default_cookies) and (not self.apple_music_api): self.apple_music_api = AppleMusicClientAPIUtils.createfromnetscapecookies(cookies=self.default_cookies, request_overrides=request_overrides, language=self.language)
        self.apple_music_api = AppleMusicClientAPIUtils.createfromnetscapecookies(cookies=self.default_cookies, request_overrides=request_overrides, language=self.language)
        if self.apple_music_api and (not self.itunes_api): self.itunes_api = AppleMusicClientItunesApiUtils(storefront=self.apple_music_api.storefront, language=self.apple_music_api.language)
        if self.apple_music_api and ('authorization' not in self.default_headers): self.default_search_headers = copy.deepcopy(self.apple_music_api.client.headers); self.default_headers = self.default_search_headers; self._initsession(); self.account_info = self.apple_music_api.account_info
        elif ('authorization' not in self.default_headers): virtual_client = SimpleNamespace(client=self.session, language=self.language); self.default_search_headers.update({"authorization": f"Bearer {AppleMusicClientAPIUtils.gettoken(virtual_client, request_overrides=request_overrides)}"}); self.default_headers = self.default_search_headers; self._initsession()
        # get tracks in playlist
        playlist_result = self.apple_music_api.getplaylist(playlist_id, request_overrides=request_overrides)
        tracks_in_playlist = safeextractfromdict(playlist_result, ['data', 0, 'relationships', 'tracks', 'data'], []) or []
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed (0/{len(tracks_in_playlist)})", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1)
                main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed ({idx}/{len(tracks_in_playlist)})")
                try: song_info = self._parsewithvipofficialapiv1(search_result=track_info, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                except Exception: song_info = SongInfo(source=self.source)
                if song_info.with_valid_download_url: song_infos.append(song_info)
            main_process_context.advance(main_progress_id, 1)
            main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed ({idx+1}/{len(tracks_in_playlist)})")
        # post processing
        playlist_name = safeextractfromdict(playlist_result, ['data', 0, 'attributes', 'name'], None)
        song_infos = self._removeduplicates(song_infos=song_infos); work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        # return results
        return song_infos