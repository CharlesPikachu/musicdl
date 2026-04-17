'''
Function:
    Implementation of KuwoMusicClient: http://www.kuwo.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import time
import random
import base64
import warnings
from contextlib import suppress
from typing import TYPE_CHECKING
from .base import BaseMusicClient
from rich.progress import Progress
from pathvalidate import sanitize_filepath
from ..utils.hosts import KUWO_MUSIC_HOSTS
from ..utils.kuwoutils import KuwoMusicClientUtils
from urllib.parse import urlencode, urlparse, parse_qs
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import optionalimport, legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils
warnings.filterwarnings('ignore')


'''KuwoMusicClient'''
class KuwoMusicClient(BaseMusicClient):
    source = 'KuwoMusicClient'
    MUSIC_QUALITIES = [(22000, 'flac'), (320, 'mp3')] # playable flac and mp3 formats
    ENC_MUSIC_QUALITIES = [(4000, '4000kflac'), (2000, '2000kflac'), (320, '320kmp3'), (192, '192kmp3'), (128, '128kmp3')] # encrypted mgg format
    def __init__(self, **kwargs):
        super(KuwoMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_download_headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_parse_headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"vipver": "1", "client": "kt", "ft": "music", "cluster": "0", "strategy": "2012", "encoding": "utf8", "rformat": "json", "mobi": "1", "issubtitle": "1", "show_copyright_off": "1", "pn": "0", "rn": "10", "all": keyword}).update(rule)
        # construct search urls
        base_url, search_urls, page_size, count = 'http://www.kuwo.cn/search/searchMusicBykeyWord?', [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['rn'] = page_size
            page_rule['pn'] = str(int(count // page_size))
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithcggapi'''
    def _parsewithcggapi(self, search_result: dict, request_overrides: dict = None):
        # init
        curl_cffi, request_overrides, song_id = optionalimport('curl_cffi'), request_overrides or {}, str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_')
        MUSIC_QUALITIES = ["acc", "wma", "ogg", "standard", "exhigh", "ape", "lossless", "hires", "zp", "hifi", "sur", "jymaster"][::-1][3:]
        if TYPE_CHECKING and curl_cffi is not None: import curl_cffi as curl_cffi
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): (resp := curl_cffi.requests.get(f"https://kw-api.cenguigui.cn/?id={song_id}&type=song&level={music_quality}&format=json", timeout=10, impersonate="chrome131", verify=False, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): (resp := self.get(f"https://kw-api.cenguigui.cn/?id={song_id}&type=song&level={music_quality}&format=json", timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): continue
            duration_in_secs = int(float(safeextractfromdict(download_result, ['data', 'duration'], 0) or 0))
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], '')), cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithyyy001api'''
    def _parsewithyyy001api(self, search_result: dict, request_overrides: dict = None):
        # init
        REQUEST_KEYS = ['YzJmNjBlZDYtOTlmZC0xNjJlLWM0NzAtYjIxNDkwOGViNWI0YjYzYzFhN2E=', 'NTVjNTY3YzItNTJlNS1kMzdiLTE1N2MtMDE0MDIxNzEwYzc1NzY2OWNkYjc=', 'OTY4M2MwNzQtY2E3ZS01ZGYwLTUyZGEtMWEzNGZiNjVhOTZhZGU2NTczYjU=', 'OTdkZjQ0OTUtYzRjOS01MmFhLTNlODAtZjliZGFiODU1Y2UxZWIwN2JlZDk=']
        MUSIC_QUALITIES, decrypt_func = ["ff", "p", "h"], lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        request_overrides, song_id = request_overrides or {}, str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_')
        # parse
        for music_quality in MUSIC_QUALITIES:
            resp = next((resp for _ in range(5) if (resp := self.get(f"https://api.yyy001.com/api/kwmusic/?apikey={decrypt_func(random.choice(REQUEST_KEYS))}&action=music_url&music_id={song_id}&quality={music_quality}", timeout=10, **request_overrides)).json()['code'] in {'200', 200} or (time.sleep(1) or False)), None)
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): continue
            duration_in_secs = float(int(search_result.get('DURATION') or search_result.get('duration') or 0))
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('SONGNAME') or search_result.get('name')), singers=legalizestring(search_result.get('ARTIST') or search_result.get('artist')), album=legalizestring(search_result.get('ALBUM') or search_result.get('album')), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('hts_MVPIC') or search_result.get('albumpic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithnxinxzapi'''
    def _parsewithnxinxzapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, MUSIC_QUALITIES = request_overrides or {}, str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_'), ['lossless', 'exhigh', 'standard']
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): (resp := self.get(f"http://music.nxinxz.com/kw.php?id={song_id}&level={music_quality}&type=json", **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): continue
            duration_in_secs = float(int(search_result.get('DURATION') or search_result.get('duration') or 0))
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('SONGNAME') or search_result.get('name')), singers=legalizestring(search_result.get('ARTIST') or search_result.get('artist')), album=legalizestring(search_result.get('ALBUM') or search_result.get('album')), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('hts_MVPIC') or search_result.get('albumpic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithhaitangwapi'''
    def _parsewithhaitangwapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, MUSIC_QUALITIES = request_overrides or {}, str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_'), ['lossless', 'exhigh', 'standard']
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): (resp := self.get(f"https://musicapi.haitangw.net/music/kw.php?id={song_id}&level={music_quality}&type=json", **request_overrides)).raise_for_status()
            if not (download_url := safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], '')) or not str(download_url).startswith('http'): continue
            duration_in_secs = float(int(search_result.get('DURATION') or search_result.get('duration') or 0))
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('SONGNAME') or search_result.get('name')), singers=legalizestring(search_result.get('ARTIST') or search_result.get('artist')), album=legalizestring(search_result.get('ALBUM') or search_result.get('album')), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('hts_MVPIC') or search_result.get('albumpic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for parser_func in [self._parsewithcggapi, self._parsewithnxinxzapi, self._parsewithhaitangwapi, self._parsewithyyy001api]:
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac, song_id = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source), str(search_result.get('MUSICRID') or search_result.get('musicrid')).removeprefix('MUSIC_')
        if not isinstance(search_result, dict) or (not (search_result.get('MUSICRID') or search_result.get('musicrid'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            for music_quality in KuwoMusicClient.MUSIC_QUALITIES:
                query = f"user=0&corp=kuwo&source=kwplayer_ar_5.1.0.0_B_jiakong_vh.apk&p2p=1&type=convert_url2&sig=0&format={music_quality[1]}&rid={song_id}"
                with suppress(Exception): (resp := self.get(f"http://mobi.kuwo.cn/mobi.s?f=kuwo&q={KuwoMusicClientUtils.encryptquery(query)}", headers={"user-agent": "okhttp/3.10.0"}, **request_overrides)).raise_for_status()
                if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                if not (download_url := re.search(r'http[^\s$\"]+', (download_result := resp.text))) or not ((download_url := download_url.group(0)).startswith('http')): continue
                duration_in_secs = float(int(search_result.get('DURATION') or search_result.get('duration') or 0))
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True); del resp
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('SONGNAME') or search_result.get('name')), singers=legalizestring(search_result.get('ARTIST') or search_result.get('artist')), album=legalizestring(search_result.get('ALBUM') or search_result.get('album')), ext=download_url_status['ext'], 
                    file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('hts_MVPIC') or search_result.get('albumpic'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        encoded_params = KuwoMusicClientUtils.buildlyricsparams(song_id, True)
        with suppress(Exception): (resp := self.get(f"http://newlyric.kuwo.cn/newlyric.lrc?{encoded_params}", **request_overrides)).raise_for_status(); song_info.lyric = cleanlrc(KuwoMusicClientUtils.convertrawlrc(KuwoMusicClientUtils.decodelyrics(resp.content, True))) or song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, lossless_quality_is_sufficient = request_overrides or {}, False if self.default_cookies or request_overrides.get('cookies') else True
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp)['abslist']:
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with third part apis
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                # --append to song_infos
                if (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url: song_infos.append(song_info)
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
        playlist_url, playlist_id = self.session.head(playlist_url, allow_redirects=True, **(request_overrides := dict(request_overrides or {}))).url, None
        with suppress(Exception): playlist_id, song_infos = parse_qs(urlparse(playlist_url).query, keep_blank_values=False).get('id')[0], []
        if not playlist_id: playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, KUWO_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, playlist_result_first = [], 1, {}
        while True:
            with suppress(Exception): (resp := self.get(f"https://m.kuwo.cn/newh5app/wapi/api/www/playlist/playListInfo?pid={playlist_id}&pn={page}&rn=100", **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['data', 'musicList'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['data', 'musicList'], [])); page += 1; del resp
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['data', 'total'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["musicrid"]: d for d in tracks_in_playlist}.values())
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}})
                song_info_flac = self._parsewiththirdpartapis(search_result=track_info, request_overrides=request_overrides)
                lossless_quality_is_sufficient = False if self.default_cookies or request_overrides.get('cookies') else True
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                if (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse song id {song_info.identifier} >>> {song_info.album} {song_info.song_name} {song_info.singers} {song_info.download_url}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['data', 'name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos