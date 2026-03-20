'''
Function:
    Implementation of StreetVoiceMusicClient: https://www.streetvoice.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import time
from bs4 import BeautifulSoup
from .base import BaseMusicClient
from rich.progress import Progress
from pathvalidate import sanitize_filepath
from ..utils.hosts import STREETVOICE_MUSIC_HOSTS
from urllib.parse import urlencode, urljoin, urlparse, urlsplit, urlunsplit
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import touchdir, legalizestring, resp2json, usesearchheaderscookies, seconds2hms, safeextractfromdict, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester


'''StreetVoiceMusicClient'''
class StreetVoiceMusicClient(BaseMusicClient):
    source = 'StreetVoiceMusicClient'
    def __init__(self, **kwargs):
        super(StreetVoiceMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0", "Referer": "https://www.streetvoice.cn/", "x-requested-with": "XMLHttpRequest"}
        self.default_parse_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0", "Referer": "https://www.streetvoice.cn/", "x-requested-with": "XMLHttpRequest"}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0", "Referer": "https://www.streetvoice.cn/", "x-requested-with": "XMLHttpRequest"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        self.search_size_per_page = min(10, self.search_size_per_page)
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {'page': 1, 'q': keyword, 'type': 'song', '_pjax': '#pjax-container'}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://www.streetvoice.cn/search/?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['page'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('song_id'))): return song_info
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            try: (resp := self.get(f"https://www.streetvoice.cn/api/v5/song/{song_id}/?_={int(time.time() * 1000)}", **request_overrides)).raise_for_status()
            except Exception: return song_info
            try: (hls_resp := self.post(f"https://www.streetvoice.cn/api/v5/song/{song_id}/hls/file/", **request_overrides)).raise_for_status()
            except Exception: return song_info
            (download_result := resp2json(resp=resp))['hls/file'] = resp2json(resp=hls_resp)
            if not (download_url := download_result['hls/file']['file']) or not str(download_url).startswith('http'): return song_info
            try: (resp := self.session.head(download_url, **request_overrides)).raise_for_status(); download_url_status = {'ok': True}
            except Exception: return song_info
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('name')), singers=legalizestring(safeextractfromdict(download_result, ['user', 'profile', 'nickname'], None)), 
                album=legalizestring(safeextractfromdict(download_result, ['album', 'name'], None)), ext=download_url.removesuffix('.m3u8').split('?')[0].split('.')[-1], file_size_bytes=None, file_size='HLS', identifier=song_id, duration_s=download_result.get('length'), 
                duration=seconds2hms(download_result.get('length')), lyric=cleanlrc(safeextractfromdict(download_result, ['lyrics'], 'NULL')), cover_url=download_result.get('image'), download_url=download_url, download_url_status=download_url_status, protocol='HLS'
            )
            if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
        # return
        return song_info
    '''_extractonesearchpage'''
    def _extractonesearchpage(self, html_text: str, page_url: str):
        soup, search_results = BeautifulSoup(html_text, "lxml"), []
        for li in soup.select("ul.list-group-song li.work-item.item_box"):
            title_a = li.select_one(".work-item-info h4 a"); artist_a = li.select_one(".work-item-info h5 a")
            img = li.select_one(".cover-block img"); play_btn = li.select_one("button.js-search[data-id]")
            like_btn = li.select_one("button.js-like-btn[data-like-count]"); like_raw = like_btn.get("data-like-count") if like_btn else None
            song_href = title_a.get("href") if title_a else None; artist_href = artist_a.get("href") if artist_a else None
            search_results.append({
                "song_id": play_btn.get("data-id") if play_btn else None, "title": title_a.get_text(strip=True) if title_a else None, "artist": artist_a.get_text(strip=True) if artist_a else None, "song_url": urljoin(page_url, song_href) if song_href else None, 
                "artist_url": urljoin(page_url, artist_href) if artist_href else None, "cover_url": img.get("src") if img else None, "like_raw": like_raw,
            })
        return search_results
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result in self._extractonesearchpage(resp.text, "https://www.streetvoice.cn/"):
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
    '''_extractplaylistpagesongs'''
    def _extractplaylistpagesongs(self, html_text, base_url='https://streetvoice.cn'):
        soup, songs, seen = BeautifulSoup(html_text, 'lxml'), [], set()
        for li in soup.select('#item_box_list_1 li.item_box'):
            artist_a = li.select_one('.work-item-info h5 a') or li.select_one('.work-item-info h4 a'); num_el = li.select_one('.work-item-number h4')
            if not (song_a := li.select_one('.work-item-info h4 a[href*="/songs/"]')): continue
            if (url := urljoin(base_url, song_a['href'])) in seen: continue
            seen.add(url); songs.append({'index': int(num_el.get_text(strip=True)) if num_el else None, 'title': ' '.join(song_a.stripped_strings), 'song_url': url, 'song_id': urlparse(url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), 'artist': artist_a.get_text(strip=True) if artist_a else None, 'artist_url': urljoin(base_url, artist_a['href']) if artist_a and artist_a.has_attr('href') else None})
        return songs
    '''_extractplaylistname'''
    def _extractplaylistname(self, html_text):
        soup = BeautifulSoup(html_text, 'lxml')
        for sel in ['.work-page-header-wrapper h1', '#sticky .work-item-info h4', 'title']:
            node = soup.select_one(sel)
            if not (node := soup.select_one(sel)): continue
            text = ' '.join(node.stripped_strings)
            if sel == 'title': text = text.split(' - ')[0].strip()
            if text: return text
        return None
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        # init
        request_overrides = request_overrides or {}
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **request_overrides).url
        playlist_url = urlunsplit(urlsplit(playlist_url)._replace(query="", fragment=""))
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, STREETVOICE_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, playlist_result_first = [], 1, {}
        while True:
            request_page_url = playlist_url if page == 1 else f"{playlist_url}?page={page}"
            try: (resp := self.get(request_page_url, allow_redirects=True, **request_overrides)).raise_for_status()
            except Exception: break
            (playlist_result := {'name': self._extractplaylistname(resp.text), 'id': playlist_id})['songs'] = self._extractplaylistpagesongs(resp.text, "https://streetvoice.cn")
            if not playlist_result['songs']: break
            tracks_in_playlist.extend(playlist_result['songs']); page += 1
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
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
        playlist_name = safeextractfromdict(playlist_result_first, ['name'], None)
        song_infos = self._removeduplicates(song_infos=song_infos); work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        # return results
        return song_infos
            