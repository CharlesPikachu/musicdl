'''
Function:
    Implementation of MOOVMusicClient: https://moov.hk/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
import time
import uuid
import copy
import hashlib
import platform
import subprocess
from pathlib import Path
from contextlib import suppress
from .base import BaseMusicClient
from platformdirs import user_log_dir
from ..utils.hosts import MOOV_MUSIC_HOSTS
from pathvalidate import sanitize_filepath, sanitize_filename
from urllib.parse import urlencode, urlparse, parse_qs, unquote
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import usedownloadheaderscookies, legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, extractdurationsecondsfromlrc, cookies2string, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester, IOUtils, SongInfoUtils, NM3U8DLREDownloadCommand


'''MOOVMusicClient'''
class MOOVMusicClient(BaseMusicClient):
    source = 'MOOVMusicClient'
    DEVICE_ID = str(uuid.UUID(bytes=hashlib.sha256(f"{platform.node()}-{uuid.getnode()}".encode()).digest()[:16], version=4)).upper()
    def __init__(self, **kwargs):
        super(MOOVMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", "Origin": "https://moov.hk", "Referer": "https://moov.hk/", "Accept": "application/json, text/javascript, */*; q=0.01",}
        self.default_parse_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36", "Origin": "https://moov.hk", "Referer": "https://moov.hk/", "Accept": "application/json, text/javascript, */*; q=0.01",}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"}
        if self.default_search_cookies: self.default_search_headers['Cookie'] = cookies2string(self.default_search_cookies)
        if self.default_parse_cookies: self.default_parse_headers['Cookie'] = cookies2string(self.default_parse_cookies)
        if self.default_download_cookies: self.default_download_headers['Cookie'] = cookies2string(self.default_download_cookies)
        MOOVMusicClient.DEVICE_ID = self.default_search_cookies.get('MOOVUUID') or self.default_parse_cookies.get('MOOVUUID') or self.default_download_cookies.get('MOOVUUID')
        self.default_headers = self.default_search_headers; self.default_search_cookies = {}; self.default_parse_cookies = {}; self.default_download_cookies = {}
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0, auto_supplement_song: bool = True):
        # deal with hls streams
        song_info, request_overrides = copy.deepcopy(song_info), copy.deepcopy(request_overrides or {})
        song_info._save_path = sanitize_filepath(song_info.save_path); song_info.work_dir = os.path.dirname(song_info.save_path); IOUtils.touchdir(song_info.work_dir)
        try:
            log_file_path = os.path.join(user_log_dir(appname='musicdl', appauthor='zcjin'), f"musicdl_{sanitize_filename(str(song_info.identifier))}.log")
            cmd = NM3U8DLREDownloadCommand().build(song_info.download_url, song_info.save_path, log_file_path=log_file_path, auto_select=True, tmp_dir=sanitize_filepath(str(Path(song_info.save_path).parent / str(song_info.identifier))), save_pattern=Path(song_info.save_path).name, mods=({"__add__": [("--key", k) for k in keys]} if (keys := song_info.download_url_status.get('decrypt_keys')) else None))
            progress.update(song_progress_id, total=None, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Downloading)")
            subprocess.run(cmd, check=True, capture_output=self.disable_print, text=True, encoding='utf-8', errors='ignore')
            real_save_path = max(Path(song_info.save_path).parent.glob(f"{Path(song_info.save_path).name}*"), key=lambda p: p.stat().st_mtime, default=None)
            song_info._save_path, song_info.ext = AudioLinkTester.extractaudiofromvideolossless(real_save_path, song_info.save_path)
            if not os.path.samefile(real_save_path, song_info.save_path): os.remove(real_save_path)
            progress.update(song_progress_id, total=os.path.getsize(song_info.save_path), advance=os.path.getsize(song_info.save_path), description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Success)")
            downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(song_info, logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else song_info)
        except Exception as err:
            progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})")
            self.logger_handle.error(f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})", disable_print=self.disable_print)
        # return
        return downloaded_song_infos
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"value": keyword, "type": "product", "from": 0, "count": 40, "_": int(time.time() * 1000)}).update(rule)
        # construct search urls
        base_url, search_urls, page_size, count = 'https://search-hk.moov-music.com/search/api/search/search?', [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['count'] = page_size
            page_rule['from'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_getsongmetainfo'''
    def _getsongmetainfo(self, song_id, request_overrides: dict = None):
        request_overrides, resp = request_overrides or {}, None
        with suppress(Exception): (resp := self.get("https://mtg.now.com/moov/api/content/getProductDetail", params={"productId": song_id}, **request_overrides)).raise_for_status()
        return (resp2json(resp=resp).get('dataObject', {}) or {})
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('productId'))): return song_info
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            search_result.update(self._getsongmetainfo(song_id=song_id, request_overrides=request_overrides))
            for music_quality in [q.strip() for q in (search_result.get('qualities', 'HD') or 'HD').split(',')][::-1]:
                params = {
                    "deviceid": MOOVMusicClient.DEVICE_ID, "devicetype": "web", "cat": "playlist", "refid": "", "reftype": "", "pid": song_id, "preview": "F", 
                    "connect": "web", "streamtype": "stdHlsSgl", "quality": music_quality, "application": "moovnext", "clientver": "2.0.6", "carrier": "csl",
                }
                with suppress(Exception): resp = None; (resp := self.get("https://mtg.now.com/moov/api/content/checkout", params=params, **request_overrides)).raise_for_status()
                download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['result', 'dataObject', 'playUrl'], None) or safeextractfromdict(download_result, ['result', 'dataObject', 'playUrlValidate'], None)
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                ext = (safeextractfromdict(download_result, ['result', 'dataObject', 'format'], 'acc') or 'aac').lower()
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('productTitle')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('artists', []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(search_result.get('albumTitle')), ext=ext, file_size_bytes='HLS', 
                    file_size='HLS', identifier=song_id, duration_s=int(float(search_result.get('productLength') or 0)), duration=SongInfoUtils.seconds2hms(search_result.get('productLength')), lyric=None, cover_url=search_result.get('image') or search_result.get('albumCover') or search_result.get('thumbnail'), download_url=download_url_status['download_url'], download_url_status=download_url_status, protocol='HLS'
                )
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        with suppress(Exception): resp = None; (resp := self.get(f'https://mtg.now.com/moov/api/lyric/getLyric?pid={song_id}&_={int(time.time() * 1000)}', **request_overrides)).raise_for_status()
        lyric = cleanlrc(safeextractfromdict((lyric_result := resp2json(resp=resp)), ['dataObject', 'lyric'], '') or '')
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        if not song_info.duration or song_info.duration in {'-:-:-', '00:00:00'}: song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        page_no, search_result_idx = int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('from')[0]) / self.search_size_per_page) + 1, -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **(request_overrides := request_overrides or {}))).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp=resp)['dataObject']['primarySearch'] + (safeextractfromdict(resp2json(resp=resp)['dataObject'], ['secondarySearch'], []) or [])):
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
    '''_guessmoovreftype'''
    def _guessmoovreftype(self, url: str, profile_id: str = "") -> str:
        p, text, query = urlparse(url), unquote(url).upper(), parse_qs(urlparse(url).query)
        frag_query = parse_qs(p.fragment.split("?", 1)[1]) if "?" in p.fragment else {}
        # explicit refType in normal query or hash query
        if (reftype := next((values[0].upper() for qs in (query, frag_query) for key, values in qs.items() if key.lower() == "reftype" and values), None)) is not None: return reftype
        # profileId from argument or URL query
        pid = (profile_id or next((v[0] for qs in (query, frag_query) for k, v in qs.items() if k.lower() in {"profileid", "playlistid"} and v), "")).upper()
        # share campaign / URL text markers
        if re.search(r"SHARING_(USER_PLAYLIST|OUPL|UPL)[-_]", text): return "OUPL"
        if re.search(r"SHARING_PP[-_]", text): return "PP"
        if re.search(r"SHARING_PC[-_]", text): return "PC"
        # hash route markers
        frag_path = p.fragment.split("?", 1)[0].lower()
        if "/playlist/user/" in frag_path: return "OUPL"
        if "/playlist/chart/" in frag_path or "/chart/" in frag_path: return "PC"
        # pageid mapping observed from MOOV share URLs
        pageid = (query.get("pageid") or frag_query.get("pageid") or [""])[0]
        if pageid == "26": return "OUPL"
        if pageid == "13": return "PP"
        if pageid == "18": return "PC"
        # profileId prefix
        if pid.startswith("PP"): return "PP"
        if pid.startswith("PC"): return "PC"
        # most user playlist IDs are long uppercase IDs without PP/PC prefix
        return "OUPL"
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        # init
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **(request_overrides := dict(request_overrides or {}))).url
        playlist_id, song_infos = (lambda p: next((v[0] for qs in (parse_qs(p.query), parse_qs(p.fragment.split("?", 1)[1] if "?" in p.fragment else "")) for k, v in qs.items() if k.lower() in {"profileid", "playlistid", "s"} and v), (p.fragment.split("?", 1)[0].rstrip("/").split("/")[-1] if "/playlist/" in p.fragment else p.path.rstrip("/").split("/")[-1])))(urlparse(playlist_url)), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, MOOV_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        (resp := self.get(f'https://mtg.now.com/moov/api/profile/getProfile?refType={self._guessmoovreftype(url=playlist_url)}&profileId={playlist_id}&deviceType=web&_={int(time.time() * 1000)}', **request_overrides)).raise_for_status()
        modules = (playlist_result := resp2json(resp=resp))['dataObject']['modules']
        tracks_in_playlist = [product for m in modules if isinstance(m, dict) for product in (m.get("products", []) or [])]
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
        playlist_name = legalizestring(safeextractfromdict(playlist_result, ['dataObject', 'modules', 0, 'chiName'], None) or safeextractfromdict(playlist_result, ['dataObject', 'modules', 0, 'engName'], None) or safeextractfromdict(playlist_result, ['dataObject', 'chiTitle', 0], None) or safeextractfromdict(playlist_result, ['dataObject', 'engTitle', 0], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos