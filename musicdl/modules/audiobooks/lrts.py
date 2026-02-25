'''
Function:
    Implementation of LRTSMusicClient: https://www.lrts.me/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
import math
from rich.progress import Progress
from urllib.parse import urlencode
from ..sources import BaseMusicClient
from ..utils import legalizestring, resp2json, seconds2hms, usesearchheaderscookies, usedownloadheaderscookies, safeextractfromdict, byte2mb, SongInfo


'''LRTSMusicClient'''
class LRTSMusicClient(BaseMusicClient):
    source = 'LRTSMusicClient'
    ALLOWED_SEARCH_TYPES = ['album', 'book']
    def __init__(self, **kwargs):
        self.allowed_search_types = list(set(kwargs.pop('allowed_search_types', LRTSMusicClient.ALLOWED_SEARCH_TYPES)))
        super(LRTSMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "accept-encoding": "gzip, deflate, br, zstd", 
            "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "cache-control": "max-age=0", "connection": "keep-alive", "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "host": "m.lrts.me", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"', "sec-fetch-dest": "document", "sec-fetch-mode": "navigate", "sec-fetch-site": "none", "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {"keyWord": keyword, "pageSize": "40", "pageNum": "1", "searchOption": "1"}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://m.lrts.me/ajax/search?'
        search_urls, page_size = [], max(self.search_size_per_page, 40)
        for search_type in LRTSMusicClient.ALLOWED_SEARCH_TYPES:
            if search_type not in self.allowed_search_types: continue
            default_rule_search_type, count = copy.deepcopy(default_rule), 0
            while self.search_size_per_source > count:
                page_rule = copy.deepcopy(default_rule_search_type)
                page_rule['pageSize'] = str(page_size)
                page_rule['pageNum'] = str(int(count // page_size) + 1)
                search_urls.append({search_type: base_url + urlencode(page_rule)})
                count += page_size
        # return
        return search_urls
    '''_parsebookwithofficialapiv1'''
    def _parsebookwithofficialapiv1(self, section_idx, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, book_id, song_id, song_info = request_overrides or {}, safeextractfromdict(search_result, ['book_info', 'id'], ''), search_result.get('id') or search_result.get('sectionId'), SongInfo(source=self.source)
        # parse
        try: (resp := self.get(f"https://m.lrts.me/ajax/getPlayPath?entityId={book_id}&entityType=3&opType=1&sections=[{section_idx}]&type=0&id={song_id}&section={section_idx}", **request_overrides)).raise_for_status(); download_result = resp2json(resp=resp)
        except Exception: download_result = {}
        download_url = safeextractfromdict(download_result, ['list', 0, 'path'], '')
        if not download_url or not download_url.startswith('http'):
            try: (resp := self.get(f"https://m.lrts.me/ajax/getListenPath?entityId={book_id}&entityType=3&opType=1&sections=[{section_idx}]&type=0&id={song_id}&section={section_idx}", **request_overrides)).raise_for_status(); download_result = resp2json(resp=resp)
            except Exception: download_result = {}
            download_url = safeextractfromdict(download_result, ['data', 'path'], '')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(safeextractfromdict(search_result, ['book_info', 'announcer'], None)), 
            album=legalizestring(safeextractfromdict(search_result, ['book_info', 'name'], None)), ext=download_url.split('?')[0].split('.')[-1] if '?' in download_url else 'm4a', file_size_bytes=float(search_result.get('size', 0) or 0), file_size=byte2mb(search_result.get('size', 0) or 0), 
            identifier=song_id, duration_s=int(float(search_result.get('length', 0.0) or 0.0)), duration=seconds2hms(int(float(search_result.get('length', 0.0) or 0.0))), lyric=None, cover_url=safeextractfromdict(search_result, ['book_info', 'cover'], None), 
            download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        # return
        return song_info
    '''_parsealbumwithofficialapiv1'''
    def _parsealbumwithofficialapiv1(self, section_idx, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, album_id, song_id, song_info = request_overrides or {}, safeextractfromdict(search_result, ['album_info', 'id'], ''), search_result.get('audioId') or search_result.get('sectionId'), SongInfo(source=self.source)
        # parse
        try: (resp := self.get(f"https://m.lrts.me/ajax/getPlayPath?entityId={album_id}&entityType=2&opType=1&sections=[{song_id}]&type=0", **request_overrides)).raise_for_status(); download_result = resp2json(resp=resp)
        except Exception: download_result = {}
        download_url = safeextractfromdict(download_result, ['list', 0, 'path'], '')
        if not download_url or not download_url.startswith('http'):
            try: (resp := self.get(f"https://m.lrts.me/ajax/getListenPath?entityId={album_id}&entityType=2&opType=1&sections=[{section_idx}]&type=0&id={song_id}&section={section_idx}", **request_overrides)).raise_for_status(); download_result = resp2json(resp=resp)
            except Exception: download_result = {}
            download_url = safeextractfromdict(download_result, ['data', 'path'], '')
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(safeextractfromdict(search_result, ['album_info', 'nickName'], None)), 
            album=legalizestring(safeextractfromdict(search_result, ['album_info', 'name'], None)), ext=download_url.split('?')[0].split('.')[-1] if '?' in download_url else 'm4a', file_size_bytes=float(search_result.get('size', 0) or 0), file_size=byte2mb(search_result.get('size', 0) or 0), 
            identifier=song_id, duration_s=int(float(search_result.get('length', 0.0) or 0.0)), duration=seconds2hms(int(float(search_result.get('length', 0.0) or 0.0))), lyric=None, cover_url=safeextractfromdict(search_result, ['album_info', 'cover'], None), 
            download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        # return
        return song_info
    '''_parsebybook'''
    def _parsebybook(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        request_overrides = request_overrides or {}
        for search_result in search_results['data']['bookResult']['list']:
            if (not isinstance(search_result, dict)) or ('id' not in search_result): continue
            download_results, tracks, page_size, unique_track_ids = [], [], 50, set()
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_results, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name', None)), 
                singers=legalizestring(search_result.get('announcer')), album=f"{safeextractfromdict(search_result, ['sections'], 0) or 0} Episodes", ext=None, file_size=None, 
                identifier=search_result['id'], duration='-:-:-', lyric=None, cover_url=search_result.get('cover', None), download_url=None, download_url_status={}, episodes=[],
            )
            num_pages = math.ceil(int(safeextractfromdict(search_result, ['sections'], 0) or 0) / page_size)
            download_book_pid = progress.add_task(f"{self.source}._parsebybook >>> (0/{num_pages}) pages downloaded in book {search_result['id']}", total=num_pages)
            for page_num_idx, page_num in enumerate(range(1, num_pages + 1)):
                if page_num_idx > 0:
                    progress.advance(download_book_pid, 1)
                    progress.update(download_book_pid, description=f"{self.source}._parsebybook >>> ({page_num_idx}/{num_pages}) pages downloaded in book {search_result['id']}")
                try: download_results.append(resp2json(self.get(f'https://m.lrts.me/ajax/getBookMenu?bookId={search_result["id"]}&pageNum={page_num}&pageSize={page_size}&sortType=0', **request_overrides)))
                except: continue
            progress.advance(download_book_pid, 1)
            progress.update(download_book_pid, description=f"{self.source}._parsebybook >>> ({page_num_idx+1}/{num_pages}) pages downloaded in book {search_result['id']}")
            for download_result in download_results:
                for track in (safeextractfromdict(download_result, ['list'], []) or []):
                    track_id = track.get('id') or track.get('sectionId')
                    if not track_id: continue
                    if track_id in unique_track_ids: continue
                    unique_track_ids.add(track_id)
                    tracks.append(track)
            download_book_pid = progress.add_task(f"{self.source}._parsebybook >>> (0/{len(tracks)}) episodes completed in book {search_result['id']}", total=len(tracks))
            for track_idx, track in enumerate(tracks):
                eps_id = track.get('id') or track.get('sectionId')
                eps_info = SongInfo(
                    raw_data={'search': track, 'book_info': copy.deepcopy(search_result), 'section_idx': track_idx + 1}, source=self.source, 
                    song_name=legalizestring(track.get('name')), singers=legalizestring(search_result.get('announcer')), 
                    album=legalizestring(search_result.get('name')), ext='m4a', file_size_bytes=float(track.get('size', 0) or 0), 
                    file_size=byte2mb(track.get('size', 0) or 0), identifier=eps_id, duration_s=int(float(track.get('length', 0.0) or 0.0)), 
                    duration=seconds2hms(int(float(track.get('length', 0.0) or 0.0))), lyric=None, cover_url=search_result.get('cover', None), 
                )
                song_info.episodes.append(eps_info)
                progress.advance(download_book_pid, 1)
                progress.update(download_book_pid, description=f"{self.source}._parsebybook >>> ({track_idx+1}/{len(tracks)}) episodes completed in book {search_result['id']}")
            if not song_info.episodes: continue
            try: song_info.duration_s = sum([eps.duration_s for eps in song_info.episodes]); song_info.duration = seconds2hms(song_info.duration_s)
            except Exception: pass
            try: song_info.file_size_bytes = sum([eps.file_size_bytes for eps in song_info.episodes]); song_info.file_size = byte2mb(song_info.file_size_bytes)
            except Exception: pass
            song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and (len(song_infos) >= self.search_size_per_page): break
        return song_infos
    '''_parsebyalbum'''
    def _parsebyalbum(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        request_overrides = request_overrides or {}
        for search_result in search_results['data']['albumResult']['list']:
            if (not isinstance(search_result, dict)) or ('id' not in search_result): continue
            download_results, tracks, unique_track_ids = [], [], set()
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_results, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name', None)), 
                singers=legalizestring(search_result.get('nickName')), album=f"{safeextractfromdict(search_result, ['sections'], 0) or 0} Episodes", ext=None, file_size=None, 
                identifier=search_result['id'], duration='-:-:-', lyric=None, cover_url=search_result.get('cover', None), download_url=None, download_url_status={}, episodes=[],
            )
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/1) pages downloaded in album {search_result['id']}", total=1)
            try: (resp := self.get(f'https://m.lrts.me/ajax/getAlbumAudios?ablumnId={search_result["id"]}&sortType=0')).raise_for_status()
            except Exception: continue
            download_results.append(resp2json(resp=resp))
            progress.advance(download_album_pid, 1)
            progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> (1/1) pages downloaded in album {search_result['id']}")
            for download_result in download_results:
                for track in (safeextractfromdict(download_result, ['list'], []) or []):
                    track_id = track.get('audioId') or track.get('sectionId')
                    if not track_id: continue
                    if track_id in unique_track_ids: continue
                    unique_track_ids.add(track_id)
                    tracks.append(track)
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/{len(tracks)}) episodes completed in album {search_result['id']}", total=len(tracks))
            for track_idx, track in enumerate(tracks):
                eps_id = track.get('audioId') or track.get('sectionId')
                eps_info = SongInfo(
                    raw_data={'search': track, 'album_info': copy.deepcopy(search_result), 'section_idx': track_idx + 1}, source=self.source, 
                    song_name=legalizestring(track.get('name')), singers=legalizestring(search_result.get('nickName')), 
                    album=legalizestring(search_result.get('name')), ext='m4a', file_size_bytes=float(track.get('size', 0) or 0), 
                    file_size=byte2mb(track.get('size', 0) or 0), identifier=eps_id, duration_s=int(float(track.get('length', 0.0) or 0.0)), 
                    duration=seconds2hms(int(float(track.get('length', 0.0) or 0.0))), lyric=None, cover_url=search_result.get('cover', None), 
                )
                song_info.episodes.append(eps_info)
                progress.advance(download_album_pid, 1)
                progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({track_idx+1}/{len(tracks)}) episodes completed in album {search_result['id']}")
            if not song_info.episodes: continue
            try: song_info.duration_s = sum([eps.duration_s for eps in song_info.episodes]); song_info.duration = seconds2hms(song_info.duration_s)
            except Exception: pass
            try: song_info.file_size_bytes = sum([eps.file_size_bytes for eps in song_info.episodes]); song_info.file_size = byte2mb(song_info.file_size_bytes)
            except Exception: pass
            song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and (len(song_infos) >= self.search_size_per_page): break
        return song_infos
    '''parseplaylist'''
    def parseplaylist(self, playlist_url):
        # init
        song_infos = []
        # bypass limits
        org_search_size_per_source = self.search_size_per_source
        org_search_size_per_page = self.search_size_per_page
        org_strict_limit = self.strict_limit_search_size_per_page
        self.search_size_per_source = 1000
        self.search_size_per_page = 1000
        self.strict_limit_search_size_per_page = False
        # parse
        if 'lrts.me/book/' in playlist_url:
            book_id = playlist_url.split('/book/')[-1].split('?')[0]
            try:
                resp = self.get(f'https://m.lrts.me/ajax/getBookDetail?bookId={book_id}')
                result = resp2json(resp)
                book_info = safeextractfromdict(result, ['data', 'bookDetail'], {})
                if not book_info: 
                    # Fallback to title from HTML
                    book_info = {'id': book_id, 'name': f'Book {book_id}'}
                    resp = self.get(f'https://www.lrts.me/book/{book_id}')
                    if resp.status_code == 200:
                        match = re.search(r'<title>(.*?)</title>', resp.text)
                        if match: book_info['name'] = match.group(1).split('-')[0].strip()
                else: book_info['id'] = book_id
                search_results = {'data': {'bookResult': {'list': [book_info]}}}
                with Progress() as progress:
                    song_infos = self._parsebybook(search_results, progress=progress)
            except: pass
        elif 'lrts.me/album/' in playlist_url:
            album_id = playlist_url.split('/album/')[-1].split('?')[0]
            try:
                album_name = f'Album {album_id}'
                resp = self.get(f'https://www.lrts.me/album/{album_id}')
                if resp.status_code == 200:
                    match = re.search(r'<title>(.*?)</title>', resp.text)
                    if match: album_name = match.group(1).split('-')[0].strip()
                resp = self.get(f'https://m.lrts.me/ajax/getAlbumAudios?ablumnId={album_id}&sortType=0')
                result = resp2json(resp)
                album_info = {
                    'id': album_id, 'name': album_name, 'sections': result.get('count', 0),
                }
                if result.get('list'): album_info['cover'] = result['list'][0].get('cover')
                search_results = {'data': {'albumResult': {'list': [album_info]}}}
                with Progress() as progress:
                    song_infos = self._parsebyalbum(search_results, progress=progress)
            except: pass
        # restore
        self.search_size_per_source = org_search_size_per_source
        self.search_size_per_page = org_search_size_per_page
        self.strict_limit_search_size_per_page = org_strict_limit
        # return
        return song_infos
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # if download_url is missing, try to fetch it
        if not song_info.download_url:
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Fetching URL)")
            try:
                section_idx = song_info.raw_data.get('section_idx', 1)
                search_result = song_info.raw_data.get('search', {})
                if 'book_info' in song_info.raw_data:
                    search_result['book_info'] = song_info.raw_data['book_info']
                    parsed_info = self._parsebookwithofficialapiv1(section_idx=section_idx, search_result=search_result, request_overrides=request_overrides)
                elif 'album_info' in song_info.raw_data:
                    search_result['album_info'] = song_info.raw_data['album_info']
                    parsed_info = self._parsealbumwithofficialapiv1(section_idx=section_idx, search_result=search_result, request_overrides=request_overrides)
                else:
                    parsed_info = None
                if parsed_info and parsed_info.download_url:
                    song_info.download_url = parsed_info.download_url
                    song_info.download_url_status = parsed_info.download_url_status
            except Exception as e:
                self.logger_handle.error(f'{self.source}._download >>> Failed to fetch URL for {song_info.song_name} (Error: {e})')
        # call super
        return super(LRTSMusicClient, self)._download(song_info, request_overrides, downloaded_song_infos, progress, song_progress_id)
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        (search_type, search_url), = search_url.items()
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)
            # --parse based on search type
            parsers = {'album': self._parsebyalbum, 'book': self._parsebybook}
            parsers[search_type](search_results, song_infos=song_infos, request_overrides=request_overrides, progress=progress)
            # --update progress
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Error: {err})")
        # return
        return song_infos
