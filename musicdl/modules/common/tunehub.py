'''
Function:
    Implementation of TuneHubMusicClient: https://tunehub.sayqz.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
import random
import base64
import requests
from rich.progress import Progress
from ..sources import BaseMusicClient
from urllib.parse import urlparse, parse_qs
from ..utils import legalizestring, resp2json, usesearchheaderscookies, seconds2hms, extractdurationsecondsfromlrc, safeextractfromdict, cleanlrc, SongInfo


'''TuneHubMusicClient'''
class TuneHubMusicClient(BaseMusicClient):
    source = 'TuneHubMusicClient'
    ALLOWED_SITES = ['netease', 'qq', 'kuwo', 'kugou', 'migu'][:3] # it seems kugou and migu are useless, recorded in 2026-01-28
    MUSIC_QUALITIES = ['flac24bit', 'flac', '320k', '128k']
    BAKA_MUSIC_QUALITIES = ['400', '380', '320', '128']
    REQUEST_API_KEYS = ['dGhfMzA2M2U0YWQyZWY4MDc1Nzc0YWJkNDEzYTQxN2NlMzE5MTRiNjBkODc3NmM1NTQ5', 'dGhfOGYwMGQ4NzA5ZGJhOWQ0NDgwYmExOTE2NjgxNDdlMWI3YjkzNjkyMDkyMGZhNjZm']
    def __init__(self, **kwargs):
        self.allowed_music_sources = list(set(kwargs.pop('allowed_music_sources', TuneHubMusicClient.ALLOWED_SITES)))
        super(TuneHubMusicClient, self).__init__(**kwargs)
        decrypt_func = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36', 
            'X-API-Key': decrypt_func(random.choice(TuneHubMusicClient.REQUEST_API_KEYS)),
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_tunehubkuwosearch: https://tunehub.sayqz.com/api/v1/methods/kuwo/search'''
    def _tunehubkuwosearch(self, keyword: str, page: int = 1, limit: int = 20, timeout: float = 10.0):
        url = "http://search.kuwo.cn/r.s"
        page = 1 if (page is None or int(page) < 1) else int(page)
        limit = 20 if (limit is None or int(limit) <= 0) else int(limit)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        params = {"client": "kt", "all": keyword, "pn": page - 1, "rn": limit, "uid": "794762570", "ver": "kwplayer_ar_9.2.2.1", "vipver": "1", "show_copyright_off": "1", "newver": "1", "ft": "music", "cluster": "0", "strategy": "2012", "encoding": "utf8", "rformat": "json", "vermerge": "1", "mobi": "1", "issubtitle": "1"}
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data: dict = resp.json()
        abslist, out = data.get("abslist"), []
        if not abslist: return []
        for item in abslist:
            musicrid = item.get("MUSICRID", "")
            out.append({"id": musicrid.replace("MUSIC_", ""), "name": item.get("SONGNAME", ""), "artist": (item.get("ARTIST", "") or "").replace("&", ", "), "album": item.get("ALBUM") or "", "source": "kuwo"})
        return out
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        allowed_music_sources = copy.deepcopy(self.allowed_music_sources)
        # construct search urls based on search rules
        search_urls, page_size = [], self.search_size_per_page
        for source in TuneHubMusicClient.ALLOWED_SITES:
            if source not in allowed_music_sources: continue
            if source in {'netease', 'qq'}:
                server = {'netease': 'netease', 'qq': 'tencent'}[source]
                search_urls.append(f"https://api.baka.plus/meting?server={server}&type=search&id=0&yrc=false&keyword={keyword}")
            else:
                source_default_rule, count = {'keyword': keyword, 'page': 1, 'limit': 20, 'timeout': 10.0}, 0
                source_default_rule.update(rule)
                while self.search_size_per_source > count:
                    page_rule = copy.deepcopy(source_default_rule)
                    page_rule['page'] = str(int(count // page_size) + 1)
                    page_rule['limit'] = str(page_size)
                    search_urls.append({'search_api': {'kuwo': self._tunehubkuwosearch}[source], 'rule': page_rule})
                    count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str | dict = None, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # successful
        try:
            # --search results
            if isinstance(search_url, dict):
                search_results = search_url['search_api'](**search_url['rule'])
            else:
                resp = self.get(search_url, **request_overrides)
                resp.raise_for_status()
                search_results = resp2json(resp)
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('id' not in search_result and 'url' not in search_result) or ('source' not in search_result): continue
                if 'id' not in search_result: search_result['id'] = parse_qs(urlparse(str(search_result['url'])).query, keep_blank_values=True).get('id')[0]
                search_result['source'] = {'netease': 'netease', 'tencent': 'qq', 'kuwo': 'kuwo'}[search_result['source']]
                song_info = SongInfo(source=self.source, root_source=search_result['source'])
                if search_result['source'] in {'netease', 'qq'}:
                    for br in (TuneHubMusicClient.BAKA_MUSIC_QUALITIES if search_result['source'] in {'netease'} else TuneHubMusicClient.BAKA_MUSIC_QUALITIES[:1]):
                        params = {'br': br, 'id': search_result['id'], 'server': {'netease': 'netease', 'qq': 'tencent', 'kuwo': 'kuwo'}[search_result['source']], 'type': 'url'}
                        try: (resp := self.session.head('https://api.baka.plus/meting?', timeout=10, params=params, allow_redirects=True, **request_overrides)).raise_for_status(); download_url = resp.url
                        except Exception: continue
                        try: (resp := self.session.head(safeextractfromdict(search_result, ['pic'], None), timeout=10, allow_redirects=True, **request_overrides)).raise_for_status(); cover_url = resp.url
                        except Exception: cover_url = safeextractfromdict(search_result, ['pic'], None) or ""
                        song_info = SongInfo(
                            raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)),
                            singers=legalizestring(safeextractfromdict(search_result, ['artist'], None)), album=legalizestring(safeextractfromdict(search_result, ['album'], None)),
                            ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=search_result['id'], duration='-:-:-', lyric=None, cover_url=cover_url, 
                            download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides), root_source=search_result['source'],
                        )
                        if song_info.root_source in ['tencent']: song_info.root_source = 'qq'
                        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
                        if song_info.with_valid_download_url: break
                elif search_result['source'] in ['kuwo']:
                    for quality in TuneHubMusicClient.MUSIC_QUALITIES:
                        data = {'quality': quality, 'ids': search_result['id'], 'platform': search_result['source']}
                        try: (resp := self.post('https://tunehub.sayqz.com/api/v1/parse?', timeout=10, data=data, **request_overrides)).raise_for_status(); download_result = resp2json(resp=resp)
                        except Exception: continue
                        download_url = safeextractfromdict(download_result, ['data', 'data', 0, 'url'], "")
                        if not download_url or not download_url.startswith('http'): continue
                        song_info = SongInfo(
                            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)), singers=legalizestring(safeextractfromdict(search_result, ['artist'], None)), 
                            album=legalizestring(safeextractfromdict(search_result, ['album'], None)), ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=search_result['id'], duration_s=safeextractfromdict(download_result, ['data', 'data', 0, 'info', 'duration'], 0),
                            duration=seconds2hms(safeextractfromdict(download_result, ['data', 'data', 0, 'info', 'duration'], 0)), lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'data', 0, 'lyrics'], 0)), cover_url=safeextractfromdict(download_result, ['data', 'data', 0, 'cover'], 0),
                            download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides), root_source=search_result['source'],
                        )
                        if str(song_info.lyric).startswith('http'): search_result['lrc'] = song_info.lyric
                        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
                        if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: continue
                # --lyric results
                try:
                    resp = self.get(search_result['lrc'], **request_overrides)
                    resp.raise_for_status()
                    lyric, lyric_result = cleanlrc(resp.text), {'lyric': resp.text}
                    song_info.duration_s = extractdurationsecondsfromlrc(lyric)
                    song_info.duration = seconds2hms(song_info.duration_s)
                except:
                    lyric_result, lyric = dict(), 'NULL'
                song_info.lyric = lyric
                song_info.raw_data['lyric'] = lyric_result
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