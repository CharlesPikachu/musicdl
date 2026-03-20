'''
Function:
    Implementation of DeezerMusicClient: https://www.deezer.com/us/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import requests
from pathlib import Path
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from ..utils.hosts import DEEZER_MUSIC_HOSTS
from urllib.parse import urlencode, urlparse
from ..utils.deezerutils import DeezerMusicClientUtils
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import replacefile, touchdir, legalizestring, resp2json, seconds2hms, usesearchheaderscookies, usedownloadheaderscookies, safeextractfromdict, extractdurationsecondsfromlrc, useparseheaderscookies, obtainhostname, hostmatchessuffix, byte2mb, cleanlrc, SongInfo, AudioLinkTester, SongInfoUtils, LyricSearchClient


'''DeezerMusicClient'''
class DeezerMusicClient(BaseMusicClient):
    source = 'DeezerMusicClient'
    def __init__(self, **kwargs):
        kwargs['maintain_session'] = True
        super(DeezerMusicClient, self).__init__(**kwargs)
        if self.default_search_cookies: assert "arl" in self.default_search_cookies, '"arl" should be configured, refer to https://musicdl.readthedocs.io/en/latest/Quickstart.html#deezer-music-download'
        if self.default_parse_cookies: assert "arl" in self.default_parse_cookies, '"arl" should be configured, refer to https://musicdl.readthedocs.io/en/latest/Quickstart.html#deezer-music-download'
        if self.default_download_cookies: assert "arl" in self.default_download_cookies, '"arl" should be configured, refer to https://musicdl.readthedocs.io/en/latest/Quickstart.html#deezer-music-download'
        self.default_search_headers = {
            'Pragma': 'no-cache', 'Origin': 'https://www.deezer.com', 'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-US,en;q=0.9', 'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:135.0) Gecko/20100101 Firefox/135.0', 'DNT': '1',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Accept': '*/*', 'Cache-Control': 'no-cache', 'X-Requested-With': 'XMLHttpRequest', 'Connection': 'keep-alive', 'Referer': 'https://www.deezer.com/login', 
        }
        self.default_parse_headers = {
            'Pragma': 'no-cache', 'Origin': 'https://www.deezer.com', 'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-US,en;q=0.9', 'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:135.0) Gecko/20100101 Firefox/135.0', 'DNT': '1',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Accept': '*/*', 'Cache-Control': 'no-cache', 'X-Requested-With': 'XMLHttpRequest', 'Connection': 'keep-alive', 'Referer': 'https://www.deezer.com/login', 
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers; self.auth_info = {}
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0, auto_supplement_song: bool = True):
        super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=[], progress=progress, song_progress_id=song_progress_id, auto_supplement_song=False)
        if DeezerMusicClientUtils.IS_ENCRYPTED_RPATTERN.search(song_info.download_url) is None: downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(copy.deepcopy(song_info), logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else copy.deepcopy(song_info)); return downloaded_song_infos
        output_filepath = (output_filepath := Path(song_info.save_path)).parent / f'{output_filepath.stem}.decrypt'
        blowfish_key = DeezerMusicClientUtils.generateblowfishkey(str(song_info.raw_data.get('id')))
        DeezerMusicClientUtils.decryptdownloadedaudiofile(src_path=str(song_info.save_path), dst_path=str(output_filepath), blowfish_key=blowfish_key)
        replacefile(str(output_filepath), str(song_info.save_path))
        downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(copy.deepcopy(song_info), logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else copy.deepcopy(song_info))
        return downloaded_song_infos
    '''_setauthinfo'''
    def _setauthinfo(self, request_overrides: dict = None):
        if self.auth_info: return
        request_overrides = request_overrides or {}
        (resp := self.post('http://www.deezer.com/ajax/gw-light.php', params={'api_version': "1.0", 'api_token': 'null', 'input': '3', 'method': 'deezer.getUserData'}, **request_overrides)).raise_for_status()
        self.auth_info = resp2json(resp=resp)
        return self.auth_info
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}; self._setauthinfo(request_overrides=request_overrides)
        if (not self.default_cookies or 'arl' not in self.default_cookies): self.logger_handle.warning(f'{self.source}._constructsearchurls >>> cookies are not configured, so song downloads are restricted and only the preview portion of the track can be downloaded.')
        # search rules
        default_rule = {'q': keyword, 'index': 1, 'limit': 20}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://api.deezer.com/search/track?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['limit'] = page_size
            page_rule['index'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, is_fallback_retry: bool = False, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source); self._setauthinfo(request_overrides=request_overrides)
        if (not isinstance(search_result, dict)) or (not (song_id := (search_result.get('id') or search_result.get('SNG_ID')))): return song_info
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            # --track details
            try: (resp := self.post('http://www.deezer.com/ajax/gw-light.php', params={'api_version': "1.0", 'api_token': safeextractfromdict(self.auth_info, ['results', 'checkForm'], None), 'input': '3', 'method': 'song.getData'}, json={'SNG_ID': song_id}, **request_overrides)).raise_for_status(); assert not safeextractfromdict((download_result := resp2json(resp=resp)), ['error'], None)
            except: (resp := self.get(f'https://api.deezer.com/track/{song_id}', **request_overrides)).raise_for_status(); download_result = resp2json(resp=resp)
            # --necessary information
            license_token = safeextractfromdict(self.auth_info, ['results', 'USER', 'OPTIONS', 'license_token'], None)
            track_token = safeextractfromdict(download_result, ['results', 'TRACK_TOKEN'], None) or download_result.get('track_token')
            track_hash = safeextractfromdict(download_result, ['results', 'MD5_ORIGIN'], None) or download_result.get('md5_origin')
            media_version = safeextractfromdict(download_result, ['results', 'MEDIA_VERSION'], None) or download_result.get('media_version')
            fallback_song_id = safeextractfromdict(download_result, ['results', 'FALLBACK', 'SNG_ID'], None) or safeextractfromdict(download_result, ['fallback', 'sng_id'], None) or safeextractfromdict(download_result, ['fallback', 'id'], None)
            # --fetch from high to low qualities
            for quality in DeezerMusicClientUtils.MUSIC_QUALITIES:
                if not track_token or not license_token: continue
                try: (resp := self.post("https://media.deezer.com/v1/get_url", json={'license_token': license_token, 'media': [{'type': "FULL", "formats": [{"cipher": "BF_CBC_STRIPE", "format": quality}]}], 'track_tokens': [track_token,]}, **request_overrides)).raise_for_status()
                except Exception: continue
                download_result['track_details'] = resp2json(resp=resp); candidate_results = safeextractfromdict(download_result['track_details'], ['data', 0, 'media', 0, 'sources'], []) or []
                if not (candidate_results := [c for c in candidate_results if isinstance(c, dict) and c.get('url') and str(c.get('url')).startswith('http')]): continue
                for candidate_result in candidate_results:
                    try: file_size_bytes = float(safeextractfromdict(download_result['track_details'], ['data', 0, 'media', 0, 'filesize'], 0))
                    except Exception: file_size_bytes = 0
                    try: duration_in_secs = float(safeextractfromdict(download_result, ['results', 'DURATION'], 0) or download_result.get('duration', 0))
                    except Exception: duration_in_secs = 0
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'id': song_id}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['results', 'SNG_TITLE'], None) or download_result.get('title')), singers=legalizestring(safeextractfromdict(download_result, ['results', 'ART_NAME'], None) or safeextractfromdict(download_result, ['artist', 'name'], None)), 
                        album=legalizestring(safeextractfromdict(download_result, ['results', 'ALB_TITLE'], None) or safeextractfromdict(download_result, ['album', 'title'], None)), ext=str(candidate_result['url']).split('?')[0].split('.')[-1], file_size_bytes=int(file_size_bytes), file_size=byte2mb(file_size_bytes), identifier=str(song_id), duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric=None, 
                        cover_url=DeezerMusicClientUtils.getcoverurl(safeextractfromdict(download_result, ['results', 'ALB_PICTURE'], None)) or safeextractfromdict(download_result, ['album', 'cover_xl'], None), download_url=candidate_result['url'], download_url_status=self.audio_link_tester.test(candidate_result['url'], request_overrides),
                    )
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                    elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
                    if song_info.with_valid_download_url: break
                if song_info.with_valid_download_url: break
            # --fallback id retry if possible
            if (not song_info.with_valid_download_url) and (not is_fallback_retry) and fallback_song_id: return self._parsewithofficialapiv1(search_result={'id': fallback_song_id}, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, lossless_quality_definitions=lossless_quality_definitions, is_fallback_retry=True, request_overrides=request_overrides)
            # --manually construct download url, pretty sketchy
            if (not song_info.with_valid_download_url) and (media_version is not None) and (track_hash is not None):
                download_url = DeezerMusicClientUtils.getencryptedfileurl(song_id, track_hash=track_hash, media_version=media_version)
                try: duration_in_secs = float(safeextractfromdict(download_result, ['results', 'DURATION'], 0) or download_result.get('duration', 0))
                except Exception: duration_in_secs = 0
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'id': song_id}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['results', 'SNG_TITLE'], None) or download_result.get('title')), singers=legalizestring(safeextractfromdict(download_result, ['results', 'ART_NAME'], None) or safeextractfromdict(download_result, ['artist', 'name'], None)), album=legalizestring(safeextractfromdict(download_result, ['results', 'ALB_TITLE'], None) or safeextractfromdict(download_result, ['album', 'title'], None)), 
                    ext='mp3', file_size_bytes=None, file_size=None, identifier=str(song_id), duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric=None, cover_url=DeezerMusicClientUtils.getcoverurl(safeextractfromdict(download_result, ['results', 'ALB_PICTURE'], None)) or safeextractfromdict(download_result, ['album', 'cover_xl'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                )
                song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                song_info.file_size = song_info.download_url_status['probe_status']['file_size']; song_info.ext = song_info.download_url_status['probe_status']['ext']
                if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
            # --use preview audio link
            if (not song_info.with_valid_download_url):
                download_url = safeextractfromdict(download_result, ['results', 'MEDIA', 0, 'HREF'], None) or download_result.get('preview')
                try: duration_in_secs = float(safeextractfromdict(download_result, ['results', 'DURATION'], 0) or download_result.get('duration', 0))
                except Exception: duration_in_secs = 0
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'id': song_id}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['results', 'SNG_TITLE'], None) or download_result.get('title')), singers=legalizestring(safeextractfromdict(download_result, ['results', 'ART_NAME'], None) or safeextractfromdict(download_result, ['artist', 'name'], None)), album=legalizestring(safeextractfromdict(download_result, ['results', 'ALB_TITLE'], None) or safeextractfromdict(download_result, ['album', 'title'], None)), 
                    ext=str(download_url).split('?')[0].split('.')[-1], file_size_bytes=None, file_size=None, identifier=str(song_id), duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric=None, cover_url=DeezerMusicClientUtils.getcoverurl(safeextractfromdict(download_result, ['results', 'ALB_PICTURE'], None)) or safeextractfromdict(download_result, ['album', 'cover_xl'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                )
                song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
        if not song_info.with_valid_download_url: return song_info
        # supplement lyric results
        try: (resp := self.post('https://auth.deezer.com/login/renew?jo=p&rto=c&i=c', **request_overrides)).raise_for_status(); headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Origin": "https://www.deezer.com", "Referer": "https://www.deezer.com/", "Authorization": f"Bearer {resp2json(resp=resp)['jwt']}"}; payload = {"operationName": "GetLyrics", "variables": {"trackId": str(song_id)}, "query": "query GetLyrics($trackId: String!) { track(trackId: $trackId) { id lyrics { id text ...SynchronizedWordByWordLines ...SynchronizedLines licence copyright writers __typename } __typename } } fragment SynchronizedWordByWordLines on Lyrics { id synchronizedWordByWordLines { start end words { start end word __typename } __typename } __typename } fragment SynchronizedLines on Lyrics { id synchronizedLines { lrcTimestamp line lineTranslated milliseconds duration __typename } __typename }"}; (resp := requests.post("https://pipe.deezer.com/api", headers=headers, json=payload, **request_overrides)).raise_for_status(); lyric_result = resp2json(resp=resp); lyric = cleanlrc(DeezerMusicClientUtils.covert2lrclyrics(lyric_result['data']['track']['lyrics'])) or 'NULL'
        except Exception: lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration = seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}; self._setauthinfo(request_overrides=request_overrides)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp=resp)['data']:
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
        request_overrides = request_overrides or {}; self._setauthinfo(request_overrides=request_overrides)
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **request_overrides).url
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, DEEZER_MUSIC_HOSTS)): return song_infos
        if (not self.default_cookies or 'arl' not in self.default_cookies): self.logger_handle.warning(f'{self.source}.parseplaylist >>> cookies are not configured, so song downloads are restricted and only the preview portion of the track can be downloaded.')
        # get tracks in playlist
        tracks_in_playlist, page, page_size, playlist_result_first = [], 1, 500, {}
        while True:
            payload = {'playlist_id': playlist_id, 'start': (page - 1) * page_size, 'tab': 0, 'header': True, 'lang': 'de', 'nb': page_size}
            try: (resp := self.post(f"https://www.deezer.com/ajax/gw-light.php?method=deezer.pagePlaylist&input=3&api_version=1.0&api_token={safeextractfromdict(self.auth_info, ['results', 'checkForm'], None)}", json=payload, **request_overrides)).raise_for_status()
            except Exception: break
            if not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['results', 'SONGS', 'data'], []): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['results', 'SONGS', 'data'], [])); page += 1
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['results', 'DATA', 'NB_SONG'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["SNG_ID"]: d for d in tracks_in_playlist}.values())
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
        playlist_name = safeextractfromdict(playlist_result_first, ['results', 'DATA', 'TITLE'], None)
        song_infos = self._removeduplicates(song_infos=song_infos); work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        # return results
        return song_infos