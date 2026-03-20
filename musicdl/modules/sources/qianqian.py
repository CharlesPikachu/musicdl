'''
Function:
    Implementation of QianqianMusicClient: http://music.taihe.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import time
import copy
import hashlib
from .base import BaseMusicClient
from rich.progress import Progress
from pathvalidate import sanitize_filepath
from urllib.parse import urlencode, urlparse
from ..utils.hosts import QIANQIAN_MUSIC_HOSTS
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import touchdir, byte2mb, resp2json, seconds2hms, legalizestring, safeextractfromdict, usesearchheaderscookies, cookies2string, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester


'''QianqianMusicClient'''
class QianqianMusicClient(BaseMusicClient):
    source = 'QianqianMusicClient'
    APPID = '16073360'
    MUSIC_QUALITIES = ['3000', '320', '128', '64']
    def __init__(self, **kwargs):
        super(QianqianMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "accept": "*/*", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "referer": "https://music.91q.com/player", "sec-ch-ua-platform": "\"Windows\"",
            "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"", "sec-fetch-site": "same-origin", "sec-fetch-dest": "empty", "sec-ch-ua-mobile": "?0", "priority": "u=1, i", 
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "from": "web", "sec-fetch-mode": "cors", 
        }
        if self.default_search_cookies: self.default_search_headers['authorization'] = f"access_token {self.default_search_cookies.get('access_token', '')}"
        if self.default_search_cookies: self.default_search_headers['cookie'] = cookies2string(self.default_search_cookies)
        self.default_parse_headers = {
            "accept": "*/*", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "referer": "https://music.91q.com/player", "sec-ch-ua-platform": "\"Windows\"",
            "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"", "sec-fetch-site": "same-origin", "sec-fetch-dest": "empty", "sec-ch-ua-mobile": "?0", "priority": "u=1, i", 
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "from": "web", "sec-fetch-mode": "cors", 
        }
        if self.default_parse_cookies: self.default_parse_headers['authorization'] = f"access_token {self.default_parse_cookies.get('access_token', '')}"
        if self.default_parse_cookies: self.default_parse_headers['cookie'] = cookies2string(self.default_parse_cookies)
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
        if self.default_download_cookies: self.default_download_headers['authorization'] = f"access_token {self.default_download_cookies.get('access_token', '')}"
        if self.default_download_cookies: self.default_download_headers['cookie'] = cookies2string(self.default_download_cookies)
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_addsignandtstoparams'''
    def _addsignandtstoparams(self, params: dict):
        secret = '0b50b02fd0d73a9c4c8c3a781c30845f'
        params['timestamp'] = str(int(time.time()))
        keys = sorted(params.keys()); string = "&".join(f"{k}={params[k]}" for k in keys)
        params['sign'] = hashlib.md5((string + secret).encode('utf-8')).hexdigest()
        return params
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {'word': keyword, 'type': '1', 'pageNo': '1', 'pageSize': '10', 'appid': QianqianMusicClient.APPID}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://music.91q.com/v1/search?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['pageSize'] = page_size
            page_rule['pageNo'] = str(int(count // page_size) + 1)
            page_rule = self._addsignandtstoparams(params=page_rule)
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('TSID'))): return song_info
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            for rate in QianqianMusicClient.MUSIC_QUALITIES:
                params = self._addsignandtstoparams(params={'TSID': song_id, 'appid': QianqianMusicClient.APPID, 'rate': rate})
                try: (resp := self.get("https://music.91q.com/v1/song/tracklink", params=params, **request_overrides)).raise_for_status()
                except Exception: continue
                download_url = safeextractfromdict((download_result := resp2json(resp)), ['data', 'path'], '') or safeextractfromdict(download_result, ['data', 'trail_audio_info', 'path'], '')
                if not download_url or not str(download_url).startswith('http'): continue
                file_size_bytes, duration_in_secs = safeextractfromdict(download_result, ['data', 'size'], 0), safeextractfromdict(download_result, ['data', 'duration'], 0)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('artist', []) or []) if isinstance(singer, dict) and singer.get('name')])),
                    album=legalizestring(search_result.get('albumTitle', None)), ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=file_size_bytes, file_size=byte2mb(file_size_bytes), identifier=song_id, duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('pic'), 
                    download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                )
                song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
                if song_info.with_valid_download_url: break
        if not song_info.with_valid_download_url: return song_info
        # supplement lyric results
        try: (resp := self.get(search_result['lyric'], **request_overrides)).raise_for_status(); resp.encoding = 'utf-8'; lyric, lyric_result = cleanlrc(resp.text) or 'NULL', dict(lyric=resp.text)
        except Exception: lyric_result, lyric = dict(), 'NULL'
        if (song_info.singers == 'NULL') and lyric and (song_info.lyric not in {'NULL'}): song_info.singers = (m.group(1) if (m := re.search(r'\[ar:(.*?)\]', lyric)) else 'NULL')
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
            for search_result in resp2json(resp)['data']['typeTrack']:
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
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, QIANQIAN_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        tracks_in_playlist, page, playlist_result_first = [], 1, None
        while True:
            params = {'pageNo': page, 'pageSize': 50, 'appid': QianqianMusicClient.APPID, 'id': playlist_id}
            try: (resp := self.get(f"https://music.91q.com/v1/tracklist/info", params=self._addsignandtstoparams(params=params), **request_overrides)).raise_for_status()
            except Exception: break
            if (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['data', 'trackList'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['data', 'trackList'], [])); page += 1
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['data', 'trackCount'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["TSID"]: d for d in tracks_in_playlist}.values())
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
        playlist_name = safeextractfromdict(playlist_result_first, ['data', 'title'], None)
        song_infos = self._removeduplicates(song_infos=song_infos); work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        # return results
        return song_infos