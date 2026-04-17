'''
Function:
    Implementation of LizhiMusicClient: https://www.lizhi.fm/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
from itertools import chain
from contextlib import suppress
from urllib.parse import urlencode
from rich.progress import Progress
from ..sources import BaseMusicClient
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, SongInfo, SongInfoUtils, AudioLinkTester


'''LizhiMusicClient'''
class LizhiMusicClient(BaseMusicClient):
    source = 'LizhiMusicClient'
    ALLOWED_SEARCH_TYPES = ['album', 'track']
    MUSIC_QUALITIES = ['_ud.mp3', '_hd.mp3', '_sd.m4a']
    def __init__(self, **kwargs):
        self.allowed_search_types = list(set(kwargs.pop('allowed_search_types', LizhiMusicClient.ALLOWED_SEARCH_TYPES)))
        super(LizhiMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1', 'Referer': 'https://m.lizhi.fm'}
        self.default_download_headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1'}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, self.search_size_per_page = rule or {}, request_overrides or {}, min(self.search_size_per_page, 20)
        # construct search urls
        search_urls, page_size = [], self.search_size_per_page
        for search_type in LizhiMusicClient.ALLOWED_SEARCH_TYPES:
            if search_type not in self.allowed_search_types: continue
            (default_rule := {'deviceId': "h5-b6ef91a9-3dbb-c716-1fdd-43ba08851150", "keywords": keyword, "page": 1, "receiptData": ""}).update(rule)
            base_url, count = 'https://m.lizhi.fm/vodapi/search/voice?', 0
            while self.search_size_per_source > count:
                (page_rule := copy.deepcopy(default_rule))['page'] = str(int(count // page_size) + 1)
                if count > 0: page_rule['receiptData'] = resp2json(self.get(search_urls[-1]['url'], **request_overrides)).get('receiptData', '')
                search_urls.append({'url': base_url + urlencode(page_rule), 'type': search_type})
                count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, safeextractfromdict(search_result, ['voiceInfo', 'voiceId'], ''), SongInfo(source=self.source)
        # parse
        (resp := self.get(f'https://m.lizhi.fm/vodapi/voice/info/{song_id}', **request_overrides)).raise_for_status()
        download_url = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'userVoice', 'voicePlayProperty', 'trackUrl'], '')
        image_url = safeextractfromdict(download_result, ['data', 'userVoice', 'voiceInfo', 'imageUrl'], "") or ""
        if (not download_url or not str(download_url).startswith('http')) and (not (m := re.search(r'/(\d{4}/\d{2}/\d{2})(?:/|$)', str(image_url)))): return song_info
        if not download_url or not str(download_url).startswith('http'): download_url = f'https://cdn101.lizhi.fm/audio/{m.group(1)}/{song_id}_sd.m4a' # cdn101 is faster than cdn5
        for quality in LizhiMusicClient.MUSIC_QUALITIES:
            download_url: str = (download_url[:-7] + quality).replace('//cdn5.lizhi.fm/audio/', '//cdn101.lizhi.fm/audio/')
            duration_in_secs = safeextractfromdict(download_result, ['data', 'userVoice', 'voiceInfo', 'duration'], 0) or 0
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'userVoice', 'voiceInfo', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'userVoice', 'userInfo', 'name'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'userVoice', 'userInfo', 'name'], None)), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'userVoice', 'voiceInfo', 'imageUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if not song_info.with_valid_download_url: download_url_status: dict = self.audio_link_tester.test(url=download_url.replace('//cdn101.lizhi.fm/audio/', '//cdn5.lizhi.fm/audio/'), request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'userVoice', 'voiceInfo', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'userVoice', 'userInfo', 'name'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'userVoice', 'userInfo', 'name'], None)), ext=download_url_status['ext'], 
                file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'userVoice', 'voiceInfo', 'imageUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsebytrack'''
    def _parsebytrack(self, search_results: list[dict], song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        # init
        request_overrides, progress, song_info = dict(request_overrides or {}), progress, SongInfo(source=self.source)
        # parse one by one
        for search_result in (search_results or []):
            if not isinstance(search_result, dict) or not (song_id := safeextractfromdict(search_result, ['voiceInfo', 'voiceId'], '')): continue
            song_info, download_url, image_url = SongInfo(source=self.source), safeextractfromdict(search_result, ['voicePlayProperty', 'trackUrl'], ''), safeextractfromdict(search_result, ['voiceInfo', 'imageUrl'], '')
            if (not download_url or not str(download_url).startswith('http')) and (not (m := re.search(r'/(\d{4}/\d{2}/\d{2})(?:/|$)', str(image_url)))): continue
            if not download_url or not str(download_url).startswith('http'): download_url = f'https://cdn101.lizhi.fm/audio/{m.group(1)}/{song_id}_sd.m4a' # cdn101 is faster than cdn5
            for quality in LizhiMusicClient.MUSIC_QUALITIES:
                download_url: str = (download_url[:-7] + quality).replace('//cdn5.lizhi.fm/audio/', '//cdn101.lizhi.fm/audio/')
                duration_in_secs = safeextractfromdict(search_result, ['voiceInfo', 'duration'], 0)
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['voiceInfo', 'name'], None)), singers=legalizestring(safeextractfromdict(search_result, ['userInfo', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['userInfo', 'name'], None)), ext=download_url_status['ext'], 
                    file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['voiceInfo', 'imageUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if not song_info.with_valid_download_url: download_url_status: dict = self.audio_link_tester.test(url=download_url.replace('//cdn101.lizhi.fm/audio/', '//cdn5.lizhi.fm/audio/'), request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['voiceInfo', 'name'], None)), singers=legalizestring(safeextractfromdict(search_result, ['userInfo', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['userInfo', 'name'], None)), ext=download_url_status['ext'], 
                    file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(search_result, ['voiceInfo', 'imageUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
            if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
            if song_info.with_valid_download_url: song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        # return
        return song_infos
    '''_parsebyalbum'''
    def _parsebyalbum(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        # init
        request_overrides, unique_album_ids = request_overrides or {}, set()
        # parse one by one
        for search_result in (search_results or []):
            if not isinstance(search_result, dict) or not (album_id := safeextractfromdict(search_result, ['userInfo', 'userId'], '')) or (album_id in unique_album_ids): continue
            unique_album_ids.add(album_id); download_results, page_size, page_no, track_idx, unique_track_ids = [], 1000, 1, 0, set()
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_results, 'lyric': {}}, source=self.source, song_name=album_id, singers=legalizestring(safeextractfromdict(search_result, ['userInfo', 'name'], None)), album=f"{safeextractfromdict(search_result, ['userInfo', 'audioNum'], 0) or 0} Episodes",
                ext=None, file_size_bytes=None, file_size=None, identifier=album_id, duration_s=None, duration='-:-:-', lyric=None, cover_url=safeextractfromdict(search_result, ['userInfo', 'photo'], None), download_url=None, download_url_status={}, episodes=[],
            )
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/0) pages downloaded in album {album_id}", total=None)
            while True:
                with suppress(Exception): (album_resp := self.get(f'https://m.lizhi.fm/vodapi/user/{album_id}?pageNo={page_no}&pageSize={page_size}', **request_overrides)).raise_for_status()
                if not locals().get('album_resp') or not hasattr(locals().get('album_resp'), 'text'): break
                if not (download_result := resp2json(resp=album_resp)).get('data'): break
                del album_resp; download_results.append(download_result); progress.update(download_album_pid, total=(page_no := page_no + 1), completed=page_no)
                progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({page_no}/{page_no}) pages downloaded in album {album_id}")
            total_episodes = sum([len(safeextractfromdict(download_result, ['data'], []) or []) for download_result in download_results])
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/{total_episodes}) episodes completed in album {album_id}", total=total_episodes)
            for track in chain.from_iterable(safeextractfromdict(download_result, ['data'], []) or [] for download_result in download_results):
                track_idx += 1; progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({track_idx}/{total_episodes}) episodes completed in album {album_id}")
                if not isinstance(track, dict) or not (eps_id := safeextractfromdict(track, ['voiceInfo', 'voiceId'], '')) or (eps_id in unique_track_ids): continue
                unique_track_ids.add(eps_id); download_url, eps_info, image_url = safeextractfromdict(track, ['voicePlayProperty', 'trackUrl'], ''), SongInfo(source=self.source), safeextractfromdict(track, ['voiceInfo', 'imageUrl'], '')
                if (not download_url or not str(download_url).startswith('http')) and (not (m := re.search(r'/(\d{4}/\d{2}/\d{2})(?:/|$)', str(image_url)))): continue
                if not download_url or not str(download_url).startswith('http'): download_url = f'https://cdn101.lizhi.fm/audio/{m.group(1)}/{eps_id}_sd.m4a' # cdn101 is faster than cdn5
                for quality in LizhiMusicClient.MUSIC_QUALITIES:
                    download_url: str = (download_url[:-7] + quality).replace('//cdn5.lizhi.fm/audio/', '//cdn101.lizhi.fm/audio/')
                    duration_in_secs = safeextractfromdict(track, ['voiceInfo', 'duration'], 0) or 0
                    download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                    eps_info = SongInfo(
                        raw_data={'search': search_result, 'download': track, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(track, ['voiceInfo', 'name'], None)), singers=legalizestring(safeextractfromdict(track, ['userInfo', 'name'], None)), album=legalizestring(safeextractfromdict(track, ['userInfo', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                        file_size=download_url_status['file_size'], identifier=eps_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(track, ['voiceInfo', 'imageUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers
                    )
                    if not eps_info.with_valid_download_url: download_url_status: dict = self.audio_link_tester.test(url=download_url.replace('//cdn101.lizhi.fm/audio/', '//cdn5.lizhi.fm/audio/'), request_overrides=request_overrides, renew_session=True)
                    eps_info = SongInfo(
                        raw_data={'search': search_result, 'download': track, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(track, ['voiceInfo', 'name'], None)), singers=legalizestring(safeextractfromdict(track, ['userInfo', 'name'], None)), album=legalizestring(safeextractfromdict(track, ['userInfo', 'name'], None)), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                        file_size=download_url_status['file_size'], identifier=eps_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=safeextractfromdict(track, ['voiceInfo', 'imageUrl'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers
                    )
                    if eps_info.with_valid_download_url and eps_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
                if not eps_info.with_valid_download_url or eps_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                if eps_info.with_valid_download_url: song_info.episodes.append(eps_info)
            if len(song_info.episodes) == 0 or not song_info.with_valid_download_url: continue
            with suppress(Exception): song_info.duration_s = sum([float(eps.duration_s) for eps in song_info.episodes]); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
            with suppress(Exception): song_info.file_size_bytes = sum([float(eps.file_size_bytes) for eps in song_info.episodes]); song_info.file_size = SongInfoUtils.byte2mb(song_info.file_size_bytes)
            if song_info.with_valid_download_url: song_info.album = f"{len(song_info.episodes)} Episodes"; song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        # return
        return song_infos            
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, search_type, search_url = request_overrides or {}, search_url['type'], search_url['url']
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            # --parse based on search type
            parsers = {'album': self._parsebyalbum, 'track': self._parsebytrack}
            parsers[search_type](resp2json(resp)['data'], song_infos=song_infos, request_overrides=request_overrides, progress=progress)
            # --update progress
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Error: {err})")
            self.logger_handle.error(f"{self.source}._search >>> {search_url} (Error: {err})", disable_print=self.disable_print)
        # return
        return song_infos