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
import json_repair
from urllib.parse import quote
from rich.progress import Progress
from ..sources import BaseMusicClient
from ..utils import legalizestring, resp2json, usesearchheaderscookies, byte2mb, estimatedurationwithfilesizebr, estimatedurationwithfilelink, seconds2hms, safeextractfromdict, cleanlrc, SongInfo, AudioLinkTester


'''GDStudioMusicClient'''
class GDStudioMusicClient(BaseMusicClient):
    source = 'GDStudioMusicClient'
    SUPPORTED_SITES = ['spotify', 'netease', 'kuwo', 'tidal', 'qobuz', 'joox', 'bilibili', 'apple', 'tencent', 'ytmusic'] # 'kugou', 'ximalaya', 'migu'
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
        random_num = ''.join([str(random.randint(0, 9)) for _ in range(21)])
        timestamp = int(time.time() * 1000)
        return f"jQuery{random_num}_{timestamp}"
    '''_yieldcrc32'''
    def _yieldcrc32(self, id_value: str, hostname: str = 'music.gdstudio.xyz', version: str = "2025.11.4"):
        # timestamp
        try: (resp := self.get('https://www.ximalaya.com/revision/time')).raise_for_status(); ts_ms = resp.text.strip()
        except Exception: ts_ms = int(time.time() * 1000)
        ts9 = str(ts_ms)[:9]
        # version
        parts = version.split("."); padded = [p if len(p) != 1 else "0" + p for p in parts]; ver_padded = "".join(padded)
        # id
        id_str = quote(str(id_value))
        # src
        src = f"{hostname}|{ver_padded}|{ts9}|{id_str}"
        # return
        return hashlib.md5(src.encode("utf-8")).hexdigest()[-8:].upper()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        allowed_music_sources = copy.deepcopy(self.allowed_music_sources)
        # search rules
        default_rule = {'types': 'search', 'count': self.search_size_per_page, 'pages': '1', 'name': keyword}
        default_rule.update(rule)
        # construct search urls based on search rules
        search_urls, page_size = [], self.search_size_per_page
        for source in GDStudioMusicClient.SUPPORTED_SITES:
            if source not in allowed_music_sources: continue
            source_default_rule = copy.deepcopy(default_rule)
            source_default_rule['source'], count = source, 0
            while self.search_size_per_source > count:
                if GDStudioMusicClient.SITE_TO_API_MAPPER[source] in {'https://music.gdstudio.xyz/api.php'}:
                    page_rule_post = copy.deepcopy(source_default_rule)
                    page_rule_post['pages'] = str(int(count // page_size) + 1); page_rule_post['count'] = str(page_size); page_rule_post['s'] = self._yieldcrc32(keyword)
                    search_urls.append({'url': GDStudioMusicClient.SITE_TO_API_MAPPER[source], 'data': page_rule_post, 'params': {'callback': self._yieldcallback()}, 'method': 'post'})
                else:
                    page_rule_get = copy.deepcopy(source_default_rule)
                    page_rule_get['pages'] = str(int(count // page_size) + 1); page_rule_get['count'] = str(page_size); page_rule_get['s'] = self._yieldcrc32(keyword); page_rule_get['callback'] = self._yieldcallback(); page_rule_get['_'] = str(int(time.time() * 1000))
                    search_urls.append({'url': GDStudioMusicClient.SITE_TO_API_MAPPER[source], 'params': page_rule_get, 'method': 'get'})
                count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = None, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        search_meta = copy.deepcopy(search_url)
        search_url, method = search_meta.pop('url'), search_meta.pop('method')
        self.default_headers, request_overrides = copy.deepcopy(self.default_headers), copy.deepcopy(request_overrides)
        # successful
        try:
            # --search results
            (resp := getattr(self, method)(search_url, **search_meta, **request_overrides)).raise_for_status()
            search_results = json_repair.loads(resp.text[resp.text.index('(')+1: resp.text.rindex(')')])
            for search_result in search_results:
                # --download results
                if (not isinstance(search_result, dict)) or ('id' not in search_result) or ('url_id' not in search_result) or ('source' not in search_result): continue
                song_info, song_id = SongInfo(source=self.source, root_source=search_result['source']), search_result['id']
                for br in [999, 740, 320, 192, 128]: # 999 and 740 mean lossless
                    params = {'callback': self._yieldcallback()}; data_json = {'types': 'url', 'id': song_id, 'source': search_result['source'], 'br': br, 's': self._yieldcrc32(song_id)}
                    try: (resp := self.post(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], params=params, data=data_json, **request_overrides)).raise_for_status() if method == 'post' else (resp := self.get(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], params={**params, **data_json, '_': str(int(time.time() * 1000))}, **request_overrides)).raise_for_status()
                    except Exception: continue
                    download_result = json_repair.loads(resp.text[resp.text.index('(')+1: resp.text.rindex(')')])
                    if not (download_url := download_result.get('url')): continue
                    if not str(download_url).startswith('http'): download_url = f'https://music.gdstudio.xyz/' + download_url
                    if search_result['source'] in {'bilibili'}: download_url = f'https://music-proxy.gdstudio.org/{download_url}'
                    download_url_status = self.audio_link_tester.test(download_url, request_overrides); download_url = download_url_status['final_url']
                    duration_in_secs = estimatedurationwithfilesizebr(download_result.get('size', 0), download_result.get('br', br), return_seconds=True)
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)), singers=legalizestring(', '.join(safeextractfromdict(search_result, ['artist'], []) or [])), 
                        album=legalizestring(safeextractfromdict(search_result, ['album'], None)), ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=download_result.get('size'), file_size=byte2mb(download_result.get('size', 0)), identifier=song_id, duration_s=duration_in_secs,
                        duration=seconds2hms(duration_in_secs), lyric=None, cover_url=None, download_url=download_url, download_url_status=download_url_status, root_source=search_result['source'],
                    )
                    if search_result['source'] in {'bilibili'}: song_info.download_url_status['ok'] = True if song_info.download_url_status['clen'] > 0 else False # use proxy url, general test method will fail
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: continue
                song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                if song_info.ext in {'m4s', 'mp4'}: song_info.ext = 'm4a'
                if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
                # --lyric results
                try:
                    data_json = {'types': 'lyric', 'id': search_result['lyric_id'], 'source': search_result['source'], 's': self._yieldcrc32(search_result['lyric_id'])}
                    if method == 'post': (resp := self.post(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], data=data_json, params={'callback': self._yieldcallback()}, **request_overrides)).raise_for_status()
                    else: (resp := self.get(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], params={**{'callback': self._yieldcallback()}, **data_json, '_': str(int(time.time() * 1000))}, **request_overrides)).raise_for_status()
                    lyric_result = json_repair.loads(resp.text[resp.text.index('(')+1: resp.text.rindex(')')])
                    lyric = cleanlrc(lyric_result.get('lyric') or "") or cleanlrc(lyric_result.get('tlyric') or "") or 'NULL'
                except:
                    lyric_result, lyric = dict(), 'NULL'
                if not lyric or lyric == 'NULL':
                    try:
                        params = {'artist_name': song_info.singers, 'track_name': song_info.song_name, 'album_name': song_info.album, 'duration': estimatedurationwithfilelink(song_info.download_url, headers=self.default_download_headers, request_overrides=request_overrides)}
                        (resp := self.get(f'https://lrclib.net/api/get?', params=params, **request_overrides)).raise_for_status()
                        lyric_result = resp2json(resp=resp); lyric = cleanlrc(lyric_result.get('syncedLyrics') or "") or 'NULL'
                        song_info.duration_s, song_info.duration = params['duration'], seconds2hms(params['duration'])
                    except:
                        lyric_result, lyric = dict(), 'NULL'
                song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
                song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
                # --cover results
                if search_result['source'] in {'kuwo'}:
                    cdn_hosts = ["http://img1.kwcdn.kuwo.cn/star/albumcover/", "http://img2.kwcdn.kuwo.cn/star/albumcover/", "http://img3.kwcdn.kuwo.cn/star/albumcover/"]
                    try: search_result['pic_id'] = '300/' + search_result['pic_id'][4:] if str(search_result['pic_id']).startswith('120/') else search_result['pic_id']; song_info.cover_url = cdn_hosts[0] + search_result['pic_id']
                    except Exception: pass
                elif search_result['source'] in {'apple'}:
                    try: song_info.cover_url = search_result['pic_id'].format(w=300, h=300)
                    except Exception: pass
                elif search_result['source'] in {'bilibili'}:
                    try: song_info.cover_url = search_result['pic_id']; song_info.cover_url = f'https:{song_info.cover_url}' if not song_info.cover_url.startswith('http') else song_info.cover_url
                    except Exception: pass
                else:
                    try:
                        data_json = {'types': 'pic', 'id': search_result['pic_id'], 'source': search_result['source'], 'size': 300, 's': self._yieldcrc32(search_result['pic_id'])}
                        (resp := self.post(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], data=data_json, params={'callback': self._yieldcallback()}, **request_overrides)).raise_for_status() if method == 'post' else (resp := self.get(GDStudioMusicClient.SITE_TO_API_MAPPER[search_result['source']], params={**{'callback': self._yieldcallback()}, **data_json, '_': str(int(time.time() * 1000))}, **request_overrides)).raise_for_status()
                        cover_result = json_repair.loads(resp.text[resp.text.index('(')+1: resp.text.rindex(')')]); song_info.cover_url = cover_result['url']
                    except Exception: pass
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