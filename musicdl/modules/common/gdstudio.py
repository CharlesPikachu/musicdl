'''
Function:
    Implementation of GDStudioMusicClient: https://music.gdstudio.xyz/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
import time
import random
import hashlib
import requests
import json_repair
from contextlib import suppress
from rich.progress import Progress
from ..sources import BaseMusicClient
from urllib.parse import quote, urljoin
from ..utils import legalizestring, resp2json, usesearchheaderscookies, cleanlrc, SongInfo, AudioLinkTester, SongInfoUtils


'''GDStudioMusicClient'''
class GDStudioMusicClient(BaseMusicClient):
    source = 'GDStudioMusicClient'
    MUSIC_QUALITIES = [999, 740, 320, 192, 128]
    SUPPORTED_SITES = ['netease', 'kuwo', 'joox', 'bilibili', 'apple', 'spotify', 'tidal', 'qobuz', 'ytmusic', 'tencent'] # 'kugou', 'ximalaya', 'migu'
    SITE_TO_API_MAPPER = {
        'netease': 'https://music.gdstudio.xyz/api.php', 'tencent': 'https://music.gdstudio.xyz/api.php', 'tidal': 'https://music.gdstudio.xyz/api.php', 'spotify': 'https://music.gdstudio.xyz/api.php', 'kuwo': 'https://music.gdstudio.xyz/api.php', 'bilibili': 'https://music.gdstudio.xyz/api.php', 'apple': 'https://music.gdstudio.xyz/api.php', 
        'migu': 'https://music-api-cn.gdstudio.xyz/api.php', 'kugou': 'https://music-api-cn.gdstudio.xyz/api.php', 'ximalaya': 'https://music-api-cn.gdstudio.xyz/api.php', 'joox': 'https://music-api-hk.gdstudio.xyz/api.php', 'qobuz': 'https://music-api-us.gdstudio.xyz/api.php', 'ytmusic': 'https://music-api-us.gdstudio.xyz/api.php',
    }
    def __init__(self, **kwargs):
        self.allowed_music_sources = list(set(kwargs.pop('allowed_music_sources', GDStudioMusicClient.SUPPORTED_SITES[:-2])))
        super(GDStudioMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'}
        self.default_download_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_yieldcallback'''
    def _yieldcallback(self):
        return f"jQuery{''.join([str(random.randint(0, 9)) for _ in range(21)])}_{int(time.time() * 1000)}"
    '''_yieldcrc32'''
    def _yieldcrc32(self, id_value: str, hostname: str = 'music.gdstudio.xyz', version: str = "2025.11.4"):
        # timestamp
        with suppress(Exception): (resp := self.get('https://www.ximalaya.com/revision/time')).raise_for_status()
        ts9 = str(int(time.time() * 1000) if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') else resp.text.strip())[:9]
        # version
        ver_padded = "".join([p if len(p) != 1 else "0" + p for p in version.split(".")])
        # src
        src = f"{hostname}|{ver_padded}|{ts9}|{quote(str(id_value))}"
        # return
        return hashlib.md5(src.encode("utf-8")).hexdigest()[-8:].upper()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, allowed_music_sources = rule or {}, request_overrides or {}, copy.deepcopy(self.allowed_music_sources)
        (default_rule := {'types': 'search', 'count': self.search_size_per_page, 'pages': '1', 'name': keyword}).update(rule)
        # construct search urls
        search_urls, page_size = [], self.search_size_per_page
        make_base_rule_func = lambda source, page: {**copy.deepcopy(default_rule), 'source': source, 'pages': str(page), 'count': str(page_size), 's': self._yieldcrc32(keyword)}
        make_post_req_func = lambda api_url, rule: {'url': api_url, 'data': rule, 'params': {'callback': self._yieldcallback()}, 'method': 'post'}
        make_get_req_func = lambda api_url, rule: {'url': api_url, 'params': {**rule, 'callback': self._yieldcallback(), '_': str(int(time.time() * 1000))}, 'method': 'get'}
        for source in GDStudioMusicClient.SUPPORTED_SITES:
            if source not in allowed_music_sources: continue
            is_post, count = (api_url := GDStudioMusicClient.SITE_TO_API_MAPPER[source]) in {'https://music.gdstudio.xyz/api.php'}, 0
            while self.search_size_per_source > count:
                rule = make_base_rule_func(source, str(int(count // page_size) + 1))
                search_urls.append(make_post_req_func(api_url, rule) if is_post else make_get_req_func(api_url, rule))
                count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = None, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, search_meta = copy.deepcopy(request_overrides or {}), copy.deepcopy(search_url)
        self.default_headers, search_url, method = copy.deepcopy(self.default_headers), search_meta.pop('url'), search_meta.pop('method')
        # successful
        try:
            # --search results
            resp: requests.Response = getattr(self, method)(search_url, **search_meta, **request_overrides)
            for search_result in json_repair.loads(resp.text[resp.text.index('(')+1: resp.text.rindex(')')]):
                # --download results
                if (not isinstance(search_result, dict)) or ('id' not in search_result) or ('url_id' not in search_result) or ('source' not in search_result): continue
                song_info, song_id = SongInfo(source=self.source, root_source=search_result['source']), search_result['id']
                for br in GDStudioMusicClient.MUSIC_QUALITIES:
                    data_json = {'types': 'url', 'id': song_id, 'source': search_result['source'], 'br': br, 's': self._yieldcrc32(song_id)}; params = {'callback': self._yieldcallback()}
                    with suppress(Exception): (resp := self.post(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], params=params, data=data_json, **request_overrides)).raise_for_status() if method == 'post' else (resp := self.get(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], params={**params, **data_json, '_': str(int(time.time() * 1000))}, **request_overrides)).raise_for_status()
                    if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                    if not (download_url := (download_result := json_repair.loads(resp.text[resp.text.index('(')+1: resp.text.rindex(')')])).get('url')): continue
                    download_url = urljoin(f'https://music.gdstudio.xyz/', download_url) if not str(download_url).startswith('http') else download_url
                    download_url = f'https://music-proxy.gdstudio.org/{download_url}' if search_result['source'] in {'bilibili'} else download_url
                    download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                    duration_in_secs = SongInfoUtils.estimatedurationwithfilesizebr(download_result.get('size', 0), download_result.get('br', br), return_seconds=True)
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join(search_result.get('artist') or [])), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                        file_size=download_url_status['file_size'], identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=None, download_url=download_url_status['download_url'], download_url_status=download_url_status, root_source=search_result['source'],
                    )
                    if search_result['source'] in {'bilibili'}: song_info.download_url_status['ok'] = True if song_info.download_url_status['file_size_bytes'] > 0 else False # use proxy url, general test method will fail
                    del resp; song_info.ext = 'm4a' if song_info.ext in {'m4s', 'mp4'} else song_info.ext
                    if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                # --lyric results
                data_json = {'types': 'lyric', 'id': search_result.get('lyric_id'), 'source': search_result['source'], 's': self._yieldcrc32(str(search_result.get('lyric_id')))}
                try:
                    (resp := self.post(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], data=data_json, params={'callback': self._yieldcallback()}, timeout=10, **request_overrides)).raise_for_status() if method == 'post' else (resp := self.get(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], params={**{'callback': self._yieldcallback()}, **data_json, '_': str(int(time.time() * 1000))}, timeout=10, **request_overrides)).raise_for_status()
                    lyric_result = json_repair.loads(resp.text[resp.text.index('(')+1: resp.text.rindex(')')])
                    lyric = cleanlrc(lyric_result.get('lyric') or "") or cleanlrc(lyric_result.get('tlyric') or "") or 'NULL'
                except:
                    lyric_result, lyric = dict(), 'NULL'
                if not lyric or lyric in {'NULL', 'null', 'None', 'none'} or '歌词获取失败' in lyric:
                    params = {'artist_name': song_info.singers, 'track_name': song_info.song_name, 'album_name': song_info.album, 'duration': SongInfoUtils.estimatedurationwithfilelink(song_info.download_url, headers=self.default_download_headers, request_overrides=request_overrides)}
                    song_info.duration_s, song_info.duration = params['duration'], SongInfoUtils.seconds2hms(params['duration'])
                    with suppress(Exception): (resp := self.get(f'https://lrclib.net/api/get?', params=params, timeout=10, **request_overrides)).raise_for_status(); lyric_result = resp2json(resp=resp); lyric = cleanlrc(lyric_result.get('syncedLyrics') or "") or 'NULL'
                song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
                song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
                # --cover results
                if search_result['source'] in {'kuwo'}:
                    kuwo_cover_cdn_hosts = ["http://img1.kwcdn.kuwo.cn/star/albumcover/", "http://img2.kwcdn.kuwo.cn/star/albumcover/", "http://img3.kwcdn.kuwo.cn/star/albumcover/"]
                    song_info.cover_url = urljoin(kuwo_cover_cdn_hosts[0], '300/' + search_result.get('pic_id')[4:] if str(search_result.get('pic_id')).startswith('120/') else search_result.get('pic_id'))
                elif search_result['source'] in {'apple'}:
                    with suppress(Exception): song_info.cover_url = str(search_result['pic_id']).format(w=300, h=300)
                elif search_result['source'] in {'bilibili'}:
                    song_info.cover_url = search_result.get('pic_id') if str(search_result.get('pic_id')).startswith('http') else f"https:{search_result.get('pic_id')}"
                else:
                    data_json = {'types': 'pic', 'id': search_result.get('pic_id'), 'source': search_result['source'], 'size': 300, 's': self._yieldcrc32(str(search_result.get('pic_id')))}
                    with suppress(Exception): (resp := self.post(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], data=data_json, params={'callback': self._yieldcallback()}, timeout=10, **request_overrides)).raise_for_status() if method == 'post' else (resp := self.get(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], params={**{'callback': self._yieldcallback()}, **data_json, '_': str(int(time.time() * 1000))}, timeout=10, **request_overrides)).raise_for_status()
                    with suppress(Exception): song_info.cover_url = json_repair.loads(resp.text[resp.text.index('(')+1: resp.text.rindex(')')])['url']
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