'''
Function:
    Implementation of LRTSMusicClient: https://www.lrts.me/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
import math
from itertools import chain
from contextlib import suppress
from rich.progress import Progress
from typing_extensions import Unpack
from urllib.parse import urlencode, urlparse, parse_qs
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, SongInfo, SongInfoUtils, AudioLinkTester


'''LRTSMusicClient'''
class LRTSMusicClient(BaseMusicClient):
    source = 'LRTSMusicClient'
    ALLOWED_SEARCH_TYPES = ['album', 'book']
    def __init__(self, allowed_search_types: list = None, **kwargs: Unpack[BaseMusicClientKwargs]):
        self.allowed_search_types = list(set(allowed_search_types or LRTSMusicClient.ALLOWED_SEARCH_TYPES))
        super(LRTSMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "cache-control": "max-age=0", "connection": "keep-alive", "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "host": "m.lrts.me", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"', "sec-fetch-dest": "document", "sec-fetch-mode": "navigate", "sec-fetch-site": "none", "sec-fetch-user": "?1", "upgrade-insecure-requests": "1", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"keyWord": keyword, "pageSize": "40", "pageNum": "1", "searchOption": "1"}).update(rule)
        # construct search urls
        search_urls, page_size, base_url = [], max(self.search_size_per_page, 40), 'https://m.lrts.me/ajax/search?'
        for search_type in LRTSMusicClient.ALLOWED_SEARCH_TYPES:
            if search_type not in self.allowed_search_types: continue
            default_rule_search_type, count = copy.deepcopy(default_rule), 0
            while self.search_size_per_source > count:
                (page_rule := copy.deepcopy(default_rule_search_type))['pageSize'] = str(page_size)
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
        (resp := self.get(f"https://m.lrts.me/ajax/getPlayPath?entityId={book_id}&entityType=3&opType=1&sections=[{section_idx}]&type=0&id={song_id}&section={section_idx}", **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['list', 0, 'path'], '')
        if not download_url or not str(download_url).startswith('http'): (resp := self.get(f"https://m.lrts.me/ajax/getListenPath?entityId={book_id}&entityType=3&opType=1&sections=[{section_idx}]&type=0&id={song_id}&section={section_idx}", **request_overrides)).raise_for_status(); download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'path'], '')
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(safeextractfromdict(search_result, ['book_info', 'announcer'], None)), album=legalizestring(safeextractfromdict(search_result, ['book_info', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('length', 0.0) or 0.0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('length', 0.0) or 0.0))), lyric=None, cover_url=safeextractfromdict(search_result, ['book_info', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsealbumwithofficialapiv1'''
    def _parsealbumwithofficialapiv1(self, section_idx, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, album_id, song_id, song_info = request_overrides or {}, safeextractfromdict(search_result, ['album_info', 'id'], ''), search_result.get('audioId') or search_result.get('sectionId'), SongInfo(source=self.source)
        # parse
        (resp := self.get(f"https://m.lrts.me/ajax/getPlayPath?entityId={album_id}&entityType=2&opType=1&sections=[{song_id}]&type=0", **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['list', 0, 'path'], '')
        if not download_url or not str(download_url).startswith('http'): (resp := self.get(f"https://m.lrts.me/ajax/getListenPath?entityId={album_id}&entityType=2&opType=1&sections=[{section_idx}]&type=0&id={song_id}&section={section_idx}", **request_overrides)).raise_for_status(); download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'path'], '')
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(safeextractfromdict(search_result, ['album_info', 'nickName'], None)), album=legalizestring(safeextractfromdict(search_result, ['album_info', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('length', 0.0) or 0.0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('length', 0.0) or 0.0))), lyric=None, cover_url=safeextractfromdict(search_result, ['album_info', 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
        )
        # return
        return song_info
    '''_parsebybook'''
    def _parsebybook(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None, main_page_no: int = 1):
        # parse books one by one
        for search_result in search_results['data']['bookResult']['list']:
            if (not isinstance(search_result, dict)) or (not (book_id := search_result.get('id'))): continue
            # --basic song info class
            download_results, tracks, page_size, unique_track_ids, request_overrides = [], [], 50, set(), dict(request_overrides or {})
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_results, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(search_result.get('announcer')), album=f"{safeextractfromdict(search_result, ['sections'], 0) or 0} Episodes", 
                ext=None, file_size_bytes=None, file_size=None, identifier=book_id, duration_s=None, duration='-:-:-', lyric=None, cover_url=search_result.get('cover'), download_url=None, download_url_status={}, episodes=[],
            )
            # --download all pages for further processing
            num_pages = math.ceil(int(safeextractfromdict(search_result, ['sections'], 0) or 0) / page_size)
            download_book_pid = progress.add_task(f"{self.source}.p{main_page_no}._parsebybook >>> (0/{num_pages}) pages downloaded in book {book_id}", total=num_pages)
            for page_num_idx, page_num in enumerate(range(1, num_pages + 1)):
                if page_num_idx > 0: progress.advance(download_book_pid, 1); progress.update(download_book_pid, description=f"{self.source}.p{main_page_no}._parsebybook >>> ({page_num_idx}/{num_pages}) pages downloaded in book {book_id}")
                with suppress(Exception): download_results.append(resp2json(self.get(f'https://m.lrts.me/ajax/getBookMenu?bookId={book_id}&pageNum={page_num}&pageSize={page_size}&sortType=0', **request_overrides)))
            progress.advance(download_book_pid, 1); progress.update(download_book_pid, description=f"{self.source}.p{main_page_no}._parsebybook >>> ({page_num_idx+1}/{num_pages}) pages downloaded in book {book_id}")
            # --parse tracks in this album one by one
            for track in chain.from_iterable((safeextractfromdict(download_result, ['list'], []) or []) for download_result in download_results):
                if (not isinstance(track, dict)) or (not track.get('id')) or (track.get('id') in unique_track_ids): continue
                unique_track_ids.add(track.get('id')); tracks.append(track)
            download_book_pid = progress.add_task(f"{self.source}.p{main_page_no}._parsebybook >>> (0/{len(tracks)}) episodes completed in book {book_id}", total=len(tracks))
            for track_idx, track in enumerate(tracks):
                if track_idx > 0: progress.advance(download_book_pid, 1); progress.update(download_book_pid, description=f"{self.source}.p{main_page_no}._parsebybook >>> ({track_idx}/{len(tracks)}) episodes completed in book {book_id}")
                eps_info, track['book_info'] = SongInfo(source=self.source), copy.deepcopy(search_result)
                with suppress(Exception): eps_info = self._parsebookwithofficialapiv1(section_idx=track_idx+1, search_result=track, request_overrides=request_overrides)
                if not eps_info.with_valid_download_url or eps_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                if eps_info.with_valid_download_url: song_info.episodes.append(eps_info)
            progress.advance(download_book_pid, 1); progress.update(download_book_pid, description=f"{self.source}.p{main_page_no}._parsebybook >>> ({track_idx+1}/{len(tracks)}) episodes completed in book {book_id}")
            if len(song_info.episodes) == 0 or not song_info.with_valid_download_url: continue
            # --post processing
            with suppress(Exception): song_info.duration_s = sum([float(eps.duration_s) for eps in song_info.episodes]); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
            with suppress(Exception): song_info.file_size_bytes = sum([float(eps.file_size_bytes) for eps in song_info.episodes]); song_info.file_size = SongInfoUtils.byte2mb(song_info.file_size_bytes)
            if song_info.with_valid_download_url: song_info.album = f"{len(song_info.episodes)} Episodes"; song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        # return
        return song_infos
    '''_parsebyalbum'''
    def _parsebyalbum(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None, main_page_no: int = 1):
        # parse albums one by one
        for search_result in search_results['data']['albumResult']['list']:
            if (not isinstance(search_result, dict)) or (not (album_id := search_result.get('id'))): continue
            # --basic song info class
            download_results, tracks, unique_track_ids, request_overrides = [], [], set(), dict(request_overrides or {})
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_results, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(search_result.get('nickName')), album=f"{safeextractfromdict(search_result, ['sections'], 0) or 0} Episodes", 
                ext=None, file_size_bytes=None, file_size=None, identifier=album_id, duration_s=None, duration='-:-:-', lyric=None, cover_url=search_result.get('cover'), download_url=None, download_url_status={}, episodes=[],
            )
            # --download all pages for further processing
            download_album_pid = progress.add_task(f"{self.source}.p{main_page_no}._parsebyalbum >>> (0/1) pages downloaded in album {album_id}", total=1)
            with suppress(Exception): resp = None; (resp := self.get(f'https://m.lrts.me/ajax/getAlbumAudios?ablumnId={album_id}&sortType=0')).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
            download_results.append(resp2json(resp=resp)); progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}.p{main_page_no}._parsebyalbum >>> (1/1) pages downloaded in album {album_id}")
            # --parse tracks in this album one by one
            for track in chain.from_iterable((safeextractfromdict(download_result, ['list'], []) or []) for download_result in download_results):
                if (not isinstance(track, dict)) or (not track.get('audioId')) or (track.get('audioId') in unique_track_ids): continue
                unique_track_ids.add(track.get('audioId')); tracks.append(track)
            download_album_pid = progress.add_task(f"{self.source}.p{main_page_no}._parsebyalbum >>> (0/{len(tracks)}) episodes completed in album {album_id}", total=len(tracks))
            for track_idx, track in enumerate(tracks):
                if track_idx > 0: progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}.p{main_page_no}._parsebyalbum >>> ({track_idx}/{len(tracks)}) episodes completed in album {album_id}")
                eps_info, track['album_info'] = SongInfo(source=self.source), copy.deepcopy(search_result)
                with suppress(Exception): eps_info = self._parsealbumwithofficialapiv1(section_idx=track_idx+1, search_result=track, request_overrides=request_overrides)
                if not eps_info.with_valid_download_url or eps_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                if eps_info.with_valid_download_url: song_info.episodes.append(eps_info)
            progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}.p{main_page_no}._parsebyalbum >>> ({track_idx+1}/{len(tracks)}) episodes completed in album {album_id}")
            if len(song_info.episodes) == 0 or not song_info.with_valid_download_url: continue
            # --post processing
            with suppress(Exception): song_info.duration_s = sum([float(eps.duration_s) for eps in song_info.episodes]); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
            with suppress(Exception): song_info.file_size_bytes = sum([float(eps.file_size_bytes) for eps in song_info.episodes]); song_info.file_size = SongInfoUtils.byte2mb(song_info.file_size_bytes)
            if song_info.with_valid_download_url: song_info.album = f"{len(song_info.episodes)} Episodes"; song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        # return
        return song_infos
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, search_type, search_url = request_overrides or {}, list(search_url.keys())[0], list(search_url.values())[0]
        page_no = int(float(parse_qs(urlparse(url=str(search_url)).query, keep_blank_values=True).get('pageNum')[0]))
        task_id = progress.add_task(f"{self.source}.{search_type}._search >>> Start to process search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            # --parse based on search type
            parsers = {'album': self._parsebyalbum, 'book': self._parsebybook}
            parsers[search_type](resp2json(resp), song_infos=song_infos, request_overrides=request_overrides, progress=progress, main_page_no=page_no)
            # --update progress
            progress.update(task_id, description=f'{self.source}.{search_type}._search >>> All search results processed on page {page_no}', total=len(song_infos), completed=len(song_infos))
        # failure
        except Exception as err:
            progress.update(task_id, description=f'{self.source}.{search_type}._search >>> {keyword} on page {page_no} (Error: {err})')
            self.logger_handle.error(f'{self.source}.{search_type}._search >>> {keyword} on page {page_no} (Error: {err})', disable_print=self.disable_print)
        # return
        return song_infos