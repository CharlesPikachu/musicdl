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
from contextlib import suppress
from rich.progress import Progress
from ..sources import BaseMusicClient
from urllib.parse import urlparse, parse_qs
from ..utils import legalizestring, resp2json, usesearchheaderscookies, extractdurationsecondsfromlrc, safeextractfromdict, cleanlrc, SongInfo, AudioLinkTester, SongInfoUtils


'''TuneHubMusicClient'''
class TuneHubMusicClient(BaseMusicClient):
    source = 'TuneHubMusicClient'
    ALLOWED_SITES = ['netease', 'qq', 'kuwo', 'kugou', 'migu'][:3] # it seems kugou and migu are useless, recorded in 2026-01-28
    TUNEHUB_API_MUSIC_QUALITIES = ['flac24bit', 'flac', '320k', '128k']
    METING_API_MUSIC_QUALITIES = ['400', '380', '320', '128']
    REQUEST_API_KEYS = ['dGhfOGYwMGQ4NzA5ZGJhOWQ0NDgwYmExOTE2NjgxNDdlMWI3YjkzNjkyMDkyMGZhNjZm', 'dGhfYWQ0NjM3YTIzNWI2ZjRlODUxNGU2ZThkMjU3Y2I0MjY0ODY2NjYyOTFiZDgxNzc0', 'dGhfZDgzYzY4YjA5NDVlYzYxMjZjNDQxMzkwN2MxYzc3MmI3YmI3ZGUwODU4NWI0N2Y1'][1:]
    def __init__(self, **kwargs):
        self.allowed_music_sources = list(set(kwargs.pop('allowed_music_sources', TuneHubMusicClient.ALLOWED_SITES)))
        super(TuneHubMusicClient, self).__init__(**kwargs)
        decrypt_func = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        self.default_search_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36', 'X-API-Key': decrypt_func(random.choice(TuneHubMusicClient.REQUEST_API_KEYS))}
        self.default_download_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_tunehubkuwosearch from https://tunehub.sayqz.com/api/v1/methods/kuwo/search'''
    def _tunehubkuwosearch(self, keyword: str, page: int = 1, limit: int = 20, timeout: float = 10.0):
        url, page, limit = "http://search.kuwo.cn/r.s", 1 if (page is None or int(page) < 1) else int(page), 20 if (limit is None or int(limit) <= 0) else int(limit)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        params = {"client": "kt", "all": keyword, "pn": page - 1, "rn": limit, "uid": "794762570", "ver": "kwplayer_ar_9.2.2.1", "vipver": "1", "show_copyright_off": "1", "newver": "1", "ft": "music", "cluster": "0", "strategy": "2012", "encoding": "utf8", "rformat": "json", "vermerge": "1", "mobi": "1", "issubtitle": "1"}
        (resp := requests.get(url, params=params, headers=headers, timeout=timeout)).raise_for_status()
        search_results = [{"id": str(item.get("MUSICRID", "")).replace("MUSIC_", ""), "name": item.get("SONGNAME", ""), "artist": (item.get("ARTIST", "") or "").replace("&", ", "), "album": item.get("ALBUM") or "", "source": "kuwo"} for item in (resp2json(resp=resp).get("abslist") or []) if isinstance(item, dict)]
        return search_results
    '''_tunehubqqsearch from https://tunehub.sayqz.com/api/v1/methods/qq/search'''
    def _tunehubqqsearch(self, keyword: str, page: int = 1, limit: int = 20, timeout: float = 10.0):
        url, page, limit = "https://u.y.qq.com/cgi-bin/musicu.fcg", 1 if (page is None or int(page) < 1) else int(page), 20 if (limit is None or int(limit) <= 0) else int(limit)
        payload = {"req_1": {"method": "DoSearchForQQMusicDesktop", "module": "music.search.SearchCgiService", "param": {"num_per_page": limit, "page_num": page, "query": keyword, "search_type": "0"}}}
        (resp := requests.post(url, json=payload, headers={"Content-Type": "application/json", "Referer": "https://y.qq.com/", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36", "Cookie": "uin="}, timeout=timeout)).raise_for_status()
        songs = resp2json(resp=resp)["req_1"]["data"]["body"]["song"]["list"]
        search_results = [{"id": x["mid"], "name": x["name"], "artist": ", ".join(s["name"] for s in x["singer"]), "album": x["album"]["name"], "source": "qq"} for x in songs]
        return search_results
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, allowed_music_sources = rule or {}, request_overrides or {}, copy.deepcopy(self.allowed_music_sources)
        # construct search urls
        search_urls, page_size, tunehub_to_meting_server_mapper = [], self.search_size_per_page, {'netease': 'netease', 'qq': 'tencent', 'kuwo': 'kuwo', 'kugou': 'kugou', 'migu': 'migu'}
        for source in TuneHubMusicClient.ALLOWED_SITES:
            if source not in allowed_music_sources: continue
            if source in {'netease'}: search_urls.append(f"https://api.qijieya.cn/meting/?server={tunehub_to_meting_server_mapper[source]}&type=search&id={keyword}"); continue
            (source_default_rule := {'keyword': keyword, 'page': 1, 'limit': 20, 'timeout': 10.0}).update(rule); count = 0
            while self.search_size_per_source > count:
                (page_rule := copy.deepcopy(source_default_rule))['limit'] = str(page_size)
                page_rule['page'] = str(int(count // page_size) + 1)
                search_urls.append({'search_api': {'kuwo': self._tunehubkuwosearch, 'qq': self._tunehubqqsearch}[source], 'rule': page_rule})
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
            search_results = search_url['search_api'](**search_url['rule']) if isinstance(search_url, dict) else resp2json(self.get(search_url, **request_overrides))
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('id' not in search_result and 'url' not in search_result): continue
                if 'id' not in search_result: search_result['id'] = parse_qs(urlparse(str(search_result['url'])).query, keep_blank_values=True).get('id')[0]
                if 'source' not in search_result: search_result['source'] = parse_qs(urlparse(str(search_result['url'])).query, keep_blank_values=True).get('server')[0]
                song_info = SongInfo(source=self.source, root_source=search_result['source'], raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                tunehub_to_meting_server_mapper = {'netease': 'netease', 'qq': 'tencent', 'kuwo': 'kuwo', 'kugou': 'kugou', 'migu': 'migu'}
                if search_result['source'] in {'netease'}:
                    for br in TuneHubMusicClient.METING_API_MUSIC_QUALITIES:
                        download_url = f"https://api.qijieya.cn/meting/?server={tunehub_to_meting_server_mapper[search_result['source']]}&type=url&id={search_result['id']}&br={br}"
                        with suppress(Exception): download_url = self.session.head(download_url, timeout=10, allow_redirects=True, **request_overrides).url
                        cover_url: str = safeextractfromdict(search_result, ['pic'], '') or f"https://api.qijieya.cn/meting/?server={tunehub_to_meting_server_mapper[search_result['source']]}&type=pic&id={search_result['id']}"
                        with suppress(Exception): cover_url = self.session.head(cover_url, timeout=10, allow_redirects=True, **request_overrides).url
                        search_result['lrc'] = search_result.get('lrc') or f"https://api.qijieya.cn/meting/?server={tunehub_to_meting_server_mapper[search_result['source']]}&type=lrc&id={search_result['id']}"
                        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                        song_info = SongInfo(
                            raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(search_result.get('artist')), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                            file_size=download_url_status['file_size'], identifier=search_result['id'], duration_s=None, duration='-:-:-', lyric=None, cover_url=cover_url, download_url=download_url_status['download_url'], download_url_status=download_url_status, root_source=search_result['source'],
                        )
                        song_info.root_source = 'qq' if song_info.root_source in {'tencent'} else song_info.root_source
                        if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
                elif search_result['source'] in {'kuwo', 'qq'}:
                    for quality in TuneHubMusicClient.TUNEHUB_API_MUSIC_QUALITIES:
                        data = {'quality': quality, 'ids': search_result['id'], 'platform': search_result['source']}
                        with suppress(Exception): (tune_resp := self.post('https://tunehub.sayqz.com/api/v1/parse?', timeout=10, data=data, **request_overrides)).raise_for_status()
                        if not locals().get('tune_resp') or not hasattr(locals().get('tune_resp'), 'text'): continue
                        download_url = safeextractfromdict((download_result := resp2json(resp=tune_resp)), ['data', 'data', 0, 'url'], ''); del tune_resp
                        if not download_url or not str(download_url).startswith('http'): continue
                        duration_in_secs = safeextractfromdict(download_result, ['data', 'data', 0, 'info', 'duration'], 0)
                        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                        song_info = SongInfo(
                            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(search_result.get('artist')), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=search_result['id'], 
                            duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=safeextractfromdict(download_result, ['data', 'data', 0, 'lyrics'], None), cover_url=safeextractfromdict(download_result, ['data', 'data', 0, 'cover'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, root_source=search_result['source'],
                        )
                        if str(song_info.lyric).startswith('http'): search_result['lrc'] = song_info.lyric; song_info.lyric = None
                        if song_info.lyric and song_info.lyric not in {'NULL'}: song_info.lyric = cleanlrc(song_info.lyric)
                        if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                # --lyric results
                try: (resp := self.get(search_result['lrc'], **request_overrides)).raise_for_status(); lyric, lyric_result = cleanlrc(resp.text), {'lyric': resp.text}; song_info.duration_s = extractdurationsecondsfromlrc(lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
                except Exception: lyric_result, lyric = dict(), 'NULL'
                song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
                song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
            # --update progress
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Error: {err})")
            self.logger_handle.error(f"{self.source}._search >>> {search_url} (Error: {err})", disable_print=self.disable_print)
        # return
        return song_infos