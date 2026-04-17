'''
Function:
    Implementation of QingtingMusicClient: https://m.qingting.fm/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
import hmac
import math
import hashlib
from itertools import chain
from contextlib import suppress
from rich.progress import Progress
from typing import Any, Dict, List
from ..sources import BaseMusicClient
from urllib.parse import urlencode, urlparse, parse_qs
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, SongInfo, SongInfoUtils, AudioLinkTester


'''QingtingMusicClient'''
class QingtingMusicClient(BaseMusicClient):
    source = 'QingtingMusicClient'
    HMAC_KEY = "99@b8#571(bb38_b"
    DEVICE_ID = "66f6e3b560ad8876e52e6e67ee535c5c"
    ALLOWED_SEARCH_TYPES = ['album', 'track']
    def __init__(self, **kwargs):
        self.allowed_search_types = list(set(kwargs.pop('allowed_search_types', QingtingMusicClient.ALLOWED_SEARCH_TYPES)))
        super(QingtingMusicClient, self).__init__(**kwargs)
        if self.default_search_cookies: assert ("qingting_id" in self.default_search_cookies) and (("access_token" in self.default_search_cookies) or ("refresh_token" in self.default_search_cookies)), '"qingting_id", "access_token" and "refresh_token" should be configured, refer to "https://musicdl.readthedocs.io/en/latest/Quickstart.html#qingtingfm-audio-radio-download"'
        if self.default_download_cookies: assert ("qingting_id" in self.default_download_cookies) and (("access_token" in self.default_download_cookies) or ("refresh_token" in self.default_download_cookies)), '"qingting_id", "access_token" and "refresh_token" should be configured, refer to "https://musicdl.readthedocs.io/en/latest/Quickstart.html#qingtingfm-audio-radio-download"'
        self.default_search_headers = {"User-Agent": "QingTing-iOS/10.7.9.0 com.Qting.QTTour Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148", "QT-App-Version": "10.7.9.0"}
        self.default_download_headers = {"User-Agent": "QingTing-iOS/10.7.9.0 com.Qting.QTTour Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148", "QT-App-Version": "10.7.9.0"}
        self.default_headers = self.default_search_headers
        self.auth_info = copy.deepcopy(self.default_search_cookies or self.default_download_cookies)
        self.default_search_cookies = {}; self.default_download_cookies = {}; self._initsession()
    '''_checkauth'''
    def _checkauth(self, request_overrides: dict = None):
        if ("access_token" in self.auth_info) or ("qingting_id" not in self.auth_info or "refresh_token" not in self.auth_info): return self.auth_info
        qingting_id, refresh_token = self.auth_info['qingting_id'], self.auth_info['refresh_token']
        (resp := self.post("https://user.qtfm.cn/u2/api/v4/auth", headers={"Content-Type": "application/x-www-form-urlencoded"}, data={"refresh_token": refresh_token, "qingting_id": qingting_id, "device_id": QingtingMusicClient.DEVICE_ID, "grant_type": "refresh_token"}, **dict(request_overrides or {}))).raise_for_status()
        self.auth_info = copy.deepcopy((auth_info := resp2json(resp)['data']))
        return auth_info
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init, search rules: sort_type should be in {"0", "1", "2"} >>> {Comprehensive Sorting, Most Popular, Latest Updates}; include should be in {"channel_ondemand", "channel_live", "program_ondemand", "people_podcaster", "all"}
        rule, request_overrides = rule or {}, request_overrides or {}; self._checkauth(request_overrides=request_overrides)
        (default_rule := {"k": keyword, "sort_type": '0', "page": "1", "include": "channel_ondemand", "pagesize": "30", "k_src": "direct"}).update(rule)
        # construct search urls
        search_urls, page_size, base_url = [], self.search_size_per_page, 'https://app.qtfm.cn/m-bff/v1/search/result?'
        for search_type in QingtingMusicClient.ALLOWED_SEARCH_TYPES:
            if search_type not in self.allowed_search_types: continue
            (default_rule_search_type := copy.deepcopy(default_rule))['include'], count = {"album": "channel_ondemand", "track": "program_ondemand"}[search_type], 0
            while self.search_size_per_source > count:
                (page_rule := copy.deepcopy(default_rule_search_type))['pagesize'] = str(page_size)
                page_rule['page'] = str(int(count // page_size) + 1)
                search_urls.append(base_url + urlencode(page_rule))
                count += page_size
        # return
        return search_urls
    '''_getchannelinfo'''
    def _getchannelinfo(self, channel_id: str, request_overrides: dict = None) -> Dict[str, Any]:
        (resp := self.get(f"https://app.qtfm.cn/m-bff/v2/channel/{channel_id}", **dict(request_overrides or {}))).raise_for_status()
        return resp2json(resp=resp)
    '''_listpageprograms'''
    def _listpageprograms(self, channel_id: str, page: int, page_size: int, request_overrides: dict = None) -> List[Dict[str, Any]]:
        (resp := self.get(f"https://app.qtfm.cn/m-bff/v2/channel/{channel_id}/programs", params={"order": "asc", "pagesize": str(page_size), "curpage": str(page)}, **dict(request_overrides or {}))).raise_for_status()
        return resp2json(resp=resp)
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info, app_url = request_overrides or {}, search_result.get('id') or search_result.get('Id'), SongInfo(source=self.source), search_result.get('url')
        hmac_md5_hex_func = lambda key, msg: hmac.new(str(key).encode("utf-8"), str(msg).encode("utf-8"), hashlib.md5).hexdigest()
        # parse
        parsed_app_url_params = parse_qs(urlparse(str(app_url)).query, keep_blank_values=True)
        channel_id, program_id = parsed_app_url_params.get('channel_id')[0], (parsed_app_url_params.get('program_id') or [song_id])[0]
        assert str(song_id) == str(program_id), '"song_id" and "app_url" are not synchronized'
        sign = hmac_md5_hex_func(QingtingMusicClient.HMAC_KEY, (path_query := f"/m-bff/v1/audiostreams/channel/{channel_id}/program/{program_id}?access_token={self.auth_info.get('access_token', '')}&device_id={QingtingMusicClient.DEVICE_ID}&qingting_id={self.auth_info.get('qingting_id', '')}&type=play"))
        (resp := self.get(f"https://app.qtfm.cn{path_query}&sign={sign}", **request_overrides)).raise_for_status()
        candidate_editions: list[dict] = (safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'editions'], []) or []) + (safeextractfromdict(download_result, ['data', 'backup_editions'], []) or [])
        with suppress(Exception): search_result['channel_info'] = self._getchannelinfo(channel_id, request_overrides) if 'channel_info' not in search_result else search_result['channel_info']
        for edition in sorted(candidate_editions, key=lambda x: (x.get('size', 0), x.get('bitrate', 0)), reverse=True):
            if not isinstance(edition, dict) or not edition.get('urls'): continue
            edition['urls'] = [edition.get('urls')] if isinstance(edition.get('urls'), str) else edition.get('urls')
            candidate_download_urls = [url for url in (edition.get('urls') or []) if url and str(url).startswith('http')]
            download_url, download_url_status = next(((download_url, result) for download_url in candidate_download_urls if (result := self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)).get("ok") is True), (None, None))
            if download_url is None or download_url_status is None or not download_url_status.get('ok'): continue
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(', '.join([singer.get('nick_name') for singer in (safeextractfromdict(search_result, ['channel_info', 'data', 'podcasters'], []) or []) if isinstance(singer, dict) and singer.get('nick_name')])), album=legalizestring(safeextractfromdict(search_result, ['channel_info', 'data', 'title'], None) or search_result.get('desc')), 
                ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(search_result.get('duration', 0) or 0)), duration=SongInfoUtils.seconds2hms(int(float(search_result.get('duration', 0) or 0))), lyric=None, cover_url=search_result.get('cover'), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and (song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): break
        # return
        return song_info
    '''_parsebytrack'''
    def _parsebytrack(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        for search_result in search_results['data']['data']:
            if (not isinstance(search_result, dict)) or (not search_result.get('id')) or (search_result.get('type') not in {'program'}): continue
            song_info, request_overrides = SongInfo(source=self.source), request_overrides or {}
            for parser in [self._parsewithofficialapiv1]:
                with suppress(Exception): song_info = parser(search_result=search_result, request_overrides=dict(request_overrides or {}))
                if song_info.with_valid_download_url and (song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): break
            if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
            if song_info.with_valid_download_url: song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        return song_infos
    '''_parsebyalbum'''
    def _parsebyalbum(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        for search_result in search_results['data']['data']:
            if (not isinstance(search_result, dict)) or (not (album_id := search_result.get('id'))) or (search_result.get('type') not in {'channel_ondemand'}): continue
            download_results, page_size, tracks, unique_track_ids, request_overrides = [], 100, [], set(), request_overrides or {}
            with suppress(Exception): search_result['channel_info'] = self._getchannelinfo(album_id, request_overrides) if 'channel_info' not in search_result else search_result['channel_info']
            num_episodes = safeextractfromdict(search_result, ['channel_info', 'data', 'program_count'], 0) or 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_results, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['podcaster', 'name'], None)), 
                album=f"{num_episodes} Episodes", ext=None, file_size_bytes=None, file_size=None, identifier=album_id, duration_s=None, duration='-:-:-', lyric=None, cover_url=search_result.get('cover'), download_url=None, download_url_status={}, episodes=[],
            )
            num_pages = math.ceil(float(safeextractfromdict(search_result, ['channel_info', 'data', 'program_count'], 0) or 0) / page_size)
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/{num_pages}) pages downloaded in album {album_id}", total=num_pages)
            for page_num_idx, page_num in enumerate(range(1, num_pages + 1)):
                if page_num_idx > 0: progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({page_num_idx}/{num_pages}) pages downloaded in album {album_id}")
                with suppress(Exception): download_results.append(self._listpageprograms(album_id, page=page_num, page_size=page_size, request_overrides=request_overrides))
            progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({page_num_idx+1}/{num_pages}) pages downloaded in album {album_id}")
            for track in chain.from_iterable((safeextractfromdict(download_result, ['data', 'programs'], []) or []) for download_result in download_results):
                if (not isinstance(track, dict)) or (not track.get('id')) or track.get('id') in unique_track_ids: continue
                unique_track_ids.add(track.get('id')); tracks.append(track)
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/{len(tracks)}) episodes completed in album {album_id}", total=len(tracks))
            for track_idx, track in enumerate(tracks):
                if track_idx > 0: progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({track_idx}/{len(tracks)}) episodes completed in album {album_id}")
                eps_info, track['channel_info'] = SongInfo(source=self.source), search_result.get('channel_info', {}) or {}
                track['url'] = f"qingtingfm://app.qingting.fm/playingview?type=ondemand&channel_id={album_id}&program_id={track['id']}"
                for parser in [self._parsewithofficialapiv1]:
                    with suppress(Exception): eps_info = parser(search_result=track, request_overrides=request_overrides)
                    if eps_info.with_valid_download_url and (eps_info.ext in AudioLinkTester.VALID_AUDIO_EXTS): break
                if not eps_info.with_valid_download_url or eps_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                if eps_info.with_valid_download_url: song_info.episodes.append(eps_info)
            progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({track_idx+1}/{len(tracks)}) episodes completed in album {album_id}")
            if len(song_info.episodes) == 0 or not song_info.with_valid_download_url: continue
            with suppress(Exception): song_info.duration_s = sum([float(eps.duration_s) for eps in song_info.episodes]); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
            with suppress(Exception): song_info.file_size_bytes = sum([float(eps.file_size_bytes) for eps in song_info.episodes]); song_info.file_size = SongInfoUtils.byte2mb(song_info.file_size_bytes)
            if song_info.with_valid_download_url: song_info.album = f"{len(song_info.episodes)} Episodes"; song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        return song_infos
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            # --parse based on search type
            search_type = parse_qs(urlparse(search_url).query, keep_blank_values=True).get('include')[0]
            parsers = {'channel_ondemand': self._parsebyalbum, 'program_ondemand': self._parsebytrack}
            parsers[search_type](resp2json(resp), song_infos=song_infos, request_overrides=request_overrides, progress=progress)
            # --update progress
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Error: {err})")
            self.logger_handle.error(f"{self.source}._search >>> {search_url} (Error: {err})", disable_print=self.disable_print)
        # return
        return song_infos