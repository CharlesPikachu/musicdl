'''
Function:
    Implementation of JooxMusicClient: https://www.joox.com/intl
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import base64
import json_repair
from bs4 import BeautifulSoup
from contextlib import suppress
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from ..utils.hosts import JOOX_MUSIC_HOSTS
from urllib.parse import urlencode, urlparse, parse_qs
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, extractdurationsecondsfromlrc, cookies2string, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, LyricSearchClient, IOUtils, SongInfoUtils


'''JooxMusicClient'''
class JooxMusicClient(BaseMusicClient):
    source = 'JooxMusicClient'
    FUZZY_MUSIC_QUALITIES = [
        "master_tapeUrl", "master_tapeURL", "master_tape_url", "masterTapeUrl", "masterTapeURL", "rMasterTapeUrl", "rMasterTapeURL", "hiresUrl", "hiresURL", "hires_url", "hiResUrl", "hiResURL", "rHiresUrl", "rHiResUrl", "flacUrl", "flacURL", "flac_url", "rFlacUrl", "rflacUrl", "rFLACUrl", "apeUrl", "apeURL", "ape_url", "rApeUrl", "rapeUrl", "stereo_atmosUrl", "stereo_atmosURL", "stereo_atmos_url", "stereoAtmosUrl", "stereoAtmosURL", "atmosUrl", "atmosURL", "atmos_url", "rStereoAtmosUrl", "rAtmosUrl", "dolby448Url", "dolby448URL", "dolby448_url", "rDolby448Url", "rDolby448URL", "dolby256Url", "dolby256URL", "dolby256_url", "rDolby256Url", "rDolby256URL", "r320Url", "r320url", "r320_url", "320Url", "320URL", "320_url", "url320", "mp3320Url", "mp3_320_url", "highUrl", "high_url", "r320oggUrl", "r320OggUrl", "r320OggURL", "r320_ogg_url", "320oggUrl", "320OggUrl", "ogg320Url", "ogg_320_url", "r192oggUrl", 
        "r192OggUrl", "r192OggURL", "r192_ogg_url", "192oggUrl", "192OggUrl", "ogg192Url", "ogg_192_url", "r192k_mnacUrl", "r192k_mnacURL", "r192k_mnac_url", "r192kMnacUrl", "r192kMnacURL", "192k_mnacUrl", "192kMnacUrl", "mnac192Url", "mnac_192_url", "r192mnacUrl", "r192Url", "r192url", "r192_url", "192Url", "192URL", "192_url", "url192", "m4a192Url", "aac192Url", "aac_192_url", "mp3Url", "r128Url", "r128url", "r128_url", "128Url", "128URL", "128_url", "url128", "m4a128Url", "aac128Url", "mp3128Url", "m4aUrl", "r96Url", "r96url", "r96_url", "96Url", "96URL", "96_url", "url96", "r48Url", "r48url", "r48_url", "48Url", "48URL", "48_url", "url48", "r24Url", "r24url", "r24_url", "24Url", "24URL", "24_url", "url24", "lowUrl", "low_url", "previewUrl", "preview_url", "refrainUrl", "refrainURL", "refrain_url", "chorusUrl", "chorus_url", "clipUrl", "clip_url", "snippetUrl", "snippet_url", "trialUrl", "trial_url",
    ]
    MUSIC_QUALITIES = [('r320Url', '320'), ('r192Url', '192'), ('mp3Url', '128'), ('m4aUrl', '96')]
    def __init__(self, **kwargs):
        super(JooxMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "cookie": "wmid=142420656; user_type=1; country=id; session_key=2a5d97d05dc8fe238150184eaf3519ad;", "x-forwarded-for": "36.73.34.109"}
        self.default_parse_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "cookie": "wmid=142420656; user_type=1; country=id; session_key=2a5d97d05dc8fe238150184eaf3519ad;", "x-forwarded-for": "36.73.34.109"}
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        if self.default_search_cookies: self.default_search_headers['cookie'] = cookies2string(self.default_search_cookies)
        if self.default_parse_cookies: self.default_parse_headers['cookie'] = cookies2string(self.default_parse_cookies)
        if self.default_download_cookies: self.default_download_headers['cookie'] = cookies2string(self.default_download_cookies)
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {'country': 'hk', 'lang': 'zh_TW', 'key': keyword, 'type': '0'}).update(rule)
        # construct search urls
        base_url = 'https://cache.api.joox.com/openjoox/v2/search_type?'
        search_urls = [base_url + urlencode(copy.deepcopy(default_rule))]
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, lang: str = 'zh_TW', country: str = 'hk', song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            (resp := self.get('https://api.joox.com/web-fcgi-bin/web_get_songinfo', params={'songid': song_id, 'lang': lang, 'country': country}, **request_overrides)).raise_for_status()
            for candidate_result in [{'quality': fmq, 'url': download_result.get(fmq)} for fmq in JooxMusicClient.FUZZY_MUSIC_QUALITIES if (download_result := json_repair.loads(resp.text.removeprefix('MusicInfoCallback(')[:-1])).get(fmq)]:
                if not (download_url := candidate_result.get('url')) or not (str(download_url).startswith('http')): continue
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('artist_list', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(search_result.get('album_name')), ext=download_url_status['ext'], 
                    file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(download_result.get('minterval') or 0)), duration=SongInfoUtils.seconds2hms(download_result.get('minterval')), lyric=None, cover_url=download_result.get('imgSrc'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        params, resp = {'musicid': song_id, 'country': country, 'lang': lang}, None
        with suppress(Exception): (resp := self.get('https://api.joox.com/web-fcgi-bin/web_lyric', params=params, **request_overrides)).raise_for_status()
        if resp is None: lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        else: lyric_result: dict = json_repair.loads(resp.text.replace('MusicJsonCallback(', '')[:-1]) or {}; lyric = cleanlrc(base64.b64decode(lyric_result.get('lyric') or '').decode('utf-8')) or 'NULL'
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, parsed_search_url = request_overrides or {}, parse_qs(urlparse(search_url).query, keep_blank_values=True)
        lang, country = parsed_search_url['lang'][0], parsed_search_url['country'][0]
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp=resp)['tracks']:
                # --init song info
                search_result = search_result[0] if isinstance(search_result, list) else search_result
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, lang=lang, country=country, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
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
        playlist_url, lang, country = self.session.head(playlist_url, allow_redirects=True, **(request_overrides := dict(request_overrides or {}))).url, 'zh_TW', 'hk'
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, JOOX_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        (resp := self.get(playlist_url, **request_overrides)).raise_for_status()
        if not (script_tag := (BeautifulSoup(resp.text, 'lxml')).find('script', id='__NEXT_DATA__')): return song_infos
        tracks_in_playlist = (playlist_result := json_repair.loads(script_tag.string))['props']['pageProps']['allPlaylistTracks']['tracks']['items']
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}})
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=track_info, lang=lang, country=country, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                if song_info.with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse song id {song_info.identifier} >>> {song_info.album} {song_info.song_name} {song_info.singers} {song_info.download_url}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result['props']['pageProps']['allPlaylistTracks'], ['name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos