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
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from urllib.parse import urlencode, urlparse
from ..utils.hosts import SOUNDCLOUD_MUSIC_HOSTS
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import touchdir, legalizestring, resp2json, usesearchheaderscookies, seconds2hms, safeextractfromdict, hostmatchessuffix, obtainhostname, useparseheaderscookies, SongInfo, AudioLinkTester, LyricSearchClient


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
        self.default_headers = self.default_search_headers
        if self.default_search_cookies: self.default_search_headers.update({'Authorization': self.default_search_cookies["oauth_token"]})
        if self.default_parse_cookies: self.default_parse_headers.update({'Authorization': self.default_parse_cookies["oauth_token"]})
        if self.default_download_cookies: self.default_download_headers.update({'Authorization': self.default_download_cookies["oauth_token"]})
        self._initsession()
    '''_setclientid'''
    def _setclientid(self, request_overrides: dict = None):
        if SoundCloudMusicClient.CLIENT_ID: return
        request_overrides = request_overrides or {}
        try: (resp := self.session.get('https://soundcloud.com/', **request_overrides)).raise_for_status()
        except: SoundCloudMusicClient.CLIENT_ID = '9jZvetLfDs6An08euQgJ0lYlHkKdGFzV'; return
        script_urls = re.findall(r'<script[^>]+src="([^"]+)"', resp.text)
        for url in reversed(script_urls):
            try: resp = self.session.get(url, **request_overrides); m = re.search(r'client_id\s*:\s*"([0-9a-zA-Z]{32})"', resp.text) if resp.status_code == 200 else None
            except Exception: continue
            if m: SoundCloudMusicClient.CLIENT_ID = m.group(1); return SoundCloudMusicClient.CLIENT_ID
        SoundCloudMusicClient.CLIENT_ID = '9jZvetLfDs6An08euQgJ0lYlHkKdGFzV'; return
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        self._setclientid(request_overrides=request_overrides)
        # search rules
        default_rule = {'q': keyword, 'sc_a_id': 'ab15798461680579b387acf67441b40149e528cd', 'facet': 'genre', 'user_id': '704923-225181-486085-807554', 'client_id': SoundCloudMusicClient.CLIENT_ID, 'limit': '20', 'offset': '0', 'linked_partitioning': '1', 'app_version': '1769771069', 'app_locale': 'en'}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://api-v2.soundcloud.com/search/tracks?'
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
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        self._setclientid(request_overrides=request_overrides); song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        guess_codec_func = lambda t: ((lambda preset, mime: "opus" if ("opus" in preset or "opus" in mime) else "aac" if ("aac" in preset or "mp4a" in mime or "audio/mp4" in mime or "m4a" in mime) else "mp3" if ("mp3" in preset or "audio/mpeg" in mime) else "abr" if ("abr" in preset) else "unknown")((safeextractfromdict(t, ["preset"], "") or "").lower(), (safeextractfromdict(t, ["format", "mime_type"], "") or "").lower()))
        guess_bitrate_kbps_func = lambda t: (lambda preset: (lambda m: int(m.group(1)) if m else 128 if preset == "mp3_0_1" else 64 if preset == "opus_0_0" else 128 if preset.startswith("abr") else 0)(re.search(r"(\d+)\s*k", preset)))((safeextractfromdict(t, ["preset"], "") or "").lower())
        quality_rank_func = lambda t: {"hq": 2, "sq": 1}.get((safeextractfromdict(t, ["quality"], "") or "").lower(), 0)
        codec_rank_func = lambda codec: {"opus": 4, "aac": 3, "abr": 2, "mp3": 1, "unknown": 0}.get((codec or "").lower(), 0)
        protocol_rank_func = lambda t: {"progressive": 2, "hls": 1}.get((safeextractfromdict(t, ["format", "protocol"], "") or "").lower(), 0)
        sort_key_func = lambda t: (lambda c, br: (quality_rank_func(t), br, codec_rank_func(c), protocol_rank_func(t)))(guess_codec_func(t), guess_bitrate_kbps_func(t))
        # supplement incomplete tracks
        if not safeextractfromdict(search_result, ['media', 'transcodings'], []): search_result = resp2json(self.get(f"https://api-v2.soundcloud.com/tracks/{song_id}", params={"client_id": SoundCloudMusicClient.CLIENT_ID}, **request_overrides))
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            for transcoding in sorted((safeextractfromdict(search_result, ['media', 'transcodings'], []) or []), key=sort_key_func, reverse=True):
                if not isinstance(transcoding, dict): continue
                preset, mime_type = transcoding.get('preset', '') or '', safeextractfromdict(transcoding, ['format', 'mime_type'], '') or ''
                download_url, protocol = transcoding.get('url', '') or '', safeextractfromdict(transcoding, ['format', 'protocol'], '') or ''
                if str(protocol).startswith(('ctr-', 'cbc-')): continue # TODO: Solve DRM issues in SoundCloud
                ext = (('opus' if ('opus' in preset or 'opus' in mime_type) else None) or ('m4a' if ('aac' in preset or 'm4a' in mime_type) else None) or 'mp3')
                if f"{protocol}_{preset}" in {"original_download"}:
                    try: (resp := self.get(f'https://api-v2.soundcloud.com/tracks/{song_id}/download', params={'client_id': SoundCloudMusicClient.CLIENT_ID}, **request_overrides)).raise_for_status()
                    except Exception: continue
                    download_url = (download_result := resp2json(resp=resp)).get('redirectUri')
                    if not download_url or not str(download_url).startswith('http'): continue
                else:
                    try: (resp := self.get(download_url, params={'client_id': SoundCloudMusicClient.CLIENT_ID}, **request_overrides)).raise_for_status()
                    except Exception: continue
                    download_url = (download_result := resp2json(resp=resp)).get('url')
                    if not download_url or not str(download_url).startswith('http'): continue
                if str(protocol).lower() in {'hls'}:
                    try: (resp := self.get(download_url, allow_redirects=True, **request_overrides)).raise_for_status()
                    except Exception: continue
                    download_url_status = {'ok': True}
                else:
                    download_url_status = self.audio_link_tester.test(download_url, request_overrides)
                try: duration_in_secs = int(float(safeextractfromdict(search_result, ['duration'], 0)) / 1000)
                except Exception: duration_in_secs = 0
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['publisher_metadata', 'artist'], None) or safeextractfromdict(search_result, ['user', 'username'], None)), album=legalizestring(safeextractfromdict(search_result, ['publisher_metadata', 'album_title'], None)), 
                    ext=ext, file_size_bytes=None, file_size=None, identifier=song_id, duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric='NULL', cover_url=search_result.get('artwork_url'), download_url=download_url, download_url_status=download_url_status
                )
                if str(protocol).lower() in {'hls'}: song_info.protocol, song_info.file_size = 'HLS', 'HLS'
                else:
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']; song_info.ext = song_info.download_url_status['probe_status']['ext']
                    if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                    elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
                if song_info.with_valid_download_url: break
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
        request_overrides = request_overrides or {}; self._setclientid()
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **request_overrides).url
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, SOUNDCLOUD_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        (resp := self.get("https://api-v2.soundcloud.com/resolve", params={"url": playlist_url, "client_id": SoundCloudMusicClient.CLIENT_ID}, **request_overrides)).raise_for_status()
        tracks_in_playlist = (playlist_result := resp2json(resp=resp))['tracks']; playlist_id = playlist_result['id']
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
        playlist_name = safeextractfromdict(playlist_result, ['title'], None)
        song_infos = self._removeduplicates(song_infos=song_infos); work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        # return results
        return song_infos