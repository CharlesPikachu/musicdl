'''
Function:
    Implementation of JamendoMusicClient: https://www.jamendo.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
import random
import hashlib
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import legalizestring, resp2json, usesearchheaderscookies, seconds2hms, safeextractfromdict, SongInfo


'''JamendoMusicClient'''
class JamendoMusicClient(BaseMusicClient):
    source = 'JamendoMusicClient'
    def __init__(self, **kwargs):
        super(JamendoMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "referer": "https://www.jamendo.com/search?q=musicdl", "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "x-jam-version": "4gvfvv",
            "x-jam-call": "$536ab7feabd2404af7b6e54b4db74039734b58b3*0.5310391483096057~", "x-requested-with": "XMLHttpRequest",
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_makexjamcall'''
    def _makexjamcall(self, path: str = '/api/search') -> str:
        rand = str(random.random())
        digest = hashlib.sha1((path + rand).encode("utf-8")).hexdigest()
        return f"${digest}*{rand}~"
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {'query': keyword, 'type': 'track', 'limit': self.search_size_per_source, 'identities': 'www', 'offset': 0}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://www.jamendo.com/api/search?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['limit'] = page_size
            page_rule['offset'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # successful
        try:
            # --search results
            headers = copy.deepcopy(self.default_headers)
            headers['x-jam-call'] = self._makexjamcall()
            resp = self.get(search_url, headers=headers, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('id' not in search_result): continue
                song_info = SongInfo(source=self.source)
                try:
                    resp = self.get('https://www.jamendo.com/api/tracks?', params={'id[]': search_result['id']}, **request_overrides)
                    resp.raise_for_status()
                    download_result = resp2json(resp=resp)[0]
                except:
                    download_result = {}
                spaths = [('download', 'mp3'), ('stream', 'mp3'), ('download', 'ogg'), ('stream', 'ogg')]
                dpaths = [('stream', 'flac'), ('download', 'flac'), ('stream', 'mp33'), ('stream', 'mp32'), ('download', 'mp3'), ('stream', 'mp3'), ('stream', 'ogg'), ('download', 'ogg')]
                candidate_urls = [safeextractfromdict(download_result, list(path), None) for path in dpaths]
                candidate_urls = [c for c in candidate_urls if c and str(c).startswith('http')]
                if not candidate_urls: candidate_urls = [safeextractfromdict(search_result, list(path), None) for path in spaths]
                candidate_urls = [c for c in candidate_urls if c and str(c).startswith('http')]
                if not candidate_urls: continue
                for download_url in candidate_urls:
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)), 
                        singers=legalizestring(safeextractfromdict(search_result, ['artist', 'name'], None)), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None)),
                        ext='mp3', file_size='NULL', identifier=search_result['id'], duration_s=safeextractfromdict(search_result, ['duration'], 0), duration=seconds2hms(search_result.get('duration', 0)),
                        lyric=download_result.get('lyrics') or 'NULL', cover_url=f"https://usercontent.jamendo.com?type=album&id={safeextractfromdict(search_result, ['album', 'id'], None)}&width=300&trackid={search_result['id']}",
                        download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                    )
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: continue
                song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
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