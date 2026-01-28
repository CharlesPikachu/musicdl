'''
Function:
    Implementation of MissEvanMusicClient: https://www.missevan.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import legalizestring, resp2json, seconds2hms, usesearchheaderscookies, safeextractfromdict, SongInfo


'''MissEvanMusicClient'''
class MissEvanMusicClient(BaseMusicClient):
    source = 'MissEvanMusicClient'
    def __init__(self, **kwargs):
        super(MissEvanMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01", "Referer": "https://www.missevan.com/",
        }
        self.default_download_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules, cid for music class should be in {48, 50, 75, 76}
        default_rule = {'s': keyword, 'p': '1', 'type': '3', 'page_size': '10', 'cid': '48'}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://www.missevan.com/sound/getsearch?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['page_size'] = page_size
            page_rule['p'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithsoundid'''
    def _parsewithsoundid(self, search_result, sound_info, album: str = 'NULL', request_overrides: dict = None):
        # init
        request_overrides, song_info = request_overrides or {}, SongInfo(source=self.source)
        # parse
        resp = self.get(f"https://www.missevan.com/sound/getsound?soundid={sound_info['sound_id']}", **request_overrides)
        resp.raise_for_status()
        download_result: dict = resp2json(resp)
        download_urls = [safeextractfromdict(download_result, ['info', 'sound', 'soundurl'], ''), safeextractfromdict(download_result, ['info', 'sound', 'soundurl_128'], '')]
        for download_url in download_urls:
            if not download_url: continue
            try: duration_s = float(safeextractfromdict(download_result, ['info', 'sound', 'duration'], 0)) / 1000
            except: duration_s = 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['info', 'sound', 'soundstr'], None)),
                singers=legalizestring(safeextractfromdict(download_result, ['info', 'sound', 'username'], None)), album=legalizestring(album), ext=download_url.split('?')[0].split('.')[-1], file_size='NULL',
                identifier=sound_info['sound_id'], duration_s=duration_s, duration=seconds2hms(duration_s), lyric='NULL', cover_url=safeextractfromdict(download_result, ['info', 'sound', 'front_cover'], None), 
                download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            if song_info.with_valid_download_url: break
        if not song_info.with_valid_download_url: return song_info
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL',)) else song_info.ext
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        safe_fetch_filesize_func = lambda file_size: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(file_size.removesuffix('MB').strip()) if isinstance(file_size, str) else 0
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['info']['Datas']
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('id' not in search_result): continue
                song_info, download_result, song_id = SongInfo(source=self.source), dict(), search_result['id']
                resp = self.get(f"https://www.missevan.com/dramaapi/getdramabysound?sound_id={song_id}", **request_overrides)
                resp.raise_for_status()
                download_result = resp2json(resp=resp)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['info', 'drama', 'name'], None)),
                    singers=legalizestring(safeextractfromdict(download_result, ['info', 'drama', 'author'], None) or safeextractfromdict(download_result, ['info', 'drama', 'username'], None)), 
                    album=legalizestring(safeextractfromdict(download_result, ['info', 'drama', 'catalog_name'], None)), ext=None, file_size=None, identifier=safeextractfromdict(download_result, ['info', 'drama', 'id'], song_id),
                    duration=None, lyric='NULL', cover_url=safeextractfromdict(download_result, ['info', 'drama', 'cover'], None), download_url=None, download_url_status=None, episodes=[],
                )
                for music_info in safeextractfromdict(download_result, ['info', 'episodes', 'music'], []) or []:
                    if 'sound_id' not in music_info: continue
                    try: song_info_eps = self._parsewithsoundid(search_result, music_info, song_info.song_name, request_overrides)
                    except: continue
                    if not song_info_eps.with_valid_download_url: continue
                    song_info.episodes.append(song_info_eps)
                for episode_info in safeextractfromdict(download_result, ['info', 'episodes', 'episode'], []) or []:
                    if 'sound_id' not in episode_info: continue
                    try: song_info_eps = self._parsewithsoundid(search_result, episode_info, song_info.song_name, request_overrides)
                    except: continue
                    if not song_info_eps.with_valid_download_url: continue
                    song_info.episodes.append(song_info_eps)
                song_info.file_size = str(sum([safe_fetch_filesize_func(eps.file_size) for eps in song_info.episodes])) + ' MB'
                song_info.duration_s = sum([eps.duration_s for eps in song_info.episodes])
                song_info.duration = seconds2hms(song_info.duration_s)
                song_info.album = f"{song_info.album} ({len(song_info.episodes)} Episodes)" if song_info.episodes else song_info.album
                if not song_info.episodes: song_info = self._parsewithsoundid(search_result, {'sound_id': search_result['id']}, song_info.album, request_overrides)
                if not song_info.with_valid_download_url: continue
                # --append to song_infos
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