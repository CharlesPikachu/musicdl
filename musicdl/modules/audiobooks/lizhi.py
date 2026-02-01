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
from contextlib import suppress
from urllib.parse import urlencode
from rich.progress import Progress
from ..sources import BaseMusicClient
from ..utils import legalizestring, resp2json, seconds2hms, usesearchheaderscookies, safeextractfromdict, SongInfo


'''LizhiMusicClient'''
class LizhiMusicClient(BaseMusicClient):
    source = 'LizhiMusicClient'
    ALLOWED_SEARCH_TYPES = ['album', 'track']
    MUSIC_QUALITIES = ['_ud.mp3', '_hd.mp3', '_sd.m4a']
    def __init__(self, **kwargs):
        self.allowed_search_types = list(set(kwargs.pop('allowed_search_types', LizhiMusicClient.ALLOWED_SEARCH_TYPES)))
        super(LizhiMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
            'Referer': 'https://m.lizhi.fm',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        self.search_size_per_page = min(self.search_size_per_page, 20)
        # construct search urls based on search rules
        search_urls, page_size = [], self.search_size_per_page
        for search_type in LizhiMusicClient.ALLOWED_SEARCH_TYPES:
            if search_type not in self.allowed_search_types: continue
            if search_type in {'track'}:
                default_rule = {'deviceId': "h5-b6ef91a9-3dbb-c716-1fdd-43ba08851150", "keywords": keyword, "page": 1, "receiptData": ""}
                default_rule.update(rule)
                base_url, count = 'https://m.lizhi.fm/vodapi/search/voice?', 0
                while self.search_size_per_source > count:
                    page_rule = copy.deepcopy(default_rule)
                    page_rule['page'] = str(int(count // page_size) + 1)
                    if count > 0:
                        with suppress(Exception): receipt_data = resp2json(self.get(search_urls[-1]['url'], **request_overrides)).get('receiptData', '')
                        page_rule['receiptData'] = receipt_data
                    search_urls.append({'url': base_url + urlencode(page_rule), 'type': search_type})
                    count += page_size
            elif search_type in ['album']:
                default_rule = {'deviceId': "h5-b6ef91a9-3dbb-c716-1fdd-43ba08851150", "keywords": keyword, "page": 1, "receiptData": ""}
                default_rule.update(rule)
                base_url, count = 'https://m.lizhi.fm/vodapi/search/voice?', 0
                while self.search_size_per_source > count:
                    page_rule = copy.deepcopy(default_rule)
                    page_rule['page'] = str(int(count // page_size) + 1)
                    if count > 0:
                        with suppress(Exception): receipt_data = resp2json(self.get(search_urls[-1]['url'], **request_overrides)).get('receiptData', '')
                        page_rule['receiptData'] = receipt_data
                    search_urls.append({'url': base_url + urlencode(page_rule), 'type': search_type})
                    count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, safeextractfromdict(search_result, ['voiceInfo', 'voiceId'], ''), SongInfo(source=self.source)
        # parse
        resp = self.get(f'https://m.lizhi.fm/vodapi/voice/info/{song_id}', **request_overrides)
        resp.raise_for_status()
        download_result = resp2json(resp=resp)
        download_url = safeextractfromdict(download_result, ['data', 'userVoice', 'voicePlayProperty', 'trackUrl'], '')
        if not download_url or not str(download_url).startswith('http'):
            image_url = safeextractfromdict(download_result, ['data', 'userVoice', 'voiceInfo', 'imageUrl'], "") or ""
            m = re.search(r'/(\d{4}/\d{2}/\d{2})(?:/|$)', str(image_url))
            if not m: return song_info
            download_url = f'https://cdn101.lizhi.fm/audio/{m.group(1)}/{song_id}_sd.m4a' # cdn101 is better than cdn5
        for quality in LizhiMusicClient.MUSIC_QUALITIES:
            download_url: str = (download_url[:-7] + quality).replace('//cdn5.lizhi.fm/audio/', '//cdn101.lizhi.fm/audio/')
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'userVoice', 'voiceInfo', 'name'], '')),
                singers=legalizestring(safeextractfromdict(download_result, ['data', 'userVoice', 'userInfo', 'name'], '')), album=legalizestring(safeextractfromdict(download_result, ['data', 'userVoice', 'userInfo', 'name'], '')), 
                ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=None, file_size='NULL', identifier=song_id, duration_s=safeextractfromdict(download_result, ['data', 'userVoice', 'voiceInfo', 'duration'], ''), 
                duration=seconds2hms(safeextractfromdict(download_result, ['data', 'userVoice', 'voiceInfo', 'duration'], '')), lyric=None, cover_url=safeextractfromdict(download_result, ['data', 'userVoice', 'voiceInfo', 'imageUrl'], None), 
                download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            if not song_info.with_valid_download_url: song_info.update(dict(
                download_url=download_url.replace('//cdn101.lizhi.fm/audio/', '//cdn5.lizhi.fm/audio/'), download_url_status=self.audio_link_tester.test(download_url.replace('//cdn101.lizhi.fm/audio/', '//cdn5.lizhi.fm/audio/'), request_overrides)
            ))
            if song_info.with_valid_download_url: break
        if not song_info.with_valid_download_url: return song_info
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        # return
        return song_info
    '''_parsebytrack'''
    def _parsebytrack(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        request_overrides = request_overrides or {}
        for search_result in search_results:
            if not isinstance(search_result, dict) or not safeextractfromdict(search_result, ['voiceInfo', 'voiceId'], ''): continue
            song_info, song_id = SongInfo(source=self.source), safeextractfromdict(search_result, ['voiceInfo', 'voiceId'], '')
            download_url = safeextractfromdict(search_result, ['voicePlayProperty', 'trackUrl'], '')
            if not download_url or not str(download_url).startswith('http'):
                image_url = safeextractfromdict(search_result, ['voiceInfo', 'imageUrl'], "") or ""
                m = re.search(r'/(\d{4}/\d{2}/\d{2})(?:/|$)', str(image_url))
                if not m: continue
                download_url = f'https://cdn101.lizhi.fm/audio/{m.group(1)}/{song_id}_sd.m4a' # cdn101 is better than cdn5
            for quality in LizhiMusicClient.MUSIC_QUALITIES:
                download_url: str = (download_url[:-7] + quality).replace('//cdn5.lizhi.fm/audio/', '//cdn101.lizhi.fm/audio/')
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['voiceInfo', 'name'], '')),
                    singers=legalizestring(safeextractfromdict(search_result, ['userInfo', 'name'], '')), album=legalizestring(safeextractfromdict(search_result, ['userInfo', 'name'], '')), 
                    ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=None, file_size='NULL', identifier=song_id, duration_s=safeextractfromdict(search_result, ['voiceInfo', 'duration'], ''), 
                    duration=seconds2hms(safeextractfromdict(search_result, ['voiceInfo', 'duration'], '')), lyric=None, cover_url=safeextractfromdict(search_result, ['voiceInfo', 'imageUrl'], None), 
                    download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                )
                if not song_info.with_valid_download_url: song_info.update(dict(
                    download_url=download_url.replace('//cdn101.lizhi.fm/audio/', '//cdn5.lizhi.fm/audio/'), download_url_status=self.audio_link_tester.test(download_url.replace('//cdn101.lizhi.fm/audio/', '//cdn5.lizhi.fm/audio/'), request_overrides)
                ))
                if song_info.with_valid_download_url: break
            if not song_info.with_valid_download_url: continue
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        return song_infos
    '''_parsebyalbum'''
    def _parsebyalbum(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None):
        request_overrides, unique_album_ids = request_overrides or {}, set()
        for search_result in search_results:
            if not isinstance(search_result, dict) or not safeextractfromdict(search_result, ['userInfo', 'userId'], ''): continue
            album_id = safeextractfromdict(search_result, ['userInfo', 'userId'], '')
            if album_id in unique_album_ids: continue
            unique_album_ids.add(album_id)
            download_results, page_size, page_no, track_idx, unique_track_ids = [], 1000, 1, 0, set()
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_results, 'lyric': {}}, source=self.source, song_name=album_id, singers=legalizestring(safeextractfromdict(search_result, ['userInfo', 'name'], '')), 
                album=f"{safeextractfromdict(search_result, ['userInfo', 'audioNum'], '') or 0} Episodes", ext=None, file_size_bytes=None, file_size=None, identifier=album_id, duration_s=None, duration='-:-:-', lyric=None, 
                cover_url=safeextractfromdict(search_result, ['userInfo', 'photo'], None), download_url=None, download_url_status={}, episodes=[],
            )
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/0) pages downloaded in album {album_id}", total=0)
            while True:
                try: resp = self.get(f'https://m.lizhi.fm/vodapi/user/{album_id}?pageNo={page_no}&pageSize={page_size}', **request_overrides); resp.raise_for_status()
                except Exception: break
                download_result = resp2json(resp=resp)
                if not download_result.get('data'): break
                download_results.append(download_result)
                page_no += 1
                progress.update(download_album_pid, total=page_no, completed=page_no)
                progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({page_no}/{page_no}) pages downloaded in album {album_id}")
            total_episodes = sum([len(safeextractfromdict(download_result, ['data'], []) or []) for download_result in download_results])
            download_album_pid = progress.add_task(f"{self.source}._parsebyalbum >>> (0/{total_episodes}) episodes completed in album {album_id}", total=total_episodes)
            for download_result in download_results:
                for track in (safeextractfromdict(download_result, ['data'], []) or []):
                    track_idx += 1
                    progress.advance(download_album_pid, 1)
                    progress.update(download_album_pid, description=f"{self.source}._parsebyalbum >>> ({track_idx}/{total_episodes}) episodes completed in album {album_id}")
                    if not isinstance(track, dict) or not safeextractfromdict(track, ['voiceInfo', 'voiceId'], ''): continue
                    eps_info, eps_id = SongInfo(source=self.source), safeextractfromdict(track, ['voiceInfo', 'voiceId'], '')
                    if eps_id in unique_track_ids: continue
                    unique_track_ids.add(eps_id)
                    download_url = safeextractfromdict(track, ['voicePlayProperty', 'trackUrl'], '')
                    if not download_url or not str(download_url).startswith('http'):
                        image_url = safeextractfromdict(track, ['voiceInfo', 'imageUrl'], "") or ""
                        m = re.search(r'/(\d{4}/\d{2}/\d{2})(?:/|$)', str(image_url))
                        if not m: continue
                        download_url = f'https://cdn101.lizhi.fm/audio/{m.group(1)}/{eps_id}_sd.m4a' # cdn101 is better than cdn5
                    for quality in LizhiMusicClient.MUSIC_QUALITIES:
                        download_url: str = (download_url[:-7] + quality).replace('//cdn5.lizhi.fm/audio/', '//cdn101.lizhi.fm/audio/')
                        eps_info = SongInfo(
                            raw_data={'search': search_result, 'download': track, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(track, ['voiceInfo', 'name'], '')),
                            singers=legalizestring(safeextractfromdict(track, ['userInfo', 'name'], '')), album=legalizestring(safeextractfromdict(track, ['userInfo', 'name'], '')), 
                            ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=eps_id, duration_s=safeextractfromdict(track, ['voiceInfo', 'duration'], ''), 
                            duration=seconds2hms(safeextractfromdict(track, ['voiceInfo', 'duration'], '')), lyric=None, cover_url=safeextractfromdict(track, ['voiceInfo', 'imageUrl'], None), 
                            download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                        )
                        if not eps_info.with_valid_download_url: eps_info.update(dict(
                            download_url=download_url.replace('//cdn101.lizhi.fm/audio/', '//cdn5.lizhi.fm/audio/'), download_url_status=self.audio_link_tester.test(download_url.replace('//cdn101.lizhi.fm/audio/', '//cdn5.lizhi.fm/audio/'), request_overrides)
                        ))
                        if eps_info.with_valid_download_url: break
                    if not eps_info.with_valid_download_url: continue
                    eps_info.download_url_status['probe_status'] = self.audio_link_tester.probe(eps_info.download_url, request_overrides)
                    eps_info.file_size = eps_info.download_url_status['probe_status']['file_size']
                    song_info.episodes.append(eps_info)
            if not song_info.with_valid_download_url: continue
            try: song_info.duration_s = sum([eps.duration_s for eps in song_info.episodes]); song_info.duration = seconds2hms(song_info.duration_s)
            except Exception: pass
            try: song_info.file_size = str(round(sum([float(eps.file_size.removesuffix('MB').strip()) for eps in song_info.episodes]), 2)) + ' MB'
            except Exception: pass
            song_info.album = f"{len(song_info.episodes)} Episodes"
            song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        return song_infos            
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        search_type, search_url = search_url['type'], search_url['url']
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['data']
            # --parse based on search type
            parsers = {'album': self._parsebyalbum, 'track': self._parsebytrack}
            parsers[search_type](search_results, song_infos=song_infos, request_overrides=request_overrides, progress=progress)
            # --update progress
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Error: {err})")
        # return
        return song_infos