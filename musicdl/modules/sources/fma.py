'''
Function:
    Implementation of FMAMusicClient: https://freemusicarchive.org/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import html
import json_repair
from contextlib import suppress
from .base import BaseMusicClient
from ..utils.hosts import FMA_MUSIC_HOSTS
from pathvalidate import sanitize_filepath
from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import urlencode, urlparse, urljoin, urlsplit, urlunsplit, parse_qs
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import legalizestring, usesearchheaderscookies, safeextractfromdict, useparseheaderscookies, obtainhostname, hostmatchessuffix, cookies2string, SongInfo, AudioLinkTester, LyricSearchClient, IOUtils, SongInfoUtils


'''FMAMusicClient'''
class FMAMusicClient(BaseMusicClient):
    source = 'FMAMusicClient'
    def __init__(self, **kwargs):
        super(FMAMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        if self.default_search_cookies: self.default_search_headers['cookie'] = cookies2string(self.default_search_cookies)
        self.default_parse_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7', 'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"', 'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Windows"', 'sec-fetch-dest': 'document', 'sec-fetch-mode': 'navigate', 'sec-fetch-site': 'same-origin', 'sec-fetch-user': '?1', 'upgrade-insecure-requests': '1', 'referer': 'https://freemusicarchive.org/', 
        }
        if self.default_parse_cookies: self.default_parse_headers['cookie'] = cookies2string(self.default_parse_cookies)
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        if self.default_download_cookies: self.default_download_cookies['cookie'] = cookies2string(self.default_download_cookies)
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"quicksearch": keyword, "pageSize": 200, "page": 1}).update(rule)
        # construct search urls
        base_url, search_urls, page_size, count = 'https://freemusicarchive.org/search/?', [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['pageSize'] = page_size
            page_rule['page'] = str(int(count // page_size) + 1)
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))): return song_info
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            (resp := self.get((url := search_result['url']), **request_overrides)).raise_for_status()
            img = ((soup := BeautifulSoup(resp.text, "lxml")).select_one(".w-full.h-80 img[src*='/image/'][src*='type=track']") or soup.select_one("img[src*='/image/'][src*='type=track']"))
            with suppress(Exception): download_result = {}; download_result = {**(json_repair.loads(soup.select_one("[data-track-info]").get("data-track-info")) or {}), "cover_url": urljoin(url, img["src"]) if img and img.get("src") else None}
            candidate_download_urls = [download_result.get('fileUrl'), search_result.get('fileUrl'), download_result.get('playbackUrl'), search_result.get('playbackUrl'), download_result.get('downloadUrl'), search_result.get('downloadUrl')]
            for download_url in [c for c in candidate_download_urls if c and str(c).startswith('http')]:
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or download_result.get('title')), singers=legalizestring(search_result.get('artistName') or download_result.get('artistName')), album=legalizestring(search_result.get('albumTitle') or download_result.get('albumTitle')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                    file_size=download_url_status['file_size'], identifier=song_id, duration_s=to_seconds_func(search_result.get('duration') or ''), duration=SongInfoUtils.seconds2hms(to_seconds_func(search_result.get('duration') or '')), lyric=None, cover_url=download_result.get('cover_url'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers
                )
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, page_no, search_result_idx = request_overrides or {}, int(float(parse_qs(urlparse(url=search_url).query, keep_blank_values=True).get('page')[0])), -1
        task_id = progress.add_task(f"{self.source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result_idx, search_result_item in enumerate(BeautifulSoup(resp.text, "lxml").select(".play-item[data-track-info]")):
                # --update progress
                progress.update(task_id, description=f'{self.source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --init song info
                with suppress(Exception): search_result = None; search_result = json_repair.loads(search_result_item["data-track-info"])
                if not search_result or not isinstance(search_result, dict) or not search_result.get('id'): continue
                search_result.update({"albumTitle": album.get_text(strip=True) if (album := search_result_item.select_one(".ptxt-album a")) else None, "albumUrl": album["href"] if album and album.has_attr("href") else None, "genres": [a.get_text(strip=True) for a in search_result_item.select(".ptxt-genre a")], "duration": duration.get_text(strip=True) if (duration := search_result_item.select_one("span.inline-flex.items-center")) else None})
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
    '''_parseplaylistpage'''
    def _parseplaylistpage(self, html_text: str):
        # init
        soup, tracks = BeautifulSoup(html_text, "html.parser"), []
        clean_text_func = lambda value: (None if not isinstance(value, str) else (lambda text: None if text in {"", "-", "—", "–"} else text)(re.sub(r"\s+", " ", value).strip()))
        tag_text_func = lambda tag: (clean_text_func(tag.get_text(" ", strip=True)) if isinstance(tag, Tag) else None)
        own_text_func = lambda tag: (clean_text_func(" ".join(str(child) for child in tag.contents if isinstance(child, NavigableString))) if isinstance(tag, Tag) else None)
        tag_attr_func = lambda tag, name: (clean_text_func(tag.get(name)) if isinstance(tag, Tag) and isinstance(name, str) else None)
        json_raw_func = lambda tag: (tag.get("data-track-info") if isinstance(tag, Tag) and isinstance(tag.get("data-track-info"), str) else None)
        duration_func = lambda track_item: (next((text for text in (tag_text_func(span) for span in track_item.find_all("span")) if isinstance(text, str) and re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", text)), None) if isinstance(track_item, Tag) else None)
        genres_func = lambda track_item: ([genre for genre in (tag_text_func(link) for link in track_item.select(".ptxt-genre a")) if isinstance(genre, str)] if isinstance(track_item, Tag) else [])
        album_title_func = lambda track_data, track_item: (clean_text_func(track_data.get("albumTitle")) if isinstance(track_data, dict) and clean_text_func(track_data.get("albumTitle")) else tag_text_func(track_item.select_one(".ptxt-album")) if isinstance(track_item, Tag) else None)
        playlist_name_func = lambda: (clean_text_func(tag_text_func(soup.title).replace(" - Free Music Archive", "")) if isinstance(tag_text_func(soup.title), str) else own_text_func(soup.select_one("h1")))
        # parse
        for track_item in soup.select(".play-item[data-track-info]"):
            with suppress(Exception): track_data = None; track_data = json_repair.loads(html.unescape(json_raw_func(track_item)))
            if not track_data or not isinstance(track_data, dict) or not track_data.get('id'): continue
            track_data.update({"album": album_title_func(track_data, track_item), "album_url": tag_attr_func(track_item.select_one(".ptxt-album a"), "href"), "duration": duration_func(track_item), "genres": genres_func(track_item)})
            tracks.append(track_data)
        # return
        return {"tracks": tracks, "playlist_name": playlist_name_func(), "playlist_id": tag_attr_func(soup.select_one('[data-type="playlist"][data-id]'), "data-id")}
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        # init
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **(request_overrides := dict(request_overrides or {}))).url
        playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, FMA_MUSIC_HOSTS)): return song_infos
        if not self.default_cookies: self.logger_handle.error(f'{self.source}.parseplaylist >>> "default_parse_cookies" are not configured, so musicdl does not have permission to parse FMA playlists, refer to "https://musicdl.readthedocs.io/en/latest/Clients.html#fmamusicclient".'); return song_infos
        # get tracks in playlist
        playlist_url = urlunsplit(((p := urlsplit((playlist_url).strip())).scheme, p.netloc, p.path.rstrip("/") or "/", "", ""))
        tracks_in_playlist, page, playlist_result_first = [], 1, None
        while True:
            with suppress(Exception): (resp := self.get(playlist_url, params={'page': page, 'pageSize': 200}, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') or (not safeextractfromdict((playlist_result := self._parseplaylistpage(resp.text)), ['tracks'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['tracks'], [])); page += 1; del resp
            if not playlist_result_first: playlist_result_first, playlist_id = copy.deepcopy(playlist_result), playlist_result['playlist_id']
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
        playlist_name = legalizestring(safeextractfromdict(playlist_result, ['playlist_name'], None) or f"playlist-{playlist_id}")
        song_infos, work_dir = self._removeduplicates(song_infos=song_infos), self._constructuniqueworkdir(keyword=playlist_name)
        for song_info in song_infos:
            song_info.work_dir, episodes = work_dir, song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, f"{song_info.song_name} - {song_info.singers}")); IOUtils.touchdir(eps_info.work_dir)
        # return results
        return song_infos