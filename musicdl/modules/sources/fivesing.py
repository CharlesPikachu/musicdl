'''
Function:
    Implementation of FiveSingMusicClient: https://5sing.kugou.com/index.html
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
from bs4 import BeautifulSoup
from .base import BaseMusicClient
from pathvalidate import sanitize_filepath
from ..utils.hosts import FIVESING_MUSIC_HOSTS
from urllib.parse import urlencode, urlparse, urljoin
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import touchdir, legalizestring, byte2mb, resp2json, usesearchheaderscookies, safeextractfromdict, extractdurationsecondsfromlrc, seconds2hms, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester


'''FiveSingMusicClient'''
class FiveSingMusicClient(BaseMusicClient):
    source = 'FiveSingMusicClient'
    MUSIC_QUALITIES = ['sq', 'hq', 'lq']
    def __init__(self, **kwargs):
        super(FiveSingMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "Referer": "https://5sing.kugou.com/"}
        self.default_parse_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36", "Referer": "https://5sing.kugou.com/"}
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {'keyword': keyword, 'sort': 1, 'page': 1, 'filter': 0, 'type': 0}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'http://search.5sing.kugou.com/home/json?'
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
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('songId'))) or (not (song_type := search_result.get('typeEname'))): return song_info
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            (resp := self.get('http://mobileapi.5sing.kugou.com/song/getSongUrl', params={'songid': str(song_id), 'songtype': song_type}, **request_overrides)).raise_for_status()
            download_result: dict = resp2json(resp)
            for quality in FiveSingMusicClient.MUSIC_QUALITIES:
                download_url = safeextractfromdict(download_result, ['data', f'{quality}url'], '') or safeextractfromdict(download_result, ['data', f'{quality}url_backup'], '')
                if not download_url or not (str(download_url).startswith('http')): continue
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('songName')), singers=legalizestring(search_result.get('singer')), album='NULL', ext=safeextractfromdict(download_result, ['data', f'{quality}ext'], 'mp3'), 
                    file_size_bytes=safeextractfromdict(download_result, ['data', f'{quality}size'], 0), file_size=byte2mb(safeextractfromdict(download_result, ['data', f'{quality}size'], 0)), identifier=song_id, duration='-:-:-', lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'user', 'I'], None), 
                    download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                )
                song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                song_info.file_size = song_info.download_url_status['probe_status']['file_size']; song_info.ext = song_info.download_url_status['probe_status']['ext']
                if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
                if song_info.with_valid_download_url: break
        if not song_info.with_valid_download_url: return song_info
        # supplement lyric results
        params = {'songid': str(song_id), 'songtype': song_type, 'songfields': '', 'userfields': ''}
        try: (resp := self.get('http://mobileapi.5sing.kugou.com/song/newget', params=params, **request_overrides)).raise_for_status(); lyric = cleanlrc(safeextractfromdict((lyric_result := resp2json(resp)), ['data', 'dynamicWords'], '')) or 'NULL'
        except Exception: lyric_result, lyric = dict(), 'NULL'
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        song_info.album = legalizestring(safeextractfromdict(lyric_result, ['data', 'albumName'], None))
        song_info.cover_url = safeextractfromdict(lyric_result, ['data', 'user', 'I'], None)
        if not song_info.duration or song_info.duration == '-:-:-': song_info.duration = seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
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
            for search_result in resp2json(resp)['list']:
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
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        # init
        request_overrides = request_overrides or {}
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **request_overrides).url
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, FIVESING_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        try: playlist_result = resp2json(self.get(f'http://mobileapi.5sing.kugou.com/song/getsonglist?id={playlist_id}&songfields=ID,user', **request_overrides))
        except Exception: playlist_result = dict()
        soup, playlist_result['song_list'] = BeautifulSoup(self.get(playlist_url, **request_overrides).text, "lxml"), []
        for li in soup.select("ul.dj_songitems > li"):
            title_a, singer_a = li.select_one("span.s_title a.songlist_hits"), li.select_one("span.s_soner a")
            info_node = li.select_one("a.paly_btn[songinfo]") or li.select_one("a.add_btn[songinfo]")
            kind, song_id = ((m.group(1), m.group(2)) if (m := re.match(r"([a-z]+)\$(\d+)", str(info_node["songinfo"]))) else (None, None)) if info_node and info_node.has_attr("songinfo") else (None, None)
            coll_btn = li.select_one("a.coll_btn[songid]")
            song_id, kind = (coll_btn.get("songid"), {"1": "yc", "2": "fc", "3": "bz"}.get(coll_btn.get("songkind"))) if (not song_id) and coll_btn else (song_id, kind)
            playlist_result['song_list'].append({"songName": title_a.get_text(strip=True) if title_a else None, "songId": song_id, "typeEname": kind, "song_url": urljoin("http://5sing.kugou.com", title_a["href"]) if title_a and title_a.has_attr("href") else None, "singer": singer_a.get_text(strip=True) if singer_a else None, "singer_url": urljoin("http://5sing.kugou.com", singer_a["href"]) if singer_a and singer_a.has_attr("href") else None})
        tracks_in_playlist = playlist_result['song_list']
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
        playlist_name = safeextractfromdict(playlist_result, ['data', 'T'], None)
        song_infos = self._removeduplicates(song_infos=song_infos); work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        # return results
        return song_infos