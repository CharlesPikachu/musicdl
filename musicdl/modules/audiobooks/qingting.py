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
from rich.progress import Progress
from typing import Any, Dict, List
from ..sources import BaseMusicClient
from urllib.parse import urlencode, urlparse, parse_qs
from ..utils import legalizestring, resp2json, seconds2hms, usesearchheaderscookies, safeextractfromdict, byte2mb, SongInfo


'''QingtingMusicClient'''
class QingtingMusicClient(BaseMusicClient):
    source = 'QingtingMusicClient'
    HMAC_KEY = "99@b8#571(bb38_b"
    DEVICE_ID = "66f6e3b560ad8876e52e6e67ee535c5c"
    ALLOWED_SEARCH_TYPES = ['album', 'track']
    def __init__(self, **kwargs):
        self.allowed_search_types = list(set(kwargs.pop('allowed_search_types', QingtingMusicClient.ALLOWED_SEARCH_TYPES)))
        super(QingtingMusicClient, self).__init__(**kwargs)
        if self.default_cookies: assert ("qingting_id" in self.default_cookies) and (("access_token" in self.default_cookies) or ("refresh_token" in self.default_cookies)), '"qingting_id", "access_token" and "refresh_token" should be configured, refer to "https://musicdl.readthedocs.io/zh/latest/Quickstart.html#qingtingfm-audio-radio-download"'
        self.default_search_headers = {"User-Agent": "QingTing-iOS/10.7.9.0 com.Qting.QTTour Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148", "QT-App-Version": "10.7.9.0"}
        self.default_download_headers = {"User-Agent": "QingTing-iOS/10.7.9.0 com.Qting.QTTour Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148", "QT-App-Version": "10.7.9.0"}
        self.default_headers = self.default_search_headers
        self.auth_info = copy.deepcopy(self.default_search_cookies or self.default_download_cookies)
        self.default_search_cookies = {}
        self.default_download_cookies = {}
        self._initsession()
    '''_auth'''
    def _auth(self, request_overrides: dict = None):
        request_overrides = request_overrides or {}
        qingting_id, refresh_token = self.auth_info['qingting_id'], self.auth_info['refresh_token']
        resp = self.post("https://user.qtfm.cn/u2/api/v4/auth", headers={"Content-Type": "application/x-www-form-urlencoded"}, data={"refresh_token": refresh_token, "qingting_id": qingting_id, "device_id": QingtingMusicClient.DEVICE_ID, "grant_type": "refresh_token"}, **request_overrides)
        resp.raise_for_status()
        auth_info = resp2json(resp)['data']
        self.auth_info = copy.deepcopy(auth_info)
        return auth_info
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        if self.auth_info and ("access_token" not in self.auth_info): self._auth()
        # search rules: sort_type should be in {"0", "1", "2"} >>> {Comprehensive Sorting, Most Popular, Latest Updates}; include should be in {"channel_ondemand", "channel_live", "program_ondemand", "people_podcaster", "all"}
        default_rule = {"k": keyword, "sort_type": '0', "page": "1", "include": "channel_ondemand", "pagesize": "30", "k_src": "direct"}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://app.qtfm.cn/m-bff/v1/search/result?'
        search_urls, page_size = [], self.search_size_per_page
        for search_type in QingtingMusicClient.ALLOWED_SEARCH_TYPES:
            if search_type not in self.allowed_search_types: continue
            default_rule_search_type = copy.deepcopy(default_rule)
            default_rule_search_type['include'], count = {"album": "channel_ondemand", "track": "program_ondemand"}[search_type], 0
            while self.search_size_per_source > count:
                page_rule = copy.deepcopy(default_rule_search_type)
                page_rule['pagesize'] = str(page_size)
                page_rule['page'] = str(int(count // page_size) + 1)
                search_urls.append(base_url + urlencode(page_rule))
                count += page_size
        # return
        return search_urls
    '''_fetchchannelinfo'''
    def _fetchchannelinfo(self, channel_id: str, request_overrides: dict = None) -> Dict[str, Any]:
        request_overrides = request_overrides or {}
        url = f"https://app.qtfm.cn/m-bff/v2/channel/{channel_id}"
        resp = self.get(url, **request_overrides)
        resp.raise_for_status()
        channel_info = resp2json(resp=resp)
        return channel_info
    '''_listpageprograms'''
    def _listpageprograms(self, channel_id: str, page: int, page_size: int, request_overrides: dict = None) -> List[Dict[str, Any]]:
        request_overrides = request_overrides or {}
        url = f"https://app.qtfm.cn/m-bff/v2/channel/{channel_id}/programs"
        resp = self.get(url, params={"order": "asc", "pagesize": str(page_size), "curpage": str(page)}, **request_overrides)
        resp.raise_for_status()
        programs = resp2json(resp=resp)
        return programs
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info, app_url = request_overrides or {}, search_result.get('id') or search_result.get('Id'), SongInfo(source=self.source), search_result.get('url')
        if not song_id or not app_url: return song_info
        hmac_md5_hex_func = lambda key, msg: hmac.new(str(key).encode("utf-8"), str(msg).encode("utf-8"), hashlib.md5).hexdigest()
        # parse
        parsed_app_url_params = parse_qs(urlparse(str(app_url)).query, keep_blank_values=True)
        channel_id, program_id = parsed_app_url_params.get('channel_id')[0], (parsed_app_url_params.get('program_id') or [song_id])[0]
        assert str(song_id) == str(program_id), 'song_id and app_url are not synchronized'
        path_query = f"/m-bff/v1/audiostreams/channel/{channel_id}/program/{program_id}?access_token={self.auth_info.get('access_token', '')}&device_id={QingtingMusicClient.DEVICE_ID}&qingting_id={self.auth_info.get('qingting_id', '')}&type=play"
        sign = hmac_md5_hex_func(QingtingMusicClient.HMAC_KEY, path_query)
        resp = self.get(f"https://app.qtfm.cn{path_query}&sign={sign}", **request_overrides)
        resp.raise_for_status()
        download_result = resp2json(resp=resp)
        if 'channel_info' not in search_result:
            try: search_result['channel_info'] = self._fetchchannelinfo(channel_id, request_overrides)
            except Exception: pass
        candidate_editions: list[dict] = sorted(download_result['data']['editions'] + (download_result['data'].get('backup_editions') if isinstance(download_result['data'].get('backup_editions'), list) else []), key=lambda x: (x.get('size', 0), x.get('bitrate', 0)), reverse=True)
        for edition in candidate_editions:
            if not edition.get('urls'): continue
            if isinstance(edition.get('urls'), str): edition['urls'] = [edition.get('urls')]
            for download_url in edition.get('urls'):
                if not download_url or not str(download_url).startswith('http'): continue
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(', '.join([singer.get('nick_name') for singer in (safeextractfromdict(search_result, ['channel_info', 'data', 'podcasters'], []) or []) if isinstance(singer, dict) and singer.get('nick_name')])),
                    album=legalizestring(safeextractfromdict(search_result, ['channel_info', 'data', 'title'], None) or search_result.get('desc')), ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=int(float(edition.get('size', 0) or 0)) * 1024, file_size=byte2mb(int(float(edition.get('size', 0) or 0)) * 1024), identifier=song_id, duration_s=int(float(search_result.get('duration', 0) or 0)),
                    duration=seconds2hms(search_result.get('duration', 0) or 0), lyric=None, cover_url=safeextractfromdict(search_result, ['cover'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                )
                if song_info.with_valid_download_url: break
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsebytrack'''
    def _parsebytrack(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        request_overrides = request_overrides or {}
        for search_result in search_results['data']['data']:
            if (not isinstance(search_result, dict)) or ('id' not in search_result) or (search_result.get('type') not in {'program'}): continue
            song_info = SongInfo(source=self.source)
            for parser in [self._parsewithofficialapiv1]:
                try: song_info = parser(search_result=search_result, request_overrides=request_overrides)
                except: continue
                if song_info.with_valid_download_url: break
            if not song_info.with_valid_download_url: continue
            song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        return song_infos
    '''_parsebyalbum'''
    def _parsebyalbum(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        request_overrides = request_overrides or {}
        for search_result in search_results['data']['data']:
            if (not isinstance(search_result, dict)) or ('id' not in search_result) or (search_result.get('type') not in {'channel_ondemand'}): continue
            try: search_result['channel_info'] = self._fetchchannelinfo(search_result['id'], request_overrides)
            except Exception: pass
            download_results, page_size, tracks, unique_track_ids = [], 100, [], set()
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_results, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(safeextractfromdict(search_result, ['podcaster', 'name'], None)), 
                album=f"{safeextractfromdict(search_result, ['channel_info', 'data', 'program_count'], 0) or 0} Episodes", ext=None, file_size=None, identifier=search_result['id'], duration='-:-:-', lyric=None, cover_url=search_result.get('cover', None),
                download_url=None, download_url_status={}, episodes=[],
            )
            num_pages = math.ceil(int(safeextractfromdict(search_result, ['channel_info', 'data', 'program_count'], 0) or 0) / page_size)
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/{num_pages}) pages downloaded in album {search_result['id']}", total=num_pages)
            for page_num_idx, page_num in enumerate(range(1, num_pages + 1)):
                if page_num_idx > 0:
                    progress.advance(download_album_pid, 1)
                    progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({page_num_idx}/{num_pages}) pages downloaded in album {search_result['id']}")
                try: download_results.append(self._listpageprograms(search_result['id'], page=page_num, page_size=page_size, request_overrides=request_overrides))
                except: continue
            progress.advance(download_album_pid, 1)
            progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({page_num_idx+1}/{num_pages}) pages downloaded in album {search_result['id']}")
            for download_result in download_results:
                for track in (safeextractfromdict(download_result, ['data', 'programs'], []) or []):
                    if not isinstance(track, dict) or not track.get('id'): continue
                    if track.get('id') in unique_track_ids: continue
                    unique_track_ids.add(track.get('id'))
                    tracks.append(track)
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/{len(tracks)}) episodes completed in album {search_result['id']}", total=len(tracks))
            for track_idx, track in enumerate(tracks):
                if track_idx > 0:
                    progress.advance(download_album_pid, 1)
                    progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({track_idx}/{len(tracks)}) episodes completed in album {search_result['id']}")
                eps_info, track['channel_info'] = SongInfo(source=self.source), search_result.get('channel_info', {})
                track['url'] = f"qingtingfm://app.qingting.fm/playingview?type=ondemand&channel_id={search_result['id']}&program_id={track['id']}"
                for parser in [self._parsewithofficialapiv1]:
                    try: eps_info = parser(search_result=track, request_overrides=request_overrides)
                    except: continue
                    if eps_info.with_valid_download_url: break
                if not eps_info.with_valid_download_url: continue
                song_info.episodes.append(eps_info)
            progress.advance(download_album_pid, 1)
            progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({track_idx+1}/{len(tracks)}) episodes completed in album {search_result['id']}")
            if not song_info.with_valid_download_url: continue
            try: song_info.duration_s = sum([eps.duration_s for eps in song_info.episodes]); song_info.duration = seconds2hms(song_info.duration_s)
            except Exception: pass
            try: song_info.file_size_bytes = sum([eps.file_size_bytes for eps in song_info.episodes]); song_info.file_size = byte2mb(song_info.file_size_bytes)
            except Exception: pass
            song_infos.append(song_info)
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
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)
            # --parse based on search type
            search_type = parse_qs(urlparse(search_url).query, keep_blank_values=True).get('include')[0]
            parsers = {'channel_ondemand': self._parsebyalbum, 'program_ondemand': self._parsebytrack}
            parsers[search_type](search_results, song_infos=song_infos, request_overrides=request_overrides, progress=progress)
            # --update progress
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Error: {err})")
        # return
        return song_infos