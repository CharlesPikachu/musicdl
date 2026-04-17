'''
Function:
    Implementation of SodaMusicClient: https://www.douyin.com/qishui/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
import copy
import json_repair
from pathlib import Path
from contextlib import suppress
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from ..utils.hosts import SODA_MUSIC_HOSTS
from urllib.parse import urlencode, urlparse, parse_qs
from ..utils.sodautils import AudioDecryptor, SodaTimedLyricsParser
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, usedownloadheaderscookies, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, SongInfoUtils, IOUtils


'''SodaMusicClient'''
class SodaMusicClient(BaseMusicClient):
    source = 'SodaMusicClient'
    def __init__(self, **kwargs):
        super(SodaMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
        self.default_parse_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0, auto_supplement_song: bool = True):
        if not song_info.raw_data.get('play_auth'): return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id, auto_supplement_song=auto_supplement_song)
        song_info = super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=[], progress=progress, song_progress_id=song_progress_id, auto_supplement_song=False)[0]
        output_filepath, file_data = (output_filepath := Path(song_info.save_path)).parent / f'{output_filepath.stem}.{song_info.ext}', bytearray(Path(song_info.save_path).read_bytes())
        AudioDecryptor.decrypt(file_data=file_data, play_auth=song_info.raw_data['play_auth'], output_filepath=str(output_filepath))
        if not os.path.samefile(song_info.save_path, str(output_filepath)): os.remove(song_info.save_path); song_info._save_path = str(output_filepath)
        downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(song_info, logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else song_info)
        return downloaded_song_infos
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, self.search_size_per_page = rule or {}, request_overrides or {}, min(self.search_size_per_page, 20)
        (default_rule := {'aid': '386088', 'app_name': 'luna_pc', 'region': 'cn', 'geo_region': 'cn', 'os_region': 'cn', 'sim_region': '', 'device_id': '1088932190113307', 'cdid': '', 'iid': '2332504177791808', 'version_name': '3.0.0', 'version_code': '30000000', 'channel': 'official', 'build_mode': 'master', 'network_carrier': '', 'ac': 'wifi', 'tz_name': 'Asia/Shanghai', 'resolution': '', 'device_platform': 'windows', 'device_type': 'Windows', 'os_version': 'Windows 11 Home China', 'fp': '1088932190113307', 'q': keyword, 'cursor': 0, 'search_id': '4ee2bc52-db9b-42c3-85cf-cdac2fe02efe', 'search_method': 'input', 'debug_params': '', 'from_search_id': 'aa21093-d49e-4d29-b6c7-548b170d12a0', 'search_scene': ''}).update(rule)
        # construct search urls
        base_url, search_urls, page_size, count = 'https://api.qishui.com/luna/pc/search/track?', [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['cursor'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := safeextractfromdict(search_result, ['entity', 'track', 'id'], None))): return song_info
        rank_audio_func = lambda video_list: sorted([v for v in video_list if isinstance(v, dict)], key=lambda x: (x.get('Size'), x.get('Bitrate')), reverse=True)
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            (resp := self.get(f'https://api.qishui.com/luna/pc/track_v2?track_id={song_id}&media_type=track&queue_type=', **request_overrides)).raise_for_status()
            (resp := self.get((download_result := resp2json(resp))['track_player']['url_player_info'], **request_overrides)).raise_for_status(); download_result['url_player_info_response'] = resp2json(resp)
            audios_sorted: list[dict] = rank_audio_func(safeextractfromdict(download_result, ['url_player_info_response', 'Result', 'Data', 'PlayInfoList'], []) or [])
            for audio_sorted in [a for a in audios_sorted if (a.get('MainPlayUrl') or a.get('BackupPlayUrl'))]:
                download_url, play_auth = audio_sorted.get('MainPlayUrl') or audio_sorted.get('BackupPlayUrl'), safeextractfromdict(audio_sorted, ['PlayAuth'], '')
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'play_auth': play_auth}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['entity', 'track', 'name'], None)), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['entity', 'track', 'artists'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['entity', 'track', 'album', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                    identifier=song_id, duration_s=int(float(audio_sorted.get('Duration', 0) or 0)), duration=SongInfoUtils.seconds2hms(int(float(audio_sorted.get('Duration', 0) or 0))), lyric=cleanlrc(SodaTimedLyricsParser.tolrclinelevel(SodaTimedLyricsParser.parsetimedlyrics(safeextractfromdict(download_result, ['lyric', 'content'], '') or ''))), cover_url=str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'urls', 0], '')) + str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'uri'], '')) + '~c5_375x375.jpg', download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        with suppress(Exception): lyric_result = {}; (resp := self.get(f'https://music.douyin.com/qishui/share/track?track_id={song_id}', **request_overrides)).raise_for_status(); lyric_result = json_repair.loads(re.search(r'_ROUTER_DATA\s*=\s*({[\s\S]*?});', resp.text).group(1).strip())
        sentences, lrc_list = safeextractfromdict(lyric_result, ['loaderData', 'track_page', 'audioWithLyricsOption', 'lyrics', 'sentences'], []) or [], []
        to_lrc_func = lambda sentence: f"[{(s:=sentence.get('startMs', 0))//60000:02d}:{(s%60000)//1000:02d}.{s%1000:03d}]{''.join(w.get('text', '') for w in sentence.get('words', []) if isinstance(w, dict))}"
        lrc_list.extend(to_lrc_func(sentence) for sentence in sentences if isinstance(sentence, dict)); lyric = cleanlrc("\n".join(lrc_list))
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_parsewithofficialapiv2'''
    def _parsewithofficialapiv2(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := safeextractfromdict(search_result, ['entity', 'track', 'id'], None))): return song_info
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            (resp := self.get(f"https://music.douyin.com/qishui/share/track?track_id={song_id}", headers=headers, **request_overrides)).raise_for_status()
            download_result = json_repair.loads(re.search(r'_ROUTER_DATA\s*=\s*({.*?});', resp.text, re.S).group(1))
            audio_option = safeextractfromdict(download_result, ['loaderData', 'track_page', 'audioWithLyricsOption'], {}) or {}
            download_url = (audio_option.get('url') or '').replace("\\u002F", "/").replace("%7C", "|").replace("%3D", "=")
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['entity', 'track', 'name'], None)), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['entity', 'track', 'artists'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['entity', 'track', 'album', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(audio_option.get('duration', 0) or 0)), duration=SongInfoUtils.seconds2hms(int(float(audio_option.get('duration', 0) or 0))), lyric=None, cover_url=str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'urls', 0], '')) + str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'uri'], '')) + '~c5_375x375.jpg', download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        with suppress(Exception): lyric_result = {}; (resp := self.get(f'https://music.douyin.com/qishui/share/track?track_id={song_id}', **request_overrides)).raise_for_status(); lyric_result = json_repair.loads(re.search(r'_ROUTER_DATA\s*=\s*({[\s\S]*?});', resp.text).group(1).strip())
        sentences, lrc_list = safeextractfromdict(lyric_result, ['loaderData', 'track_page', 'audioWithLyricsOption', 'lyrics', 'sentences'], []) or [], []
        to_lrc_func = lambda sentence: f"[{(s:=sentence.get('startMs', 0))//60000:02d}:{(s%60000)//1000:02d}.{s%1000:03d}]{''.join(w.get('text', '') for w in sentence.get('words', []) if isinstance(w, dict))}"
        lrc_list.extend(to_lrc_func(sentence) for sentence in sentences if isinstance(sentence, dict)); lyric = cleanlrc("\n".join(lrc_list))
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
            for search_result in resp2json(resp)['result_groups'][0]['data']:
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                with suppress(Exception): song_info = song_info if song_info.with_valid_download_url else self._parsewithofficialapiv2(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
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
        playlist_url, playlist_id = self.session.head(playlist_url, allow_redirects=True, **dict(request_overrides := request_overrides or {})).url, None
        with suppress(Exception): playlist_id, song_infos = parse_qs(urlparse(playlist_url).query, keep_blank_values=False).get('playlist_id')[0], []
        if not playlist_id: playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, SODA_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, page_size, playlist_result_first = [], 1, 20, {}
        while True:
            params = {'playlist_id': playlist_id, 'cursor': str(page_size * (page - 1)), 'cnt': str(page_size), 'aid': '386088', 'device_platform': 'web', 'channel': 'pc_web'}
            with suppress(Exception): (resp := self.get(f"https://api.qishui.com/luna/pc/playlist/detail?", params=params, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['media_resources'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['media_resources'], [])); page += 1; del resp
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['playlist', 'count_tracks'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["id"]: d for d in tracks_in_playlist}.values())
        for track in tracks_in_playlist: track['entity'].__setitem__('track', safeextractfromdict(track, ['entity', 'track_wrapper', 'track'], {})) if isinstance(track, dict) and isinstance(track.get('entity'), dict) else None
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
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['playlist', 'title'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos