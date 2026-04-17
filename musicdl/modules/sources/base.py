'''
Function:
    Implementation of BaseMusicClient
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import random
import pickle
import requests
from pathlib import Path
from threading import Lock
from rich.text import Text
from itertools import chain
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT, TIT2, TPE1, TALB
from mutagen.flac import FLAC
from datetime import datetime
from typing import TYPE_CHECKING
from collections import defaultdict
from pathvalidate import sanitize_filepath
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn, MofNCompleteColumn, ProgressColumn, Task
from ..utils import LoggerHandle, AudioLinkTester, SongInfo, SongInfoUtils, HLSDownloader, IOUtils, usedownloadheaderscookies, usesearchheaderscookies, useparseheaderscookies, cookies2dict, cookies2string, optionalimport, optionalimportfrom

try:
    from fake_useragent import UserAgent
except ImportError:
    UserAgent = None

# Suppress urllib3 warnings for frozen mode compatibility
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure requests adapters with extended timeout for frozen mode
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_robust_session():
    """Create a requests session with retry and timeout configuration for frozen mode."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


'''AudioAwareColumn'''
class AudioAwareColumn(ProgressColumn):
    def __init__(self):
        super(AudioAwareColumn, self).__init__()
        self._download_col = DownloadColumn()
    '''render'''
    def render(self, task: Task):
        kind = task.fields.get("kind", "download")
        if kind == "overall": completed = int(task.completed); total = int(task.total) if task.total is not None else 0; return Text(f"{completed}/{total} audios")
        elif kind == "hls": completed = int(task.completed); total = int(task.total) if task.total is not None else 0; return Text(f"{completed}/{total} segments")
        else: return self._download_col.render(task)


'''BaseMusicClient'''
class BaseMusicClient():
    source = 'BaseMusicClient'
    def __init__(self, search_size_per_source: int = 5, auto_set_proxies: bool = False, random_update_ua: bool = False, enable_search_curl_cffi: bool = False, enable_parse_curl_cffi: bool = False, enable_download_curl_cffi: bool = False, maintain_session: bool = False, logger_handle: LoggerHandle = None, disable_print: bool = False, work_dir: str = 'musicdl_outputs', 
                 max_retries: int = 3, freeproxy_settings: dict = None, default_search_cookies: dict | str = None, default_download_cookies: dict | str = None, default_parse_cookies: dict | str = None, strict_limit_search_size_per_page: bool = True, search_size_per_page: int = 10, quark_parser_config: dict = None):
        # set up work dir
        IOUtils.touchdir(work_dir)
        # search size
        self.search_size_per_source = search_size_per_source
        self.search_size_per_page = min(search_size_per_source, search_size_per_page)
        self.strict_limit_search_size_per_page = strict_limit_search_size_per_page
        # pyfreeproxy
        self.auto_set_proxies = auto_set_proxies
        self.freeproxy_settings = dict(freeproxy_settings or {})
        freeproxy = optionalimportfrom('freeproxy', 'freeproxy')
        if TYPE_CHECKING: from freeproxy import freeproxy as freeproxy
        (default_freeproxy_settings := dict(disable_print=True, proxy_sources=['ProxiflyProxiedSession'], max_tries=20, init_proxied_session_cfg={})).update(self.freeproxy_settings)
        self.proxied_session_client = freeproxy.ProxiedSessionClient(**default_freeproxy_settings) if auto_set_proxies else None
        # logger handle
        self.disable_print = disable_print
        self.logger_handle = logger_handle if logger_handle else LoggerHandle()
        # work dir
        self.work_dir = work_dir
        # whether maintain session
        self.maintain_session = maintain_session
        # max http request retries
        self.max_retries = max(max_retries, 1)
        # headers and ua trick
        self.random_update_ua = random_update_ua
        self.default_search_headers = {'User-Agent': UserAgent().random}
        self.default_download_headers = {'User-Agent': UserAgent().random}
        self.default_parse_headers = {'User-Agent': UserAgent().random}
        self.default_headers = self.default_search_headers
        # cookies
        self.default_search_cookies = cookies2dict(default_search_cookies)
        self.default_download_cookies = cookies2dict(default_download_cookies)
        self.default_parse_cookies = cookies2dict(default_parse_cookies)
        self.default_cookies = self.default_search_cookies
        # curl cffi trick
        self.enable_search_curl_cffi = enable_search_curl_cffi
        self.enable_download_curl_cffi = enable_download_curl_cffi
        self.enable_parse_curl_cffi = enable_parse_curl_cffi
        self.enable_curl_cffi = self.enable_search_curl_cffi
        self.cc_impersonates = self._listccimpersonates() if (enable_search_curl_cffi or enable_download_curl_cffi or enable_parse_curl_cffi) else None
        # quark parser settings
        self.quark_parser_config = quark_parser_config or {}
        self.quark_default_download_headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36 Core/1.94.225.400 QQBrowser/12.2.5544.400', 'origin': 'https://pan.quark.cn', 'referer': 'https://pan.quark.cn/', 'accept-language': 'zh-CN,zh;q=0.9', 'cookie': cookies2string(self.quark_parser_config.get('cookies'))}
        self.quark_default_download_cookies = {} # placeholder for future potential changes in quark, useless now
        # init requests.Session
        self._initsession()
    '''_listccimpersonates'''
    def _listccimpersonates(self):
        curl_cffi = optionalimport('curl_cffi')
        root = Path(curl_cffi.__file__).resolve().parent
        exts = {".py", ".so", ".pyd", ".dll", ".dylib"}
        pat = re.compile(rb"\b(?:chrome|edge|safari|firefox|tor)(?:\d+[a-z_]*|_android|_ios)?\b")
        return sorted({m.decode("utf-8", "ignore") for p in root.rglob("*") if p.suffix in exts for m in pat.findall(p.read_bytes())})
    '''_initsession'''
    def _initsession(self):
        if self.maintain_session and getattr(self, 'session', None) and getattr(self, 'audio_link_tester', None) and getattr(self, 'quark_audio_link_tester', None): self.session.headers = self.default_headers; return
        curl_cffi = optionalimport('curl_cffi')
        if TYPE_CHECKING: import curl_cffi as curl_cffi
        self.session = create_robust_session() if not self.enable_curl_cffi else curl_cffi.requests.Session()
        self.session.headers = self.default_headers
        self.audio_link_tester = AudioLinkTester(headers=copy.deepcopy(self.default_download_headers), cookies=copy.deepcopy(self.default_download_cookies))
        self.quark_audio_link_tester = AudioLinkTester(headers=copy.deepcopy(self.quark_default_download_headers), cookies=copy.deepcopy(self.quark_default_download_cookies))
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None) -> list:
        raise NotImplementedError('not to be implemented')
    '''_constructuniqueworkdir'''
    def _constructuniqueworkdir(self, keyword: str, sort_by_search_kwd_and_time: bool = True) -> str:
        time_stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        IOUtils.touchdir((work_dir := sanitize_filepath(os.path.join(self.work_dir, self.source, f'{time_stamp} {keyword}') if sort_by_search_kwd_and_time else os.path.join(self.work_dir, self.source))))
        return work_dir
    '''_removeduplicates'''
    def _removeduplicates(self, song_infos: list[SongInfo] = None) -> list[SongInfo]:
        unique_song_infos, identifiers = [], set()
        for song_info in song_infos:
            if song_info.identifier in identifiers: continue
            identifiers.add(song_info.identifier); unique_song_infos.append(song_info)
        return unique_song_infos
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        raise NotImplementedError('not be implemented')
    '''search'''
    @usesearchheaderscookies
    def search(self, keyword: str, num_threadings: int = 5, request_overrides: dict = None, rule: dict = None, main_process_context: Progress = None, main_progress_id: int = None, main_progress_lock: Lock = None) -> list[SongInfo]:
        # logging
        self.logger_handle.info(f'Start to search music files using {self.source}.', disable_print=self.disable_print)
        # construct search urls
        search_urls = self._constructsearchurls(keyword=keyword, rule=dict(rule or {}), request_overrides=(request_overrides := dict(request_overrides or {})))
        # multi threadings for searching music files
        owns_progress = True if main_process_context is None else False
        if owns_progress: main_process_context = Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10); main_process_context.__enter__()
        main_progress_lock = Lock() if main_progress_lock is None else main_progress_lock
        with main_progress_lock:
            progress_id = main_process_context.add_task(f"{self.source}.search >>> Completed (0/{len(search_urls)}) Search URLs", total=len(search_urls))
            if main_progress_id is not None:
                cur_total = main_process_context.tasks[main_progress_id].total or 0
                main_process_context.update(main_progress_id, total=cur_total + len(search_urls))
                main_process_context.update(main_progress_id, description=f"Search From Sources >>> Completed ({int(main_process_context.tasks[main_progress_id].completed)}/{cur_total + len(search_urls)}) Search URLs")
        submitted_tasks = []; song_infos: dict[str, list[SongInfo]] = {}
        with ThreadPoolExecutor(max_workers=num_threadings) as pool:
            for search_url_idx, search_url in enumerate(search_urls): song_infos[str(search_url_idx)] = []; submitted_tasks.append(pool.submit(self._search, keyword, search_url, request_overrides, song_infos[str(search_url_idx)], main_process_context, progress_id))
            for future in as_completed(submitted_tasks):
                future.result()
                with main_progress_lock:
                    main_process_context.advance(progress_id, 1); num_searched_urls = int(main_process_context.tasks[progress_id].completed)
                    main_process_context.update(progress_id, description=f"{self.source}.search >>> Completed ({num_searched_urls}/{len(search_urls)}) Search URLs")
                    main_progress_id is not None and main_process_context.advance(main_progress_id, 1)
                    main_progress_id is not None and main_process_context.update(main_progress_id, description=f"Search From Sources >>> Completed ({int(main_process_context.tasks[main_progress_id].completed)}/{int(main_process_context.tasks[main_progress_id].total or 0)}) Search URLs")
        song_infos, work_dir, work_dir_to_song_info = self._removeduplicates(song_infos=list(chain.from_iterable(song_infos.values()))), self._constructuniqueworkdir(keyword=keyword), defaultdict(list)
        for song_info in song_infos:
            if not isinstance(song_info, SongInfo) or not song_info.with_valid_download_url: continue
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            work_dir_to_song_info[song_info.work_dir].append(song_info.todict())
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # logging and save search results
        if len(song_infos) > 0:
            work_dir_for_logging = ', '.join(list(set([k for k, _ in work_dir_to_song_info.items()])))
            [(IOUtils.touchdir(w), self._savetopkl(items, os.path.join(w, "search_results.pkl"))) for w, items in work_dir_to_song_info.items()]
            self._savetotxt(song_infos, os.path.join(work_dir_for_logging, 'search_results.txt'))
            self.logger_handle.info(f'Finished searching music files from {self.source}. Search results have been saved to {work_dir_for_logging}, valid items: {len(song_infos)}.', disable_print=self.disable_print)
        else:
            self.logger_handle.info(f'Finished searching music files from {self.source}. No valid items found.', disable_print=self.disable_print)
        if owns_progress: main_process_context.__exit__(None, None, None)
        # return
        return song_infos
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list[SongInfo] = [], progress: Progress = None, song_progress_id: int = 0, auto_supplement_song: bool = True):
        # init
        song_info, request_overrides = copy.deepcopy(song_info), copy.deepcopy(request_overrides or {})
        song_info._save_path = sanitize_filepath(song_info.save_path); song_info.work_dir = os.path.dirname(song_info.save_path); IOUtils.touchdir(song_info.work_dir)
        # hls
        if song_info.protocol.upper() in {'HLS'}:
            try:
                hls_downloader = HLSDownloader(output_dir=song_info.work_dir, proxies=request_overrides.pop('proxies', {}) or self._autosetproxies(), headers=song_info.default_download_headers or request_overrides.pop('headers', {}) or self.default_headers, cookies=song_info.default_download_cookies or request_overrides.pop('cookies', {}) or self.default_cookies, logger_handle=self.logger_handle, verify_tls=request_overrides.pop('verify', True), timeout=request_overrides.pop('timeout', (10, 30)), disable_print=self.disable_print, request_overrides=request_overrides)
                hls_downloader.download(song_info.download_url, song_info.save_path, quality='best', keep_temp=False, remux=True, progress=progress, progress_id=song_progress_id)
                downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(song_info, logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else song_info)
            except Exception as err:
                progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})")
                self.logger_handle.error(f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})", disable_print=self.disable_print)
        # http with pre downloaded contents
        elif song_info.protocol.upper() in {'HTTP'} and song_info.downloaded_contents:
            try:
                progress.update(song_progress_id, total=(total_size := song_info.downloaded_contents.__sizeof__()))
                with open(song_info.save_path, "wb") as fp: fp.write(song_info.downloaded_contents)
                progress.advance(song_progress_id, total_size)
                progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Success)")
                downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(song_info, logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else song_info)
            except Exception as err:
                progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})")
                self.logger_handle.error(f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})", disable_print=self.disable_print)
        # naive http download
        elif song_info.protocol.upper() in {'HTTP'}:
            try:
                if song_info.default_download_headers: request_overrides['headers'] = song_info.default_download_headers
                if 'timeout' not in request_overrides: request_overrides['timeout'] = (10, 30)
                if song_info.default_download_cookies: request_overrides['cookies'] = song_info.default_download_cookies
                try: (resp := self.get(song_info.download_url, stream=True, **request_overrides)).raise_for_status()
                except Exception: (resp := self.get(song_info.download_url, stream=True, verify=False, **request_overrides)).raise_for_status()
                total_size, chunk_size, downloaded_size = int(float(resp.headers.get("Content-Length", 0) or 0)), 65536, 0
                progress.update(song_progress_id, total=total_size if total_size > 0 else None)
                with open(song_info.save_path, "wb") as fp:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if chunk: fp.write(chunk); downloaded_size += len(chunk)
                        downloading_text = "%0.2fMB/%0.2fMB" % (downloaded_size / 1024 / 1024, total_size / 1024 / 1024) if total_size > 0 else "%0.2fMB/%0.2fMB" % (downloaded_size / 1024 / 1024, downloaded_size / 1024 / 1024)
                        (total_size == 0) and progress.update(song_progress_id, total=downloaded_size); progress.advance(song_progress_id, len(chunk))
                        progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Downloading: {downloading_text})")
                progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Success)")
                downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(song_info, logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else song_info)
            except Exception as err:
                progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})")
                self.logger_handle.error(f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})", disable_print=self.disable_print)
        # return
        return downloaded_song_infos
    '''_embed_lyrics'''
    def _embed_lyrics(self, song_info: SongInfo):
        try:
            if not song_info.lyric or not song_info.save_path or not os.path.exists(song_info.save_path):
                return
            ext = song_info.ext.lower()
            if ext == 'mp3':
                try:
                    audio = MP3(song_info.save_path, ID3=ID3)
                    if audio.tags is None:
                        audio.add_tags()
                    audio.tags.add(USLT(encoding=3, lang='eng', desc='desc', text=song_info.lyric))
                    if song_info.song_name: audio.tags.add(TIT2(encoding=3, text=song_info.song_name))
                    if song_info.singers: audio.tags.add(TPE1(encoding=3, text=song_info.singers))
                    if song_info.album: audio.tags.add(TALB(encoding=3, text=song_info.album))
                    audio.save()
                except Exception as err:
                    self.logger_handle.warning(f'BaseMusicClient._embed_lyrics >>> {song_info.song_name} (MP3 Error: {err})', disable_print=self.disable_print)
            elif ext == 'flac':
                try:
                    audio = FLAC(song_info.save_path)
                    audio['lyrics'] = song_info.lyric
                    if song_info.song_name: audio['title'] = song_info.song_name
                    if song_info.singers: audio['artist'] = song_info.singers
                    if song_info.album: audio['album'] = song_info.album
                    audio.save()
                except Exception as err:
                    self.logger_handle.warning(f'BaseMusicClient._embed_lyrics >>> {song_info.song_name} (FLAC Error: {err})', disable_print=self.disable_print)
        except Exception as err:
             self.logger_handle.warning(f'BaseMusicClient._embed_lyrics >>> {song_info.song_name} (Global Error: {err})', disable_print=self.disable_print)
    '''download'''
    @usedownloadheaderscookies
    def download(self, song_infos: list[SongInfo], num_threadings: int = 5, request_overrides: dict = None, progress_handler: Progress = None, auto_supplement_song: bool = True) -> list[SongInfo]:
        # init
        request_overrides = request_overrides or {}
        # logging
        self.logger_handle.info(f'Start to download music files using {self.source}.', disable_print=self.disable_print)
        song_infos = [song_info for song_info in song_infos if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS]
        # multi threadings for downloading music files
        columns = [SpinnerColumn(), TextColumn("{task.description}"), BarColumn(bar_width=None), TaskProgressColumn(), AudioAwareColumn(), TransferSpeedColumn(), TimeRemainingColumn()]
        owns_progress = False
        if progress_handler:
            progress = progress_handler
        else:
            progress = Progress(*columns, refresh_per_second=20, expand=True)
            owns_progress = True
            progress.__enter__()
        try:
            songs_progress_id = progress.add_task(f"{self.source}.download >>> Completed (0/{len(song_infos)}) SongInfos", total=len(song_infos), kind='overall')
            song_progress_ids, submitted_tasks, downloaded_song_infos = [], [], []
            for _, song_info in enumerate(song_infos):
                desc = f"{self.source}.download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Preparing)"
                song_progress_ids.append(progress.add_task(desc, total=None, kind='download'))
            with ThreadPoolExecutor(max_workers=num_threadings) as pool:
                for song_progress_id, song_info in zip(song_progress_ids, song_infos): submitted_tasks.append(pool.submit(self._download, song_info, dict(request_overrides or {}), downloaded_song_infos, progress, song_progress_id, auto_supplement_song))
                for future in as_completed(submitted_tasks): future.result(); progress.advance(songs_progress_id, 1); progress.update(songs_progress_id, description=f"{self.source}.download >>> Completed ({int(progress.tasks[songs_progress_id].completed)}/{len(song_infos)}) SongInfos")
        finally:
            if owns_progress:
                progress.__exit__(None, None, None)
        # logging and save download results
        if len(downloaded_song_infos) > 0:
            work_dir_to_song_info, work_dir_for_logging = defaultdict(list), ', '.join(list(set([str(s.work_dir) for s in downloaded_song_infos])))
            for song_info in downloaded_song_infos:
                if not isinstance(song_info, SongInfo) or not song_info.with_valid_download_url: continue
                work_dir_to_song_info[song_info.work_dir].append(song_info.todict())
            [(IOUtils.touchdir(w), self._savetopkl(items, os.path.join(w, "download_results.pkl"))) for w, items in work_dir_to_song_info.items()]
            self._savetotxt(downloaded_song_infos, os.path.join(work_dir_for_logging, 'download_results.txt'), auto_sanitize=False) if hasattr(self, '_savetotxt') else None
            self.logger_handle.info(f'Finished downloading music files from {self.source}. Download results have been saved to {work_dir_for_logging}, valid downloads: {len(downloaded_song_infos)}.', disable_print=self.disable_print)
        else:
            self.logger_handle.info(f'Finished downloading music files from {self.source}. No valid downloads found.', disable_print=self.disable_print)
        # return
        return downloaded_song_infos
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None) -> list[SongInfo]:
        raise NotImplementedError(f'Not supported now to parse playlist from {self.source}')
    '''_autosetproxies'''
    def _autosetproxies(self) -> dict:
        if not self.auto_set_proxies: return {}
        try: proxies = self.proxied_session_client.getrandomproxy()
        except Exception as err: self.logger_handle.error(f'{self.source}._autosetproxies >>> freeproxy lib failed to auto fetch proxies (Error: {err})', disable_print=self.disable_print); proxies = {}
        return proxies
    '''get'''
    def get(self, url, **kwargs):
        if 'cookies' not in kwargs: kwargs['cookies'] = self.default_cookies
        if 'impersonate' not in kwargs and self.enable_curl_cffi: kwargs['impersonate'] = random.choice(self.cc_impersonates)
        if 'timeout' not in kwargs: kwargs['timeout'] = (10, 30)
        if 'verify' not in kwargs: kwargs['verify'] = False
        max_retries = kwargs.pop('max_retries', self.max_retries)
        resp = None
        for _ in range(max_retries):
            if not self.maintain_session:
                self._initsession()
                with suppress(Exception):
                    if self.random_update_ua: self.session.headers.update({'User-Agent': UserAgent().random})
            proxies = kwargs.pop('proxies', None) or self._autosetproxies() or self.session.proxies
            try: (resp := self.session.get(url, proxies=proxies, **kwargs)).raise_for_status()
            except Exception as err: self.logger_handle.error(f'{self.source}.get >>> {url} (Error: {err}; status={getattr(locals().get("resp"), "status_code", None)})', disable_print=self.disable_print); continue
            return resp
        return resp
    '''post'''
    def post(self, url, **kwargs):
        if 'cookies' not in kwargs: kwargs['cookies'] = self.default_cookies
        if 'impersonate' not in kwargs and self.enable_curl_cffi: kwargs['impersonate'] = random.choice(self.cc_impersonates)
        if 'timeout' not in kwargs: kwargs['timeout'] = (10, 30)
        if 'verify' not in kwargs: kwargs['verify'] = False
        max_retries = kwargs.pop('max_retries', self.max_retries)
        resp = None
        for _ in range(max_retries):
            if not self.maintain_session:
                self._initsession()
                with suppress(Exception):
                    if self.random_update_ua: self.session.headers.update({'User-Agent': UserAgent().random})
            proxies = kwargs.pop('proxies', None) or self._autosetproxies() or self.session.proxies
            try: (resp := self.session.post(url, proxies=proxies, **kwargs)).raise_for_status()
            except Exception as err: self.logger_handle.error(f'{self.source}.post >>> {url} (Error: {err}; status={getattr(locals().get("resp"), "status_code", None)})', disable_print=self.disable_print); continue
            return resp
        return resp
    '''_savetopkl'''
    def _savetopkl(self, data, file_path, auto_sanitize=True):
        if auto_sanitize: file_path = sanitize_filepath(file_path)
        with open(file_path, 'wb') as fp: pickle.dump(data, fp)
    '''_savetotxt'''
    def _savetotxt(self, song_infos, file_path, auto_sanitize=True):
        if auto_sanitize: file_path = sanitize_filepath(file_path)
        with open(file_path, 'w', encoding='utf-8') as fp:
            for song_info in song_infos:
                fp.write('='*50 + '\n')
                fp.write(f'Song Name: {song_info.song_name}\n')
                fp.write(f'Singers: {song_info.singers}\n')
                fp.write(f'Album: {song_info.album}\n')
                fp.write(f'Source: {song_info.source}\n')
                fp.write(f'Duration: {song_info.duration}\n')
                fp.write(f'File Size: {song_info.file_size}\n')
                fp.write(f'Bitrate: {song_info.bitrate}\n')
                fp.write(f'Save Path: {song_info.save_path}\n')
                fp.write('-'*20 + ' Lyrics ' + '-'*20 + '\n')
                fp.write(f'{song_info.lyric}\n')
                fp.write('='*50 + '\n\n')