'''
Function:
    Implementation of TIDALMusicClient: https://tidal.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import aigpy
import base64
import tempfile
from pathlib import Path
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from ..utils.hosts import TIDAL_MUSIC_HOSTS
from urllib.parse import urlencode, urlparse
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils.tidalutils import TIDALMusicClientUtils, SearchResult, SessionStorage, Track, TidalTvSession, StreamUrl, Artist
from ..utils import legalizestring, resp2json, seconds2hms, touchdir, replacefile, usesearchheaderscookies, usedownloadheaderscookies, safeextractfromdict, useparseheaderscookies, hostmatchessuffix, obtainhostname, cleanlrc, SongInfo, SongInfoUtils


'''TIDALMusicClient'''
class TIDALMusicClient(BaseMusicClient):
    source = 'TIDALMusicClient'
    def __init__(self, **kwargs):
        super(TIDALMusicClient, self).__init__(**kwargs)
        assert self.default_search_cookies or self.default_download_cookies or self.default_parse_cookies, f'cookies are not configured, so TIDAL is unavailable, refer to https://musicdl.readthedocs.io/en/latest/Quickstart.html#tidal-high-quality-music-download.'
        session_storage = SessionStorage(**(self.default_search_cookies or self.default_download_cookies or self.default_parse_cookies))
        self.tidal_tv_session = TidalTvSession(session_storage.client_id, session_storage.client_secret)
        self.tidal_tv_session.setstorage(session_storage); TIDALMusicClientUtils.SESSION_STORAGE = session_storage
        self.default_search_headers = {"X-Tidal-Token": self.tidal_tv_session.client_id, "Authorization": f"Bearer {self.tidal_tv_session.access_token}", "Connection": "Keep-Alive", "Accept-Encoding": "gzip", "User-Agent": "TIDAL_ANDROID/1039 okhttp/3.14.9"}
        self.default_parse_headers = {"X-Tidal-Token": self.tidal_tv_session.client_id, "Authorization": f"Bearer {self.tidal_tv_session.access_token}", "Connection": "Keep-Alive", "Accept-Encoding": "gzip", "User-Agent": "TIDAL_ANDROID/1039 okhttp/3.14.9"}
        self.default_download_headers = {"X-Tidal-Token": self.tidal_tv_session.client_id, "Authorization": f"Bearer {self.tidal_tv_session.access_token}", "Connection": "Keep-Alive", "Accept-Encoding": "gzip", "User-Agent": "TIDAL_ANDROID/1039 okhttp/3.14.9"}
        self.default_headers = self.default_search_headers
        self.default_search_cookies = {}; self.default_parse_cookies = {}; self.default_download_cookies = {}; self.default_cookies = {}
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0, auto_supplement_song: bool = True):
        if isinstance(song_info.download_url, str): return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id, auto_supplement_song=auto_supplement_song)
        request_overrides = request_overrides or {}
        try:
            touchdir(song_info.work_dir); stream_url: StreamUrl = song_info.download_url; stream_resp: dict = song_info.raw_data['download']
            download_ext, final_ext = TIDALMusicClientUtils.guessstreamextension(stream=stream_url), f'.{song_info.ext}'
            remux_required = TIDALMusicClientUtils.shouldremuxflac(download_ext, final_ext, stream_url)
            assert TIDALMusicClientUtils.flacremuxavailable(), f'FLAC stream for {stream_url.url} requires remuxing but no backend is available.'
            progress.update(song_progress_id, total=1, kind='overall'); progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Downloading)")
            with tempfile.TemporaryDirectory(prefix="musicdl-TIDALMusicClient-track-") as tmpdir:
                download_part = os.path.join(tmpdir, f"download{download_ext}.part" if download_ext else "download.part")
                if "vnd.tidal.bt" in stream_resp['manifestMimeType']:
                    tool = aigpy.download.DownloadTool(download_part, stream_url.urls); tool.setUserProgress(None); tool.setPartSize(song_info.chunk_size)
                    check, err = tool.start(showProgress=False)
                    if not check: raise RuntimeError(err)
                elif "dash+xml" in stream_resp['manifestMimeType']:
                    local_file_path, manifest_content = os.path.join(tmpdir, str(song_info.identifier) + '.mpd'), base64.b64decode(stream_resp['manifest'])
                    with open(local_file_path, "wb") as fp: fp.write(manifest_content)
                    check = TIDALMusicClientUtils.downloadstreamwithnm3u8dlre(local_file_path, download_part, silent=self.disable_print, random_uuid=str(song_info.identifier))
                    if not check: raise RuntimeError(f"N_m3u8DL-RE error while dealing with {manifest_content.decode('utf-8')}")
                    download_part = max(Path(download_part).parent.glob(f"{Path(download_part).name}*"), key=lambda p: p.stat().st_mtime, default=None)
                decrypted_target, remux_target = os.path.join(tmpdir, f"decrypted{download_ext}" if download_ext else "decrypted"), os.path.join(tmpdir, "remux.flac")
                decrypted_path = TIDALMusicClientUtils.decryptdownloadedaudio(stream_url, download_part, decrypted_target); processed_path = decrypted_path
                if remux_required:
                    processed_path, backend_used = TIDALMusicClientUtils.remuxflacstream(decrypted_path, remux_target)
                    if processed_path != decrypted_path and os.path.exists(decrypted_path): os.remove(decrypted_path)
                    else: final_ext = download_ext; processed_path = decrypted_path
                replacefile(processed_path, song_info.save_path)
            progress.update(song_progress_id, total=os.path.getsize(song_info.save_path), kind='download'); progress.advance(song_progress_id, os.path.getsize(song_info.save_path))
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Success)")
            downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(copy.deepcopy(song_info), logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else copy.deepcopy(song_info))
        except Exception as err:
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Error: {err})")
        return downloaded_song_infos
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        self.tidal_tv_session.refresh(request_overrides=request_overrides); TIDALMusicClientUtils.SESSION_STORAGE = self.tidal_tv_session.getstorage()
        self.default_headers.update({"Authorization": f"Bearer {self.tidal_tv_session.access_token}"})
        self.default_search_headers.update({"Authorization": f"Bearer {self.tidal_tv_session.access_token}"})
        self.default_parse_headers.update({"Authorization": f"Bearer {self.tidal_tv_session.access_token}"})
        self.default_download_headers.update({"Authorization": f"Bearer {self.tidal_tv_session.access_token}"})
        # search rules
        default_rule = {'countryCode': self.tidal_tv_session.country_code, 'limit': 10, 'offset': 0, 'query': keyword, 'types': 'ARTISTS,ALBUMS,TRACKS,VIDEOS,PLAYLISTS'}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://api.tidalhifi.com/v1/search?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['limit'] = page_size
            page_rule['offset'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: Track, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, Track)) or (not (song_id := search_result.id)): return song_info
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            for quality in TIDALMusicClientUtils.MUSIC_QUALITIES:
                try: download_url, stream_resp = TIDALMusicClientUtils.getstreamurl(song_id, quality=quality[1], apply_thirdpart_apis=(not self.tidal_tv_session.isvipaccount(request_overrides=request_overrides)), request_overrides=request_overrides)
                except Exception: continue
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': stream_resp, 'lyric': {}, 'quality': quality}, source=self.source, song_name=legalizestring(search_result.title), singers=legalizestring(', '.join([str(singer.name) for singer in (search_result.artists or []) if isinstance(singer, Artist)])),
                    album=legalizestring(search_result.album.title), ext=TIDALMusicClientUtils.getexpectedextension(download_url).removeprefix('.'), file_size_bytes='HLS', file_size='HLS', identifier=search_result.id, duration_s=search_result.duration, duration=seconds2hms(search_result.duration), lyric=None, 
                    cover_url=TIDALMusicClientUtils.getcoverurl(search_result.album.cover), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url.urls[0], request_overrides),
                )
                if song_info.with_valid_download_url: break
        if not song_info.with_valid_download_url: return song_info
        # supplement lyric results
        params = {'countryCode': self.tidal_tv_session.country_code, 'include': 'lyrics'}
        try: (resp := self.get(f'https://openapi.tidal.com/v2/tracks/{song_id}', params=params, **request_overrides)).raise_for_status(); lyric = cleanlrc(safeextractfromdict((lyric_result := resp2json(resp)), ['included', 0, 'attributes', 'lrcText'], 'NULL'))
        except Exception: lyric_result, lyric = {}, 'NULL'
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
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
            for search_result in aigpy.model.dictToModel(resp2json(resp=resp), SearchResult()).tracks.items:
                # --parse with official apis
                try: song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                except Exception: song_info = SongInfo(source=self.source)
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
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, TIDAL_MUSIC_HOSTS)): return song_infos
        self.tidal_tv_session.refresh(request_overrides=request_overrides); TIDALMusicClientUtils.SESSION_STORAGE = self.tidal_tv_session.getstorage()
        self.default_headers.update({"Authorization": f"Bearer {self.tidal_tv_session.access_token}"})
        self.default_search_headers.update({"Authorization": f"Bearer {self.tidal_tv_session.access_token}"})
        self.default_parse_headers.update({"Authorization": f"Bearer {self.tidal_tv_session.access_token}"})
        self.default_download_headers.update({"Authorization": f"Bearer {self.tidal_tv_session.access_token}"})
        # get tracks in playlist
        tracks_in_playlist, page, page_size, playlist_result_first = [], 1, 50, {}
        while True:
            params = {'offset': (page - 1) * page_size, 'limit': page_size, 'countryCode': self.tidal_tv_session.country_code, 'locale': 'en_US', 'deviceType': 'BROWSER'}
            try: (resp := self.get(f"https://tidal.com/v1/playlists/{playlist_id}/items", params=params, **request_overrides)).raise_for_status()
            except Exception: break
            if (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['items'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['items'], [])); page += 1
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['totalNumberOfItems'], 0)) <= len(tracks_in_playlist)): break
        for track_idx in range(len(tracks_in_playlist)):
            try: tracks_in_playlist[track_idx] = aigpy.model.dictToModel(tracks_in_playlist[track_idx]['item'], Track()); assert tracks_in_playlist[track_idx].id
            except Exception: continue
        tracks_in_playlist = list({d.id: d for d in tracks_in_playlist}.values())
        try: playlist_result_first['meta_info'] = resp2json(self.get(f'https://tidal.com/v1/playlists/{playlist_id}?countryCode={self.tidal_tv_session.country_code}&locale=en_US&deviceType=BROWSER', **request_overrides))
        except Exception: pass
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed (0/{len(tracks_in_playlist)})", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1)
                main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed ({idx}/{len(tracks_in_playlist)})")
                try: song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                except Exception: song_info = SongInfo(source=self.source)
                if song_info.with_valid_download_url: song_infos.append(song_info)
            main_process_context.advance(main_progress_id, 1)
            main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed ({idx+1}/{len(tracks_in_playlist)})")
        # post processing
        playlist_name = safeextractfromdict(playlist_result_first, ['meta_info', 'title'], None)
        song_infos = self._removeduplicates(song_infos=song_infos); work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        # return results
        return song_infos
