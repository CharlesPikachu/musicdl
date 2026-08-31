'''
Function:
    Implementation of MiguMusicClient: https://music.migu.cn/v5/#/musicLibrary
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import json
import requests
from typing import Any, Dict
from contextlib import suppress
from rich.progress import Progress
from typing_extensions import Unpack
from pathvalidate import sanitize_filepath
from ..utils.hosts import MIGU_MUSIC_HOSTS
from .base import BaseMusicClient, BaseMusicClientKwargs
from urllib.parse import urlencode, urlparse, parse_qs, urlsplit, urljoin
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import resp2json, legalizestring, safeextractfromdict, usesearchheaderscookies, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils


'''MiguMusicClient'''
class MiguMusicClient(BaseMusicClient):
    source = 'MiguMusicClient'
    MAGIC = b"\xab\xcd\x01"
    MIGU_KEY = b"Jk8qzuePiJ1qE3mDYhLQ3T73DtDoAhLP"
    MUSIC_QUALITIES = {'LQ': 'mp3', 'PQ': 'mp3', 'HQ': 'mp3', 'SQ': 'flac', 'ZQ': 'flac', 'Z3D': 'flac', 'ZQ24': 'flac', 'ZQ32': 'flac'}
    def __init__(self, **kwargs: Unpack[BaseMusicClientKwargs]):
        super(MiguMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", "Accept": "application/json, text/plain, */*", 
            "Origin": "https://h5.nf.migu.cn", "Referer": "https://h5.nf.migu.cn/", "ua": "Android_migu", "version": "6.8.8", "channel": "014021I", "subchannel": "014021I",
        }
        self.default_parse_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", "Accept": "application/json, text/plain, */*", 
            "Origin": "https://h5.nf.migu.cn", "Referer": "https://h5.nf.migu.cn/", "ua": "Android_migu", "version": "6.8.8", "channel": "014021I", "subchannel": "014021I",
        }
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"text": keyword, 'pageNo': 1, 'pageSize': 20, 'isCopyright': 1, 'sort': 1, 'searchSwitch': {"song": 1, "album": 0, "singer": 0, "tagSong": 1, "mvSong": 0, "bestShow": 1}}).update(rule)
        # construct search urls
        search_urls, page_size, count, base_url = [], self.search_size_per_page, 0, 'https://c.musicapp.migu.cn/v1.0/content/search_all.do?'
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['pageSize'] = page_size
            page_rule['pageNo'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_decryptresp'''
    def _decryptresp(self, resp: requests.Response) -> Dict[str, Any]:
        raw, key = resp.content, MiguMusicClient.MIGU_KEY
        if resp.headers.get("signature") == "1" or raw.startswith(MiguMusicClient.MAGIC):
            seed = raw[3]; plain = bytes((byte + seed - key[i % len(key)]) & 0xFF for i, byte in enumerate(raw[4:]))
            return json.loads(plain.decode("utf-8"))
        else:
            return json.loads(raw.decode("utf-8"))
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (content_id := search_result.get('contentId'))) or (not (copyright_id := search_result.get('copyrightId'))): return song_info
        safe_obtain_filesize_func = lambda meta: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(str(meta.get('size') or meta.get('iosSize') or meta.get('androidSize') or meta.get('isize') or meta.get('asize') or '0').removesuffix('MB').strip()) if isinstance(meta, dict) else 0
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            headers =  {"Content-Type": "application/json;charset=UTF-8", "birth": "h5page", "signature": "1"}
            for music_quality in sorted((search_result.get('rateFormats', []) or []) + (search_result.get('newRateFormats', []) or []) + (search_result.get('audioFormats', []) or []), key=lambda x: int(safe_obtain_filesize_func(x)), reverse=True):
                if (not isinstance(music_quality, dict)) or (not (format_type := music_quality.get('formatType'))) or (not (resource_type := music_quality.get('resourceType'))) or (format_type in {'Z3D'}): continue # Z3D is encrypted audio format
                params = [("contentId", content_id), ("copyrightId", copyright_id), ("resourceType", resource_type), ("netType", "01"), ("toneFlag", format_type), ("scene", ""), ("lowerQualityContentId", content_id)]
                with suppress(Exception): (resp := self.get(f"https://c.musicapp.migu.cn/strategy/listen-url/h5/v2.4", params=params, headers=headers, **request_overrides)).raise_for_status()
                if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                download_url = safeextractfromdict((download_result := self._decryptresp(resp=resp)), ['data', 'url'], '') or f"https://app.pd.nf.migu.cn/MIGUM3.0/v1.0/content/sub/listenSong.do?channel=mx&copyrightId={copyright_id}&contentId={content_id}&toneFlag={format_type}&resourceType={resource_type}&userId=15548614588710179085069&netType=00"
                if not (download_url := re.sub(r'(?<=/)MP3_128_16_Stero(?=/)', 'MP3_320_16_Stero', download_url)) or not str(download_url).startswith('http'): continue
                duration_in_secs = int(float(safeextractfromdict(download_result, ['data', 'song', 'duration'], 0) or 0))
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True); del resp
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name') or search_result.get('songName')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singers') or search_result.get('singerList') or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(search_result.get('album') or (', '.join([album.get('name') for album in (search_result.get('albums') or []) if isinstance(album, dict) and album.get('name')]))),
                    ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=content_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['imgItems', -1, 'img'], None) or next((search_result.get(k) for k in ("img3", "img2", "img1") if search_result.get(k)), None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info.cover_url and not song_info.cover_url.startswith('http'): song_info.cover_url = urljoin('https://d.musicapp.migu.cn', song_info.cover_url)
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        lyric_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "Referer": "https://y.migu.cn/"}
        with suppress(Exception): lyric_url = search_result.get('lyricUrl') or self.get(f"https://app.c.nf.migu.cn/MIGUM3.0/strategy/pc/listen/v1.0?scene=&netType=01&resourceType=2&copyrightId={copyright_id}&contentId={content_id}&toneFlag=PQ", **request_overrides).json()['data']['lrcUrl']
        with suppress(Exception): (resp := requests.get(lyric_url, headers=lyric_headers, allow_redirects=True, **request_overrides)).raise_for_status(); resp.encoding = 'utf-8'; song_info.lyric = cleanlrc(resp.text)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, page_no, search_result_idx = request_overrides or {}, int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('pageNo')[0])), -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp)['songResultData']['result']):
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
        with suppress(Exception): playlist_id, song_infos = parse_qs(urlsplit(urlsplit(playlist_url).fragment).query).get('playlistId')[0], []
        if not playlist_id: playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, MIGU_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, playlist_result_first = [], 1, {}
        while True:
            with suppress(Exception): (resp := self.get(f"https://app.c.nf.migu.cn/MIGUM3.0/resource/playlist/song/v2.0?pageNo={page}&pageSize=50&playlistId={playlist_id}", **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['data', 'songList'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['data', 'songList'], [])); page += 1; del resp
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['data', 'totalCount'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["contentId"]: d for d in tracks_in_playlist}.values())
        with suppress(Exception): (resp := self.get(f'https://app.c.nf.migu.cn/resource/playlist/v2.0?playlistId={playlist_id}', **request_overrides)).raise_for_status(); playlist_result_first['meta_info'] = resp2json(resp=resp)
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
        playlist_name = legalizestring(safeextractfromdict(playlist_result_first, ['meta_info', 'data', 'title'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos