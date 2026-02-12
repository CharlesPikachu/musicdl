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
from rich.progress import Progress
from urllib.parse import urlencode
from ..utils.tidalutils import TIDALMusicClientUtils, SearchResult, SessionStorage, Track, TidalTvSession, StreamUrl, Artist
from ..utils import legalizestring, resp2json, seconds2hms, touchdir, replacefile, usesearchheaderscookies, usedownloadheaderscookies, safeextractfromdict, cleanlrc, SongInfo, SongInfoUtils


'''TIDALMusicClient'''
class TIDALMusicClient(BaseMusicClient):
    source = 'TIDALMusicClient'
    def __init__(self, **kwargs):
        super(TIDALMusicClient, self).__init__(**kwargs)
        assert self.default_cookies, f'{self.source}.__init__ >>> cookies are not configured, so TIDAL is unavailable, refer to https://musicdl.readthedocs.io/zh/latest/Quickstart.html#tidal-high-quality-music-download.'
        session_storage = SessionStorage(**self.default_cookies)
        self.tidal_tv_session = TidalTvSession(session_storage.client_id, session_storage.client_secret)
        self.tidal_tv_session.setstorage(session_storage); TIDALMusicClientUtils.SESSION_STORAGE = session_storage
        self.default_search_headers = {"X-Tidal-Token": self.tidal_tv_session.client_id, "Authorization": f"Bearer {self.tidal_tv_session.access_token}", "Connection": "Keep-Alive", "Accept-Encoding": "gzip", "User-Agent": "TIDAL_ANDROID/1039 okhttp/3.14.9"}
        self.default_download_headers = {"X-Tidal-Token": self.tidal_tv_session.client_id, "Authorization": f"Bearer {self.tidal_tv_session.access_token}", "Connection": "Keep-Alive", "Accept-Encoding": "gzip", "User-Agent": "TIDAL_ANDROID/1039 okhttp/3.14.9"}
        self.default_headers = self.default_search_headers
        self.default_search_cookies = {}; self.default_download_cookies = {}; self.default_cookies = {}
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0):
        if isinstance(song_info.download_url, str): return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id)
        request_overrides = request_overrides or {}
        try:
            touchdir(song_info.work_dir)
            stream_url: StreamUrl = song_info.download_url; stream_resp: dict = song_info.raw_data['download']
            download_ext, final_ext = TIDALMusicClientUtils.guessstreamextension(stream=stream_url), f'.{song_info.ext}'
            remux_required = TIDALMusicClientUtils.shouldremuxflac(download_ext, final_ext, stream_url)
            assert TIDALMusicClientUtils.flacremuxavailable(), f'FLAC stream for {stream_url.url} requires remuxing but no backend is available.'
            progress.update(song_progress_id, total=1, kind='overall')
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Downloading)")
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
            progress.update(song_progress_id, total=os.path.getsize(song_info.save_path), kind='download')
            progress.advance(song_progress_id, os.path.getsize(song_info.save_path))
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Success)")
            downloaded_song_infos.append(SongInfoUtils.fillsongtechinfo(copy.deepcopy(song_info), logger_handle=self.logger_handle, disable_print=self.disable_print))
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
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results: list[Track] = aigpy.model.dictToModel(resp2json(resp=resp), SearchResult()).tracks.items
            for search_result in search_results:
                if not search_result.id: continue
                song_info = SongInfo(source=self.source)
                # --download results
                for quality in TIDALMusicClientUtils.MUSIC_QUALITIES:
                    try: download_url, stream_resp = TIDALMusicClientUtils.getstreamurl(search_result.id, quality=quality[1], request_overrides=request_overrides)
                    except Exception: continue
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': stream_resp, 'lyric': {}, 'quality': quality}, source=self.source, song_name=legalizestring(search_result.title), singers=legalizestring(', '.join([str(singer.name) for singer in (search_result.artists or []) if isinstance(singer, Artist)])),
                        album=legalizestring(search_result.album.title), ext=TIDALMusicClientUtils.getexpectedextension(download_url).removeprefix('.'), file_size_bytes='HLS', file_size='HLS', identifier=search_result.id, duration_s=search_result.duration, duration=seconds2hms(search_result.duration), lyric=None, 
                        cover_url=TIDALMusicClientUtils.getcoverurl(search_result.album.cover), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url.urls[0], request_overrides),
                    )
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: continue
                # --lyric results
                params = {'countryCode': self.tidal_tv_session.country_code, 'include': 'lyrics'}
                try:
                    resp = self.get(f'https://openapi.tidal.com/v2/tracks/{search_result.id}', params=params, **request_overrides)
                    resp.raise_for_status()
                    lyric_result = resp2json(resp)
                    lyric = cleanlrc(safeextractfromdict(lyric_result, ['included', 0, 'attributes', 'lrcText'], 'NULL'))
                except:
                    lyric_result, lyric = {}, 'NULL'
                song_info.raw_data['lyric'] = lyric_result
                song_info.lyric = lyric
                # --append to song_infos
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