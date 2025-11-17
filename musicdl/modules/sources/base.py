'''
Function:
    Implementation of BaseMusicClient
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import pickle
import requests
from datetime import datetime
from freeproxy import freeproxy
from fake_useragent import UserAgent
from pathvalidate import sanitize_filepath
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..utils import LoggerHandle, touchdir, usedownloadheaderscookies, usesearchheaderscookies
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn, MofNCompleteColumn


'''BaseMusicClient'''
class BaseMusicClient():
    source = 'BaseMusicClient'
    def __init__(self, search_size_per_source: int = 5, auto_set_proxies: bool = False, random_update_ua: bool = False, max_retries: int = 5, maintain_session: bool = False, 
                 logger_handle: LoggerHandle = None, disable_print: bool = False, work_dir: str = 'musicdl_outputs', proxy_sources: list = None, default_search_cookies: dict = {},
                 default_download_cookies: dict = {}):
        # set up work dir
        touchdir(work_dir)
        # set attributes
        self.search_size_per_source = search_size_per_source
        self.auto_set_proxies = auto_set_proxies
        self.random_update_ua = random_update_ua
        self.max_retries = max_retries
        self.maintain_session = maintain_session
        self.logger_handle = logger_handle if logger_handle else LoggerHandle()
        self.disable_print = disable_print
        self.work_dir = work_dir
        self.proxy_sources = proxy_sources
        self.default_search_cookies = default_search_cookies if default_search_cookies else {}
        self.default_download_cookies = default_download_cookies if default_download_cookies else {}
        self.default_cookies = default_search_cookies
        # init requests.Session
        self.default_search_headers = {'User-Agent': UserAgent().random}
        self.default_download_headers = {'User-Agent': UserAgent().random}
        self.default_headers = self.default_search_headers
        self._initsession()
        # proxied_session_client
        self.proxied_session_client = freeproxy.ProxiedSessionClient(
            proxy_sources=['QiyunipProxiedSession'] if proxy_sources is None else proxy_sources, 
            disable_print=True
        ) if auto_set_proxies else None
    '''_initsession'''
    def _initsession(self):
        self.session = requests.Session()
        self.session.headers = self.default_headers
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = {}, request_overrides: dict = {}):
        raise NotImplementedError('not to be implemented')
    '''_constructuniqueworkdir'''
    def _constructuniqueworkdir(self, keyword: str):
        time_stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        work_dir = os.path.join(self.work_dir, self.source, f'{time_stamp} {keyword.replace(" ", "")}')
        touchdir(work_dir)
        return work_dir
    '''_removeduplicates'''
    def _removeduplicates(self, song_infos: list = None):
        unique_song_infos, identifiers = [], set()
        for song_info in song_infos:
            if song_info['identifier'] in identifiers:
                continue
            identifiers.add(song_info['identifier'])
            unique_song_infos.append(song_info)
        return unique_song_infos
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = {}, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        raise NotImplementedError('not be implemented')
    '''search'''
    @usesearchheaderscookies
    def search(self, keyword: str, num_threadings=5, request_overrides: dict = {}, rule: dict = {}):
        # logging
        self.logger_handle.info(f'Start to search music files using {self.source}.', disable_print=self.disable_print)
        # construct search urls
        search_urls = self._constructsearchurls(keyword=keyword, rule=rule, request_overrides=request_overrides)
        # multi threadings for searching music files
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn()) as progress:
            progress_id = progress.add_task(f"{self.source}.search >>> completed (0/{len(search_urls)})", total=len(search_urls))
            song_infos, submitted_tasks = [], []
            with ThreadPoolExecutor(max_workers=num_threadings) as pool:
                for search_url in search_urls:
                    submitted_tasks.append(pool.submit(
                        self._search, keyword, search_url, request_overrides, song_infos, progress, progress_id
                    ))
                for _ in as_completed(submitted_tasks):
                    num_searched_urls = int(progress.tasks[progress_id].completed)
                    progress.update(progress_id, description=f"{self.source}.search >>> completed ({num_searched_urls}/{len(search_urls)})")
        song_infos = self._removeduplicates(song_infos=song_infos)
        work_dir = self._constructuniqueworkdir(keyword=keyword)
        for song_info in song_infos:
            song_info['work_dir'] = work_dir
        # logging
        if len(song_infos) > 0:
            work_dir = song_infos[0]['work_dir']
            touchdir(work_dir)
            self._savetopkl(song_infos, os.path.join(work_dir, 'search_results.pkl'))
        else:
            work_dir = self.work_dir
        self.logger_handle.info(f'Finished searching music files using {self.source}. Search results have been saved to {work_dir}, valid items: {len(song_infos)}.', disable_print=self.disable_print)
        # return
        return song_infos
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: dict, request_overrides: dict = {}, downloaded_song_infos: list = [], progress: Progress = None, 
                  song_progress_id: int = 0, songs_progress_id: int = 0):
        try:
            touchdir(song_info['work_dir'])
            with self.get(song_info['download_url'], stream=True, **request_overrides) as resp:
                resp.raise_for_status()
                total_size, chunk_size, downloaded_size = int(resp.headers['content-length']), song_info.get('chunk_size', 1024), 0
                progress.update(song_progress_id, total=total_size)
                save_path, same_name_file_idx = os.path.join(song_info['work_dir'], f"{song_info['song_name']}.{song_info['ext']}"), 1
                while os.path.exists(save_path):
                    save_path = os.path.join(song_info['work_dir'], f"{song_info['song_name']}_{same_name_file_idx}.{song_info['ext']}")
                    same_name_file_idx += 1
                with open(save_path, "wb") as fp:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if not chunk: continue
                        fp.write(chunk)
                        downloaded_size = downloaded_size + len(chunk)
                        downloading_text = "%0.2fMB/%0.2fMB" % (downloaded_size / 1024 / 1024, total_size / 1024 / 1024)
                        progress.advance(song_progress_id, len(chunk))
                        progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info['song_name']} (Downloading: {downloading_text})")
                progress.advance(songs_progress_id, 1)
                progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info['song_name']} (Success)")
                downloaded_song_info = copy.deepcopy(song_info)
                downloaded_song_info['save_path'] = save_path
                downloaded_song_infos.append(downloaded_song_info)
        except Exception as err:
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info['song_name']} (Error: {err})")
        return downloaded_song_infos
    '''download'''
    @usedownloadheaderscookies
    def download(self, song_infos: list, num_threadings=5, request_overrides: dict = {}):
        # logging
        self.logger_handle.info(f'Start to download music files using {self.source}.', disable_print=self.disable_print)
        # multi threadings for downloading music files
        columns = [
            SpinnerColumn(), TextColumn("{task.description}"), BarColumn(bar_width=None), TaskProgressColumn(),
            DownloadColumn(), TransferSpeedColumn(), TimeRemainingColumn(),
        ]
        with Progress(*columns, refresh_per_second=20, expand=True) as progress:
            songs_progress_id = progress.add_task(f"{self.source}.download >>> completed (0/{len(song_infos)})", total=len(song_infos))
            song_progress_ids, downloaded_song_infos, submitted_tasks = [], [], []
            for _, song_info in enumerate(song_infos):
                desc = f"{self.source}.download >>> {song_info['song_name']} (Preparing)"
                song_progress_ids.append(progress.add_task(desc, total=None))
            with ThreadPoolExecutor(max_workers=num_threadings) as pool:
                for song_progress_id, song_info in zip(song_progress_ids, song_infos):
                    submitted_tasks.append(pool.submit(
                        self._download, song_info, request_overrides, downloaded_song_infos, progress, song_progress_id, songs_progress_id
                    ))
                for _ in as_completed(submitted_tasks):
                    num_downloaded_songs = int(progress.tasks[songs_progress_id].completed)
                    progress.update(songs_progress_id, description=f"{self.source}.download >>> completed ({num_downloaded_songs}/{len(song_infos)})")
        # logging
        if len(downloaded_song_infos) > 0:
            work_dir = downloaded_song_infos[0]['work_dir']
            touchdir(work_dir)
            self._savetopkl(downloaded_song_infos, os.path.join(work_dir, 'download_results.pkl'))
        else:
            work_dir = self.work_dir
        self.logger_handle.info(f'Finished downloading music files using {self.source}. Download results have been saved to {work_dir}, valid downloads: {len(downloaded_song_infos)}.', disable_print=self.disable_print)
        # return
        return downloaded_song_infos
    '''get'''
    def get(self, url, **kwargs):
        if 'cookies' not in kwargs: kwargs['cookies'] = self.default_cookies
        resp = None
        for _ in range(self.max_retries):
            if not self.maintain_session:
                self._initsession()
                if self.random_update_ua: self.session.headers.update({'User-Agent': UserAgent().random})
            if self.auto_set_proxies:
                try:
                    self.session.proxies = self.proxied_session_client.getrandomproxy()
                except Exception as err:
                    self.logger_handle.error(f'{self.source}.get >>> {url} (Error: {err})', disable_print=self.disable_print)
                    self.session.proxies = {}
            else:
                self.session.proxies = {}
            try:
                resp = self.session.get(url, **kwargs)
            except Exception as err:
                self.logger_handle.error(f'{self.source}.get >>> {url} (Error: {err})', disable_print=self.disable_print)
                continue
            if resp.status_code != 200: continue
            return resp
        return resp
    '''post'''
    def post(self, url, **kwargs):
        if 'cookies' not in kwargs: kwargs['cookies'] = self.default_cookies
        resp = None
        for _ in range(self.max_retries):
            if not self.maintain_session:
                self._initsession()
                if self.random_update_ua: self.session.headers.update({'User-Agent': UserAgent().random})
            if self.auto_set_proxies:
                try:
                    self.session.proxies = self.proxied_session_client.getrandomproxy()
                except Exception as err:
                    self.logger_handle.error(f'{self.source}.post >>> {url} (Error: {err})', disable_print=self.disable_print)
                    self.session.proxies = {}
            else:
                self.session.proxies = {}
            try:
                resp = self.session.post(url, **kwargs)
            except Exception as err:
                self.logger_handle.error(f'{self.source}.post >>> {url} (Error: {err})', disable_print=self.disable_print)
                continue
            if resp.status_code != 200: continue
            return resp
        return resp
    '''_savetopkl'''
    def _savetopkl(self, data, file_path, auto_sanitize=True):
        if auto_sanitize: file_path = sanitize_filepath(file_path)
        with open(file_path, 'wb') as fp:
            pickle.dump(data, fp)