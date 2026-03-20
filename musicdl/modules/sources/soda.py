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
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from ..utils.hosts import SODA_MUSIC_HOSTS
from urllib.parse import urlencode, urlparse, parse_qs
from ..utils.sodautils import AudioDecryptor, SodaTimedLyricsParser
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import touchdir, legalizestring, byte2mb, resp2json, usesearchheaderscookies, safeextractfromdict, seconds2hms, usedownloadheaderscookies, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, SongInfoUtils


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
        super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=[], progress=progress, song_progress_id=song_progress_id, auto_supplement_song=False)
        with open(song_info.save_path, "rb") as fp: file_data = bytearray(fp.read())
        output_filepath = (output_filepath := Path(song_info.save_path)).parent / f'{output_filepath.stem}.m4a'
        AudioDecryptor.decrypt(file_data=file_data, play_auth=song_info.raw_data['play_auth'], output_filepath=str(output_filepath))
        if not os.path.samefile(song_info.save_path, str(output_filepath)): os.remove(song_info.save_path)
        song_info._save_path = str(output_filepath); downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(copy.deepcopy(song_info), logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else copy.deepcopy(song_info))
        return downloaded_song_infos
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        self.search_size_per_page = min(self.search_size_per_page, 20)
        # search rules
        default_rule = {
            'aid': '386088', 'app_name': 'luna_pc', 'region': 'cn', 'geo_region': 'cn', 'os_region': 'cn', 'sim_region': '', 'device_id': '1088932190113307', 'cdid': '', 'iid': '2332504177791808', 'version_name': '3.0.0', 'version_code': '30000000', 'channel': 'official', 'build_mode': 'master', 'network_carrier': '', 'ac': 'wifi', 'tz_name': 'Asia/Shanghai', 
            'resolution': '', 'device_platform': 'windows', 'device_type': 'Windows', 'os_version': 'Windows 11 Home China', 'fp': '1088932190113307', 'q': keyword, 'cursor': 0, 'search_id': '4ee2bc52-db9b-42c3-85cf-cdac2fe02efe', 'search_method': 'input', 'debug_params': '', 'from_search_id': 'aa21093-d49e-4d29-b6c7-548b170d12a0', 'search_scene': '',
        }
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://api.qishui.com/luna/pc/search/track?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['cursor'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := safeextractfromdict(search_result, ['entity', 'track', 'id'], None))): return song_info
        rank_audio_func = lambda video_list: sorted(video_list, key=lambda x: (x.get('Size'), x.get('Bitrate')), reverse=True)
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            (resp := self.get(f'https://api.qishui.com/luna/pc/track_v2?track_id={song_id}&media_type=track&queue_type=', **request_overrides)).raise_for_status()
            (resp := self.get((download_result := resp2json(resp))['track_player']['url_player_info'], **request_overrides)).raise_for_status()
            download_result['url_player_info_response'] = resp2json(resp)
            audios_sorted: list[dict] = rank_audio_func(safeextractfromdict(download_result, ['url_player_info_response', 'Result', 'Data', 'PlayInfoList'], []) or [])
            audios_sorted: list[dict] = [a for a in audios_sorted if (a.get('MainPlayUrl') or a.get('BackupPlayUrl'))]
            for audio_sorted in audios_sorted:
                download_url = audio_sorted.get('MainPlayUrl') or audio_sorted.get('BackupPlayUrl'); play_auth = safeextractfromdict(audio_sorted, ['PlayAuth'], '')
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'play_auth': play_auth}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['entity', 'track', 'name'], None)), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['entity', 'track', 'artists'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['entity', 'track', 'album', 'name'], None)), ext=audio_sorted.get('Format', 'm4a'), file_size_bytes=audio_sorted.get('Size', 0), file_size=byte2mb(audio_sorted.get('Size', 0)), 
                    identifier=str(song_id), duration_s=audio_sorted.get('Duration'), duration=seconds2hms(audio_sorted.get('Duration')), lyric=cleanlrc(SodaTimedLyricsParser.tolrclinelevel(SodaTimedLyricsParser.parsetimedlyrics(safeextractfromdict(download_result, ['lyric', 'content'], '')))) or 'NULL', cover_url=str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'urls', 0], '')) + str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'uri'], '')) + '~c5_375x375.jpg', download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                )
                song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                song_info.file_size = song_info.download_url_status['probe_status']['file_size']; song_info.ext = song_info.download_url_status['probe_status']['ext']
                if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
                if song_info.with_valid_download_url: break
        if not song_info.with_valid_download_url: return song_info
        # supplement lyric results
        try:
            (resp := self.get(f'https://music.douyin.com/qishui/share/track?track_id={song_id}', **request_overrides)).raise_for_status()
            lyric_result = json_repair.loads(re.search(r'_ROUTER_DATA\s*=\s*({[\s\S]*?});', resp.text).group(1).strip())
            sentences, lrc_list = lyric_result['loaderData']['track_page']['audioWithLyricsOption']['lyrics']['sentences'], []
            for sentence in sentences:
                if not isinstance(sentence, dict): continue
                start_ms = sentence.get('startMs', 0); sentence_text = "".join([w.get('text', '') for w in sentence.get('words', []) if isinstance(w, dict)])
                minutes, seconds, m_seconds = start_ms // 60000, (start_ms % 60000) // 1000, start_ms % 1000; time_tag = f"[{minutes:02d}:{seconds:02d}.{m_seconds:03d}]"
                lrc_list.append(f"{time_tag}{sentence_text}")
            lyric = cleanlrc("\n".join(lrc_list)) or 'NULL'
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
            for search_result in resp2json(resp)['result_groups'][0]['data']:
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
        return song_infos
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        # init
        request_overrides = request_overrides or {}
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **request_overrides).url
        try: playlist_id, song_infos = parse_qs(urlparse(playlist_url).query, keep_blank_values=False).get('playlist_id')[0], []; assert playlist_id
        except: playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, SODA_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, page_size, playlist_result_first = [], 1, 20, {}
        while True:
            params = {'playlist_id': playlist_id, 'cursor': str(page_size * (page - 1)), 'cnt': str(page_size), 'aid': '386088', 'device_platform': 'web', 'channel': 'pc_web'}
            try: (resp := self.get(f"https://api.qishui.com/luna/pc/playlist/detail?", params=params, **request_overrides)).raise_for_status()
            except Exception: break
            if (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['media_resources'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['media_resources'], [])); page += 1
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['playlist', 'count_tracks'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["id"]: d for d in tracks_in_playlist}.values())
        for track_idx in range(len(tracks_in_playlist)):
            try: tracks_in_playlist[track_idx]['entity']['track'] = safeextractfromdict(tracks_in_playlist[track_idx], ['entity', 'track_wrapper', 'track'], {})
            except Exception: continue
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
        playlist_name = safeextractfromdict(playlist_result_first, ['playlist', 'title'], None)
        song_infos = self._removeduplicates(song_infos=song_infos); work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        # return results
        return song_infos