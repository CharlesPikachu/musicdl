'''
Function:
    Implementation of NeteaseMusicClient: https://music.163.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import json
import copy
import base64
import random
import warnings
from .base import BaseMusicClient
from rich.progress import Progress
from ..utils.neteaseutils import EapiCryptoUtils, MUSIC_QUALITIES, DEFAULT_COOKIES
from ..utils import resp2json, seconds2hms, legalizestring, safeextractfromdict, usesearchheaderscookies, extractdurationsecondsfromlrc, cleanlrc, SongInfo
warnings.filterwarnings('ignore')


'''NeteaseMusicClient'''
class NeteaseMusicClient(BaseMusicClient):
    source = 'NeteaseMusicClient'
    def __init__(self, **kwargs):
        super(NeteaseMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Referer': 'https://music.163.com/',
        }
        self.default_download_headers = {}
        self.default_headers = self.default_search_headers
        self.default_search_cookies = self.default_search_cookies or DEFAULT_COOKIES
        self.default_download_cookies = self.default_download_cookies or DEFAULT_COOKIES
        self._initsession()
    '''_parsewithxiaoqinapi'''
    def _parsewithxiaoqinapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result['id']
        # parse
        for quality in MUSIC_QUALITIES:
            try:
                resp = self.post('https://wyapi-eo.toubiec.cn/api/getSongUrl', json={'id': song_id, 'level': quality}, timeout=10, verify=False, **request_overrides)
                resp.raise_for_status()
                download_result = resp2json(resp=resp)
                if ('data' not in download_result) or (not download_result['data']): continue
            except:
                continue
            download_url: str = safeextractfromdict(download_result, ['data', 'url'], '')
            if not download_url or not download_url.startswith('http'): continue
            ext = download_url.split('?')[0].split('.')[-1]
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': quality}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)), singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), 
                album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), ext=ext, file_size='NULL', identifier=search_result['id'], duration_s=search_result.get('dt', 0) / 1000 if isinstance(search_result.get('dt', 0), (int, float)) else 0, duration=seconds2hms(search_result.get('dt', 0) / 1000 if isinstance(search_result.get('dt', 0), (int, float)) else 0), 
                lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsewithcggapi'''
    def _parsewithcggapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result['id']
        # safe fetch filesize func
        safe_fetch_filesize_func = lambda meta: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(str(meta.get('size', '0.00MB')).removesuffix('MB').strip()) if isinstance(meta, dict) else 0
        # to seconds func
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse
        for quality in MUSIC_QUALITIES:
            for prefix in ['api-v2', 'api-v1', 'api', 'player']:
                try:
                    resp = self.get(url=f'https://{prefix}.cenguigui.cn/api/netease/music_v1.php?id={song_id}&type=json&level={quality}', timeout=10, **request_overrides)
                    resp.raise_for_status()
                    download_result = resp2json(resp=resp)
                    if 'data' not in download_result or (safe_fetch_filesize_func(download_result['data']) < 1): continue
                    break
                except:
                    continue
            download_url: str = safeextractfromdict(download_result, ['data', 'url'], '')
            if not download_url or not download_url.startswith('http'): continue
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)),
                singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), 
                ext=download_url.split('?')[0].split('.')[-1], file_size=str(safeextractfromdict(download_result, ['data', 'size'], "")).removesuffix('MB').strip() + ' MB', identifier=search_result['id'],
                duration_s=to_seconds_func(safeextractfromdict(download_result, ['data', 'duration'], "")), duration=seconds2hms(to_seconds_func(safeextractfromdict(download_result, ['data', 'duration'], ""))),
                lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], "")), cover_url=safeextractfromdict(download_result, ['data', 'pic'], ""), download_url=download_url,
                download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsewithbugpkapi'''
    def _parsewithbugpkapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result['id']
        # safe fetch filesize func
        safe_fetch_filesize_func = lambda meta: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(str(meta.get('size', '0.00MB')).removesuffix('MB').strip()) if isinstance(meta, dict) else 0
        # parse
        for quality in MUSIC_QUALITIES:
            try:
                resp = self.get(f'https://api.bugpk.com/api/163_music?ids={song_id}&level={quality}&type=json', timeout=10, **request_overrides)
                resp.raise_for_status()
                download_result = resp2json(resp=resp)
                if 'url' not in download_result or (safe_fetch_filesize_func(download_result) < 1): continue
            except:
                continue
            download_url: str = safeextractfromdict(download_result, ['url'], '')
            if not download_url or not download_url.startswith('http'): continue
            lyric = cleanlrc(safeextractfromdict(download_result, ['lyric'], "")) or 'NULL'
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': quality}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['name'], None)), singers=legalizestring(download_result.get('ar_name')), 
                album=legalizestring(safeextractfromdict(download_result, ['al_name'], None)), ext=download_url.split('?')[0].split('.')[-1], file_size=str(safeextractfromdict(download_result, ['size'], "")).removesuffix('MB').strip() + ' MB', identifier=search_result['id'], 
                duration_s=search_result.get('dt', 0) / 1000 if isinstance(search_result.get('dt', 0), (int, float)) else 0, duration=seconds2hms(search_result.get('dt', 0) / 1000 if isinstance(search_result.get('dt', 0), (int, float)) else 0), lyric=lyric,
                cover_url=safeextractfromdict(download_result, ['pic'], ""), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            if song_info.album == 'NULL': song_info.album = legalizestring(safeextractfromdict(search_result, ['al', 'name'], None))
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsewithxianyuwapi'''
    def _parsewithxianyuwapi(self, search_result: dict, request_overrides: dict = None):
        # init
        decrypt_func = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        request_overrides, song_id, song_info = request_overrides or {}, search_result['id'], SongInfo(source=self.source)
        REQUEST_KEYS = ['c2stOTUwZTc4MTNjMzhjMmUzMWQzOWQ4NzlkMzIwNDg4OTU=', 'c2stNjJjZGIwM2UyMjcwZWIzOTY4Y2NhNzg4MTM5OWY0MTI=']
        # parse
        resp = self.get(f'https://apii.xianyuw.cn/api/v1/163-music-search?id={song_id}&key={decrypt_func(random.choice(REQUEST_KEYS))}&no_url=0&br=hires', **request_overrides)
        resp.raise_for_status()
        download_result = resp2json(resp=resp)
        download_url: str = download_result['data']['url']
        if not download_url or not download_url.startswith('http'): return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': 'hires'}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'title'], None)),
            singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'author'], "")).replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), 
            ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=search_result['id'], duration='-:-:-', lyric='NULL', cover_url=safeextractfromdict(download_result, ['data', 'cover'], ""), 
            download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        if song_info.album == 'NULL': song_info.album = legalizestring(safeextractfromdict(search_result, ['al', 'name'], None))
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        cookies = self.default_cookies or request_overrides.get('cookies')
        if cookies and (cookies != DEFAULT_COOKIES): return SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        for imp_func in [self._parsewithcggapi, self._parsewithxiaoqinapi, self._parsewithxianyuwapi, self._parsewithbugpkapi]:
            try:
                song_info_flac = imp_func(search_result, request_overrides)
                if song_info_flac.with_valid_download_url: break
            except:
                song_info_flac = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
        return song_info_flac
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {'s': keyword, 'type': 1, 'limit': 10, 'offset': 0}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://music.163.com/api/cloudsearch/pc'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['limit'] = page_size
            page_rule['offset'] = int(count // page_size) * page_size
            search_urls.append({'url': base_url, 'data': page_rule})
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = {}, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        search_meta = copy.deepcopy(search_url)
        search_url = search_meta.pop('url')
        # successful
        try:
            # --search results
            resp = self.post(search_url, **search_meta, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['result']['songs']
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('id' not in search_result): continue
                song_info = SongInfo(source=self.source, raw_data={'quality': MUSIC_QUALITIES[-1]})
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
                # ----parse from high to low music quality until successful fetch
                for quality_idx, quality in enumerate(MUSIC_QUALITIES):
                    if quality_idx >= MUSIC_QUALITIES.index(song_info_flac.raw_data['quality']) and song_info_flac.with_valid_download_url: song_info = song_info_flac; break
                    params = {'ids': [search_result['id']], 'level': quality, 'encodeType': 'flac', 'header': json.dumps({"os": "pc", "appver": "", "osver": "", "deviceId": "pyncm!", "requestId": str(random.randrange(20000000, 30000000))})}
                    if quality == 'sky': params['immerseType'] = 'c51'
                    params = EapiCryptoUtils.encryptparams(url='https://interface3.music.163.com/eapi/song/enhance/player/url/v1', payload=params)
                    cookies = {"os": "pc", "appver": "", "osver": "", "deviceId": "pyncm!"}
                    cookies.update(copy.deepcopy(self.default_cookies))
                    try:
                        resp = self.post('https://interface3.music.163.com/eapi/song/enhance/player/url/v1', data={"params": params}, cookies=cookies, **request_overrides)
                        resp.raise_for_status()
                        download_result: dict = resp2json(resp)
                        if ('data' not in download_result) or (not download_result['data']): continue
                    except:
                        continue
                    download_url: str = safeextractfromdict(download_result, ['data', 0, 'url'], '')
                    if not download_url: continue
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'quality': quality}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)),
                        singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['ar'], []) or []) if isinstance(singer, dict) and singer.get('name')])), album=legalizestring(safeextractfromdict(search_result, ['al', 'name'], None)), 
                        ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=search_result['id'], duration_s=search_result.get('dt', 0) / 1000 if isinstance(search_result.get('dt', 0), (int, float)) else 0,
                        duration=seconds2hms(search_result.get('dt', 0) / 1000 if isinstance(search_result.get('dt', 0), (int, float)) else 0), lyric=None, cover_url=safeextractfromdict(search_result, ['al', 'picUrl'], None), 
                        download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                    )
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] != 'NULL') else song_info.ext
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: song_info = song_info_flac
                if not song_info.with_valid_download_url: continue
                # --lyric results
                data = {'id': search_result['id'], 'cp': 'false', 'tv': '0', 'lv': '0', 'rv': '0', 'kv': '0', 'yv': '0', 'ytv': '0', 'yrv': '0'}
                try:
                    resp = self.post('https://interface3.music.163.com/api/song/lyric', data=data, **request_overrides)
                    resp.raise_for_status()
                    lyric_result: dict = resp2json(resp)
                    lyric = safeextractfromdict(lyric_result, ['lrc', 'lyric'], 'NULL')
                    lyric = 'NULL' if not lyric else cleanlrc(lyric)
                except:
                    lyric_result, lyric = dict(), 'NULL'
                song_info.raw_data['lyric'] = lyric_result
                song_info.lyric = lyric
                if not song_info.duration or song_info.duration == '-:-:-': song_info.duration = seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
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