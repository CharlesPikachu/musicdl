'''
Function:
    Implementation of KugouMusicClient: http://www.kugou.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
import random
import base64
import hashlib
import warnings
import json_repair
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils.kugouutils import KugouMusicClientUtils, MUSIC_QUALITIES
from ..utils import legalizestring, byte2mb, resp2json, seconds2hms, usesearchheaderscookies, safeextractfromdict, optionalimport, cleanlrc, SongInfo
warnings.filterwarnings('ignore')


'''KugouMusicClient'''
class KugouMusicClient(BaseMusicClient):
    source = 'KugouMusicClient'
    def __init__(self, **kwargs):
        super(KugouMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_parsewithcggapi'''
    def _parsewithcggapi(self, file_hash: list, search_result: dict, request_overrides: dict = None):
        # init
        curl_cffi = optionalimport('curl_cffi')
        request_overrides = request_overrides or {}
        MUSIC_QUALITIES = ['lossless', 'exhigh', 'hires', 'standard', 'ogg']
        # safe fetch filesize func
        safe_fetch_filesize_func = lambda meta: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(str(meta.get('size', '0.00MB')).removesuffix('MB').strip()) if isinstance(meta, dict) else 0
        # parse
        for quality in MUSIC_QUALITIES:
            try:
                resp = curl_cffi.requests.get(f"https://music-api2.cenguigui.cn/?kg=&id={file_hash}&type=song&format=json&level={quality}", timeout=10, impersonate="chrome131", verify=False, **request_overrides)
                resp.raise_for_status()
                download_result = json_repair.loads(resp.text)
                if 'data' not in download_result or (safe_fetch_filesize_func(download_result['data']) < 1): continue
            except:
                continue
            download_url = safeextractfromdict(download_result, ['data', 'url'], '')
            if not download_url: continue
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)),
                singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(search_result.get('album_name')), ext=download_url.split('?')[0].split('.')[-1], 
                file_size=str(safeextractfromdict(download_result, ['data', 'size'], "")).removesuffix('MB').strip() + ' MB', identifier=file_hash, duration_s=safeextractfromdict(search_result, ['duration'], 0), 
                duration=seconds2hms(safeextractfromdict(search_result, ['duration'], 0)), lyric='NULL', cover_url=safeextractfromdict(download_result, ['data', 'pic'], ""), download_url=download_url, 
                download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, file_hash: str, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for imp_func in [self._parsewithcggapi]:
            try:
                song_info_flac = imp_func(file_hash, search_result, request_overrides)
                if song_info_flac.with_valid_download_url: break
            except:
                song_info_flac = SongInfo(source=self.source)
        return song_info_flac
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {"format": "json", "keyword": keyword, "showtype": 1, "page": 1, "pagesize": 10}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'http://mobilecdn.kugou.com/api/v3/search/song?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['pagesize'] = page_size
            page_rule['page'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        safe_fetch_filesize_func = lambda size: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(size.removesuffix('MB').strip()) if isinstance(size, str) else 0
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['data']['info']
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('hash' not in search_result): continue
                song_info = SongInfo(source=self.source)
                song_info_flac = self._parsewiththirdpartapis(file_hash=search_result['hash'], search_result=search_result, request_overrides=request_overrides)
                for quality in MUSIC_QUALITIES:
                    if song_info_flac.with_valid_download_url and song_info_flac.ext in ('flac',): song_info = song_info_flac; break
                    try:
                        per_request_overrides = copy.deepcopy(request_overrides)
                        if 'impersonate' not in per_request_overrides and self.enable_curl_cffi: per_request_overrides['impersonate'] = random.choice(self.cc_impersonates)
                        self._autosetproxies()
                        per_request_overrides['proxies'] = per_request_overrides.pop('proxies', None) or self.session.proxies
                        download_result: dict = KugouMusicClientUtils.getsongurl(self.session, hash_value=search_result['hash'], quality=quality, request_overrides=per_request_overrides, cookies=copy.deepcopy(request_overrides.get('cookies') or self.default_cookies))
                        download_url = safeextractfromdict(download_result, ['url'], '') or safeextractfromdict(download_result, ['backupUrl'], '')
                    except:
                        download_result, download_url = {}, None
                    if not download_url:
                        md5_hex = hashlib.md5((search_result['hash'] + 'kgcloudv2').encode("utf-8")).hexdigest()
                        try:
                            resp = self.get(f"https://trackercdn.kugou.com/i/v2/?cdnBackup=1&behavior=download&pid=1&cmd=21&appid=1001&hash={search_result['hash']}&key={md5_hex}", **request_overrides)
                            resp.raise_for_status()
                            download_result: dict = resp2json(resp)
                            download_url = (
                                safeextractfromdict(download_result, ['url'], '') or safeextractfromdict(download_result, ['backup_url'], '') or safeextractfromdict(download_result, ['backupUrl'], '') or 
                                safeextractfromdict(download_result, ['mp3Url'], '') or safeextractfromdict(download_result, ['backupMp3Url'], '')
                            )
                        except:
                            continue
                    if download_url and isinstance(download_url, (list, tuple)): download_url = list(download_url)[0]
                    if not download_url or not str(download_url).startswith('http'): continue
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['songname'], None) or safeextractfromdict(search_result, ['songname_original'], None) or safeextractfromdict(search_result, ['filename'], None)),
                        singers=legalizestring(safeextractfromdict(search_result, ['singername'], None)), album=legalizestring(safeextractfromdict(search_result, ['album_name'], None)), ext=download_result.get('extName') or download_url.split('?')[0].split('.')[-1] or 'mp3', file_size_bytes=download_result.get('fileSize', 0),
                        file_size=byte2mb(download_result.get('fileSize', 0)), identifier=search_result['hash'], duration_s=safeextractfromdict(search_result, ['duration'], 0), duration=seconds2hms(search_result.get('duration')), lyric='NULL', cover_url=safeextractfromdict(search_result, ['trans_param', 'union_cover'], ""),
                        download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                    )
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] != 'NULL') else song_info.ext
                    if song_info.cover_url and isinstance(song_info.cover_url, str): song_info.cover_url = song_info.cover_url.format(size=300)
                    if song_info_flac.with_valid_download_url and (safe_fetch_filesize_func(song_info.file_size) < safe_fetch_filesize_func(song_info_flac.file_size)): song_info = song_info_flac
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: song_info = song_info_flac
                if not song_info.with_valid_download_url: continue
                # --lyric results
                params = {'keyword': search_result.get('filename', ''), 'duration': search_result.get('duration', '99999'), 'hash': search_result['hash']}
                try:
                    resp = self.get('http://lyrics.kugou.com/search', params=params, **request_overrides)
                    resp.raise_for_status()
                    lyric_result = resp2json(resp=resp)
                    resp = self.get(f"http://lyrics.kugou.com/download?ver=1&client=pc&id={lyric_result['candidates'][0]['id']}&accesskey={lyric_result['candidates'][0]['accesskey']}&fmt=lrc&charset=utf8", **request_overrides)
                    resp.raise_for_status()
                    lyric_result['lyrics.kugou.com/download'] = resp2json(resp=resp)
                    lyric = lyric_result['lyrics.kugou.com/download']['content']
                    lyric = cleanlrc(base64.b64decode(lyric).decode('utf-8'))
                except:
                    lyric_result, lyric = dict(), 'NULL'
                song_info.raw_data['lyric'] = lyric_result
                song_info.lyric = lyric
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