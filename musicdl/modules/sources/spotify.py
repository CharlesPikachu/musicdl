'''
Function:
    Implementation of SpotifyMusicClient: https://open.spotify.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
from bs4 import BeautifulSoup
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from urllib.parse import urlparse, parse_qs
from ..utils.hosts import SPOTIFY_MUSIC_HOSTS
from ..utils.spotifyutils import SpotifyMusicClientPlaylistUtils, SpotifyMusicClientSearchUtils
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import byte2mb, touchdir, legalizestring, resp2json, seconds2hms, usesearchheaderscookies, safeextractfromdict, naiveguessextfromaudiobytes, useparseheaderscookies, obtainhostname, hostmatchessuffix, extractdurationsecondsfromlrc, SongInfo, AudioLinkTester, LyricSearchClient


'''SpotifyMusicClient'''
class SpotifyMusicClient(BaseMusicClient):
    source = 'SpotifyMusicClient'
    def __init__(self, **kwargs):
        super(SpotifyMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "Accept": "application/json", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://open.spotify.com/", "Origin": "https://open.spotify.com/"}
        self.default_parse_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "Accept": "application/json", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://open.spotify.com/", "Origin": "https://open.spotify.com/"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls based on search rules
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            search_urls.append({'api': SpotifyMusicClientSearchUtils.searchbykeyword, 'inputs': {'session': copy.deepcopy(self.session), 'query': keyword, 'limit': page_size, 'offset': count, 'rule': copy.deepcopy(rule), 'request_overrides': request_overrides}})
            count += page_size
        # return
        return search_urls
    '''_parsewithspotisaverapi'''
    def _parsewithspotisaverapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, str(search_result['id'])
        headers = {
            "referer": "https://spotisaver.net/en1", "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"', "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"', "sec-fetch-dest": "empty", 
            "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        }
        # parse
        (resp := self.get(f'https://spotisaver.net/api/get_playlist.php?id={song_id}&type=track&lang=en', headers=headers, **request_overrides)).raise_for_status()
        payload = {"track": (download_result := resp2json(resp=resp))["tracks"][0], "download_dir": "downloads", "filename_tag": "SPOTISAVER", "user_ip": "2601:1e23:dac0:b1d7:39a4:640e:4700:01c7", "is_premium": "true"}
        (resp := self.post('https://spotisaver.net/api/download_track.php', json=payload, headers=headers, **request_overrides)).raise_for_status()
        try: duration_in_secs = float(safeextractfromdict(download_result, ['tracks', 0, 'duration_ms'], 0)) / 1000
        except Exception: duration_in_secs = 0
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['tracks', 0, 'name'], None)), singers=legalizestring(', '.join(safeextractfromdict(download_result, ['tracks', 0, 'artists'], []) or [])), album=legalizestring(safeextractfromdict(download_result, ['tracks', 0, 'album'], None)), ext=naiveguessextfromaudiobytes(resp.content), 
            file_size_bytes=resp.content.__sizeof__(), file_size=byte2mb(resp.content.__sizeof__()), identifier=song_id, duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['tracks', 0, 'image', 'url'], None), download_url=None, downloaded_contents=resp.content, download_url_status={'ok': True},
        )
        if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
        # return
        return song_info
    '''_parsewithspotubedlapi'''
    def _parsewithspotubedlapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, str(search_result['id'])
        headers = {
            "referer": "https://spotubedl.com/", "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"', "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"', "sec-fetch-dest": "empty", 
            "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        }
        # parse
        (resp := self.get(f'https://spotubedl.com/api/metadata/{song_id}', headers=headers, **request_overrides)).raise_for_status()
        vid = parse_qs(urlparse(str((download_result := resp2json(resp=resp))['youtube_url'])).query, keep_blank_values=True).get('v')[0]
        (resp := self.get(f'https://spotubedl.com/api/download/{vid}?engine=v1&format=mp3&quality=320', headers=headers, **request_overrides)).raise_for_status()
        download_url = resp2json(resp=resp)['url']; download_result['youtube_resp'] = resp2json(resp=resp)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(', '.join(download_result.get('artists', []) or [])), 
            album=legalizestring(download_result.get('album_name', None)), ext='mp3', file_size_bytes=None, file_size=None, identifier=song_id, duration_s=download_result.get('duration'), duration=seconds2hms(download_result.get('duration')), 
            lyric=None, cover_url=download_result.get('cover_url'), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides), default_download_headers=headers,
        )
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
        elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
        # return
        return song_info
    '''_parsewithspotidownloaderapi'''
    def _parsewithspotidownloaderapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, str(search_result['id'])
        # fetch token
        (resp := self.get('https://spdl.afkarxyz.fun/token', headers={"User-Agent": "CharlesPikachu-musicdl"}, **request_overrides)).raise_for_status()
        session_token = (download_result := resp2json(resp=resp))['token']
        headers = {"Authorization": f"Bearer {session_token}", "Content-Type": "application/json", "Origin": "https://spotidownloader.com", "Referer": "https://spotidownloader.com/"}
        # parse
        (resp := self.post(f'https://api.spotidownloader.com/download', headers=headers, json={"id": song_id}, **request_overrides)).raise_for_status()
        download_result.update(resp2json(resp=resp))
        download_urls: list[str] = [u for u in [download_result.get('linkFlac'), download_result.get('link')] if u and str(u).startswith('http')]
        try: duration_in_secs = float(safeextractfromdict(search_result, ['item', 'data', 'duration', 'totalMilliseconds'], 0) or safeextractfromdict(search_result, ['itemV2', 'data', 'trackDuration', 'totalMilliseconds'], 0)) / 1000
        except Exception: duration_in_secs = 0
        for download_url in download_urls:
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['metadata', 'title'], None)), singers=legalizestring(safeextractfromdict(download_result, ['metadata', 'artists'], None)), album=legalizestring(safeextractfromdict(download_result, ['metadata', 'album'], None)), 
                ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=None, file_size=None, identifier=song_id, duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['metadata', 'cover'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides), 
            )
            if song_info.ext in {'m4s', 'mp4'}: song_info.ext = 'm4a'
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
            elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsewithspotmateapi'''
    def _parsewithspotmateapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, session = request_overrides or {}, str(search_result['id']), copy.deepcopy(self.session)
        session.headers = {'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36'}
        (resp := session.get('https://spotmate.online/en', **request_overrides)).raise_for_status()
        cookies = "; ".join([f"{cookie.name}={cookie.value}" for cookie in session.cookies])
        soup = BeautifulSoup(resp.text, 'lxml'); meta_tag = soup.find('meta', attrs={'name': 'csrf-token'}); csrf_token = meta_tag.get('content')
        headers = {
            'authority': 'spotmate.online', 'accept': '*/*', 'accept-language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7', 'origin': 'https://spotmate.online', 'referer': 'https://spotmate.online/en', 'x-csrf-token': csrf_token, 
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"', 'sec-fetch-dest': 'empty', 'sec-fetch-site': 'same-origin', 'content-type': 'application/json', 
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36', 'cookie': cookies, 'sec-fetch-mode': 'cors', 
        }
        # parse
        (resp := session.post('https://spotmate.online/getTrackData', json={'spotify_url': f'https://open.spotify.com/track/{song_id}'}, headers=headers, **request_overrides)).raise_for_status()
        download_result = resp2json(resp=resp)
        (resp := session.post('https://spotmate.online/convert', json={'urls': f'https://open.spotify.com/track/{song_id}'}, headers=headers, **request_overrides)).raise_for_status()
        download_result['convert'] = resp2json(resp=resp); download_url = download_result['convert']['url']
        try: duration_in_secs = float(safeextractfromdict(download_result, ['duration_ms'], 0)) / 1000
        except Exception: duration_in_secs = 0
        try: ext = parse_qs(urlparse(download_url).query, keep_blank_values=True).get('format')[0]
        except Exception: ext = 'mp3'
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('name', '')), singers=legalizestring(', '.join([singer.get('name') for singer in (download_result.get('artists', []) or []) if isinstance(singer, dict) and singer.get('name')])), 
            album=legalizestring(safeextractfromdict(search_result, ['itemV2', 'data', 'albumOfTrack', 'name'], None) or safeextractfromdict(search_result, ['item', 'data', 'albumOfTrack', 'name'], None)), ext=ext, file_size=None, identifier=song_id, duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric='NULL', 
            cover_url=safeextractfromdict(download_result, ['album', 'images', 0, 'url'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides), default_download_headers=headers,
        )
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
        elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        for imp_func in [self._parsewithspotisaverapi, self._parsewithspotidownloaderapi, self._parsewithspotmateapi, self._parsewithspotubedlapi]:
            try: song_info_flac = imp_func(search_result, request_overrides); assert song_info_flac.with_valid_download_url; break
            except: song_info_flac = SongInfo(source=self.source)
        return song_info_flac
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            pass  # TODO: Solve DRM Issues in Spotify
        if not song_info.with_valid_download_url: song_info = song_info_flac
        if not song_info.with_valid_download_url: return song_info
        # supplement lyric results
        lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration = seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, search_api, search_api_inputs = request_overrides or {}, search_url['api'], search_url['inputs']
        # successful
        try:
            # --search results
            for search_result in safeextractfromdict((search_resp := search_api(**search_api_inputs)), ['data', 'searchV2', 'tracksV2', 'items'], []) or safeextractfromdict(search_resp, ['data', 'searchV2', 'tracks', 'items'], []):
                search_result['id'] = safeextractfromdict(search_result, ['item', 'data', 'id'], None)
                if not search_result['id']: search_result['id'] = str(safeextractfromdict(search_result, ['item', 'data', 'uri'], '')).removeprefix('spotify:track:')
                # --parse with third part apis
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
                # --parse with official apis
                lossless_quality_is_sufficient = False if self.default_cookies or request_overrides.get('cookies') else True
                try: song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                except Exception: song_info = SongInfo(source=self.source)
                # --append to song_infos
                if not song_info.with_valid_download_url: song_info = song_info_flac
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
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, SPOTIFY_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        playlist_result_first, tracks_in_playlist = SpotifyMusicClientPlaylistUtils.parse(copy.deepcopy(self.session), playlist_id=playlist_id, request_overrides=request_overrides)
        tracks_in_playlist = list({d["id"]: d for d in tracks_in_playlist}.values())
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed (0/{len(tracks_in_playlist)})", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1)
                main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed ({idx}/{len(tracks_in_playlist)})")
                song_info_flac = self._parsewiththirdpartapis(search_result=track_info, request_overrides=request_overrides)
                lossless_quality_is_sufficient = False if self.default_cookies or request_overrides.get('cookies') else True
                try: song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                except Exception: song_info = song_info_flac
                if not song_info.with_valid_download_url: song_info = song_info_flac
                if song_info.with_valid_download_url: song_infos.append(song_info)
            main_process_context.advance(main_progress_id, 1)
            main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed ({idx+1}/{len(tracks_in_playlist)})")
        # post processing
        playlist_name = safeextractfromdict(playlist_result_first, ['data', 'playlistV2', 'name'], None)
        song_infos = self._removeduplicates(song_infos=song_infos); work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        # return results
        return song_infos