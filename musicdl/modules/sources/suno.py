'''
Function:
    Implementation of SunoMusicClient: https://suno.com/discover
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import time
import json
import copy
import uuid
import math
import base64
from contextlib import suppress
from urllib.parse import urlparse
from typing_extensions import Unpack
from pathvalidate import sanitize_filepath
from ..utils.hosts import SUNO_MUSIC_HOSTS
from .base import BaseMusicClient, BaseMusicClientKwargs
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import resp2json, legalizestring, safeextractfromdict, usesearchheaderscookies, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, IOUtils, SongInfoUtils


'''SunoMusicClient'''
class SunoMusicClient(BaseMusicClient):
    source = 'SunoMusicClient'
    AUTH_TOKEN = None
    browser_token_func = lambda: json.dumps({"token": base64.urlsafe_b64encode(json.dumps({"timestamp": int(time.time() * 1000)}, separators=(",", ":")).encode("utf-8")).decode("utf-8").rstrip("=")}, separators=(",", ":"))
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(SunoMusicClient, self).__init__(**kwargs)
        SunoMusicClient.AUTH_TOKEN = self.default_search_cookies.get('auth_token') or self.default_parse_cookies.get('auth_token') or self.default_download_cookies.get('auth_token')
        self.default_search_headers = {
            "accept": "*/*", "content-type": "application/json", "origin": "https://suno.com", "referer": "https://suno.com/", "browser-token": SunoMusicClient.browser_token_func(),
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36", "device-id": str(uuid.uuid4()),
        }
        if self.default_search_cookies: self.default_search_headers["authorization"] = f"Bearer {SunoMusicClient.AUTH_TOKEN}"
        self.default_parse_headers = {
            "accept": "*/*", "content-type": "application/json", "origin": "https://suno.com", "referer": "https://suno.com/", "browser-token": SunoMusicClient.browser_token_func(),
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36", "device-id": str(uuid.uuid4()),
        }
        if self.default_parse_cookies: self.default_parse_headers["authorization"] = f"Bearer {SunoMusicClient.AUTH_TOKEN}"
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"}
        if self.default_download_cookies: self.default_download_headers["authorization"] = f"Bearer {SunoMusicClient.AUTH_TOKEN}"
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, cursor = rule or {}, request_overrides or {}, None
        # construct search urls
        base_url, search_results = 'https://studio-api-prod.suno.com/api/unified/feed', []
        for page in range(math.ceil(self.search_size_per_source / self.search_size_per_page)):
            (default_rule := {"feed_id": "omnisearch_songs", "cursor": cursor, "page_size": self.search_size_per_page, "request_metadata": {"term": keyword}}).update(rule)
            (resp := self.post(base_url, json=default_rule, **request_overrides)).raise_for_status()
            search_items = safeextractfromdict(resp2json(resp=resp), ['feed', 'items'], []) or []
            cursor = safeextractfromdict(resp2json(resp=resp), ['feed', 'next_cursor'], None)
            search_results.append({'items': [item.get('content_item') for item in search_items if isinstance(item, dict) and item.get("content_type") == "clip"], 'page': page + 1})
        # return
        return search_results
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            media_info = next((media for media in (search_result.get('media_urls') or []) if isinstance(media, dict) and media.get('content_type') == 'm4a-opus' and media.get('url')), None) or next((media for media in (search_result.get('media_urls') or []) if isinstance(media, dict) and media.get('content_type') == 'mp3' and media.get('url')), None)
            download_url = (media_info or {}).get('url') or search_result.get('audio_url') or f'https://cdn1.suno.ai/{song_id}.mp3'
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = float(safeextractfromdict(search_result, ['metadata', 'duration'], 0) or 0)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['persona', 'name'], None) or search_result.get('display_name')), album=legalizestring(search_result.get('model_name')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=safeextractfromdict(search_result, ['metadata', 'prompt'], None), cover_url=search_result.get('image_large_url') or search_result.get('image_url'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            song_info.lyric = cleanlrc(song_info.lyric) if song_info.lyric else song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = None, request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, search_results, page_no, search_result_idx = request_overrides or {}, (search_url or {})['items'], (search_url or {})['page'], -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            for search_result_idx, search_result in enumerate(search_results):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
            # --update progress
            progress.update(task_id, description=f'{self.source}._search >>> {search_result_idx+1} search results processed on page {page_no}')
        # failure
        except Exception as err:
            progress.update(task_id, description=f'{self.source}._search >>> {keyword} on page {page_no} (Error: {err})')
            self.logger_handle.error(f'{self.source}._search >>> {keyword} on page {page_no} (Error: {err})', disable_print=self.disable_print)
        # return
        return song_infos
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        # init
        playlist_url, playlist_id = self.session.head(playlist_url, allow_redirects=True, **dict(request_overrides := request_overrides or {})).url, None
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, SUNO_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, playlist_result_first = [], 1, {}
        while True:
            with suppress(Exception): (resp := self.get(f"https://studio-api-prod.suno.com/api/playlist/{playlist_id}/", params={"page": page}, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['playlist_clips'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['playlist_clips'], [])); page += 1; del resp
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (not playlist_result.get("next_cursor")) or (float(playlist_result.get('num_total_results')) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({clip["id"]: clip for d in tracks_in_playlist if isinstance(d, dict) and (clip := d.get('clip') or {})}.values())
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed (0/{len(tracks_in_playlist)}) SongInfo", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx}/{len(tracks_in_playlist)}) SongInfo")
                song_info = SongInfo(source=self.source, raw_data={'search': track_info, 'download': {}, 'lyric': {}})
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                if song_info.with_valid_download_url: song_infos.append(song_info); continue
                self.logger_handle.warning(f'Fail to parse track info {track_info}', disable_print=self.disable_print)
            main_process_context.advance(main_progress_id, 1); main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} Songs Found in Playlist {playlist_id} >>> Completed ({idx+1}/{len(tracks_in_playlist)}) SongInfo")
        # post processing
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos