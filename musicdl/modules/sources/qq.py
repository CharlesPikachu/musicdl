'''
Function:
    Implementation of QQMusicClient: https://y.qq.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import json
import random
import base64
from .base import BaseMusicClient
from rich.progress import Progress
from ..utils.hosts import QQ_MUSIC_HOSTS
from pathvalidate import sanitize_filepath
from urllib.parse import urlparse, parse_qs
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils.qqutils import QQMusicClientUtils, SearchType, Credential, ThirdPartVKeysAPISongFileType, SongFileType, EncryptedSongFileType
from ..utils import touchdir, resp2json, seconds2hms, legalizestring, safeextractfromdict, usesearchheaderscookies, extractdurationsecondsfromlrc, useparseheaderscookies, obtainhostname, hostmatchessuffix, optionalimport, cleanlrc, SongInfo, AudioLinkTester


'''QQMusicClient'''
class QQMusicClient(BaseMusicClient):
    source = 'QQMusicClient'
    def __init__(self, use_encrypted_endpoint: bool = False, **kwargs):
        super(QQMusicClient, self).__init__(**kwargs)
        self.use_encrypted_endpoint = use_encrypted_endpoint
        self.default_search_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36', 'Referer': 'https://y.qq.com/', 'Origin': 'https://y.qq.com/',}
        self.default_parse_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36', 'Referer': 'https://y.qq.com/', 'Origin': 'https://y.qq.com/',}
        self.default_download_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36', 'Referer': 'http://y.qq.com',}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {'searchid': QQMusicClientUtils.randomsearchid(), 'query': keyword, 'search_type': SearchType.SONG.value, 'num_per_page': self.search_size_per_page, 'page_num': 1, 'highlight': 1, 'grp': 1}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = QQMusicClientUtils.enc_endpoint if self.use_encrypted_endpoint else QQMusicClientUtils.endpoint
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['num_per_page'] = page_size
            page_rule['page_num'] = int(count // page_size) + 1
            payload = QQMusicClientUtils.buildrequestdata(params=page_rule, module="music.search.SearchCgiService", method="DoSearchForQQMusicMobile", credential=Credential().fromcookiesdict(self.default_cookies or request_overrides.get('cookies', {})))
            search_urls.append({'url': base_url, 'data': json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")})
            if self.use_encrypted_endpoint: search_urls[-1]['params'] = {"sign": QQMusicClientUtils.sign(payload)}
            count += page_size
        # return
        return search_urls
    '''_parsewithvkeysapi'''
    def _parsewithvkeysapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result.get('mid') or search_result.get('songmid')
        safe_obtain_filesize_func = lambda meta: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(str(meta.get('size', '0.00MB')).removesuffix('MB').strip()) if isinstance(meta, dict) else 0
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse
        for quality in list(ThirdPartVKeysAPISongFileType.ID_TO_NAME.value.keys())[::-1]:
            try: (resp := self.get(f"https://api.vkeys.cn/v2/music/tencent/geturl?mid={song_id}&quality={quality}", timeout=10, **request_overrides)).raise_for_status()
            except Exception: break
            if (not safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'url'], None)) or (safe_obtain_filesize_func(download_result['data']) < 0.01): continue
            if not (download_url := download_result['data']['url']) or not str(download_url).startswith('http'): continue
            try: (resp := self.get(f"https://api.vkeys.cn/v2/music/tencent/lyric?mid={song_id}", timeout=10, **request_overrides)).raise_for_status(); lyric_result = resp2json(resp=resp)
            except Exception: lyric_result = {}
            duration_in_secs = safeextractfromdict(download_result, ['data', 'interval'], 0)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': lyric_result}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'song'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'singer'], '') or '').replace('/', ', ')), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url.split('?')[0].split('.')[-1], 
                file_size_bytes=None, file_size=str(safeextractfromdict(download_result, ['data', 'size'], '0.00')).removesuffix('MB').strip() + ' MB', identifier=song_id, duration_s=to_seconds_func(duration_in_secs), duration=seconds2hms(to_seconds_func(duration_in_secs)), lyric=cleanlrc(safeextractfromdict(lyric_result, ['data', 'lrc'], 'NULL')) or 'NULL', cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url, 
                download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
            elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsewithlittleyouziapi'''
    def _parsewithlittleyouziapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result.get('mid') or search_result.get('songmid')
        # parse
        for quality in range(0, 11):
            try: (resp := self.get(f"https://www.littleyouzi.com/api/v2/qqmusic?mid={song_id}&quality={quality}", timeout=10, **request_overrides)).raise_for_status()
            except Exception: break
            download_url: str = safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 'audio'], '')
            if not download_url or not str(download_url).startswith('http'): continue
            try: (resp := self.get(f"https://www.littleyouzi.com/api/v2/qqmusic?mid={song_id}&lyrics=true", timeout=10, **request_overrides)).raise_for_status(); lyric_result = resp2json(resp=resp)
            except Exception: lyric_result = {}
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': lyric_result}, source=self.source, song_name=legalizestring(search_result.get('title', None) or search_result.get('songname', None)), singers=legalizestring(', '.join([singer.get('name', '') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name', None)])),
                album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname')), ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=None, file_size=None, identifier=song_id, duration_s=search_result.get('interval', 0), duration=seconds2hms(search_result.get('interval', 0)), lyric=cleanlrc(lyric_result.get('content') or 'NULL'),
                cover_url=None, download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
            elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsewithnkiapi'''
    def _parsewithnkiapi(self, search_result: dict, request_overrides: dict = None):
        # init
        decrypt_func, curl_cffi = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8'), optionalimport('curl_cffi')
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        REQUEST_KEYS = ['MjhmZWNlOTI1NDM5YjA1Mjc5MmE5Nzk4OWM4NzBjZWQzODAzYTcxYzZiNTM0ZjcxZTVhNTMzMzhiMmQzMWVmOA==', 'YzRjNGY1ZmMzNmJhZDRjYWNiOTg4MzllMTRmZWE0MDI3N2IzNWVhMmViMWJhYmRhZDdiYmRlMTI4NDAwZjNiMQ==']
        # parse
        try: (resp := curl_cffi.requests.get(f'https://api.nki.pw/API/music_open_api.php?mid={song_id}&apikey={decrypt_func(random.choice(REQUEST_KEYS))}', timeout=10, impersonate="chrome131", verify=False, **request_overrides)).raise_for_status()
        except Exception: (resp := self.get(f'https://api.nki.pw/API/music_open_api.php?mid={song_id}&apikey={decrypt_func(random.choice(REQUEST_KEYS))}', timeout=10, **request_overrides)).raise_for_status()
        download_url: str = (download_result := resp2json(resp=resp)).get('song_play_url_sq') or download_result.get('song_play_url_pq') or download_result.get('song_play_url_accom') or download_result.get('song_play_url_hq') or download_result.get('song_play_url') or download_result.get('song_play_url_standard') or download_result.get('song_play_url_fq')
        if not download_url or not str(download_url).startswith('http'): return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('song_name')), singers=legalizestring(download_result.get('singer_name')), album=legalizestring(download_result.get('album_name')), 
            ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=None, file_size=None, identifier=song_id, duration=download_result.get('duration', '-:-:-'), lyric=cleanlrc(download_result.get('song_lyric', 'NULL')) or 'NULL', cover_url=download_result.get('album_pic', None), 
            download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
        elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
        # return
        return song_info
    '''_parsewithtangapi'''
    def _parsewithtangapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        # parse
        (resp := self.get(f'https://tang.api.s01s.cn/music_open_api.php?mid={song_id}', **request_overrides)).raise_for_status()
        download_url: str = (download_result := resp2json(resp=resp)).get('song_play_url_sq') or download_result.get('song_play_url_pq') or download_result.get('song_play_url_accom') or download_result.get('song_play_url_hq') or download_result.get('song_play_url') or download_result.get('song_play_url_standard') or download_result.get('song_play_url_fq')
        if not download_url or not str(download_url).startswith('http'): return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(download_result.get('song_name')), singers=legalizestring(download_result.get('singer_name')), album=legalizestring(download_result.get('album_name')), 
            ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=None, file_size=None, identifier=song_id, duration=download_result.get('duration', '-:-:-'), lyric=cleanlrc(download_result.get('song_lyric', 'NULL')) or 'NULL', cover_url=download_result.get('album_pic', None), 
            download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
        elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
        # return
        return song_info
    '''_parsewithxianyuwapi'''
    def _parsewithxianyuwapi(self, search_result: dict, request_overrides: dict = None):
        # init
        decrypt_func, REQUEST_KEYS = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8'), ['c2stOTUwZTc4MTNjMzhjMmUzMWQzOWQ4NzlkMzIwNDg4OTU=', 'c2stNjJjZGIwM2UyMjcwZWIzOTY4Y2NhNzg4MTM5OWY0MTI=']
        request_overrides, song_id, song_info = request_overrides or {}, search_result.get('mid') or search_result.get('songmid'), SongInfo(source=self.source)
        # parse
        (resp := self.get(f'https://apii.xianyuw.cn/api/v1/qq-music-search?id={song_id}&key={decrypt_func(random.choice(REQUEST_KEYS))}&no_url=0&br=hires', **request_overrides)).raise_for_status()
        download_url: str = (download_result := resp2json(resp=resp))['data']['url']
        if not download_url or not str(download_url).startswith('http'): return song_info
        lyric = cleanlrc(safeextractfromdict(download_result, ['data', 'lrc'], 'NULL')) or 'NULL'
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'title'], None)), singers=legalizestring(str(safeextractfromdict(download_result, ['data', 'author'], '')).replace('/', ', ')), 
            album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=None, file_size=None, identifier=song_id, duration_s=extractdurationsecondsfromlrc(lyric), duration=seconds2hms(extractdurationsecondsfromlrc(lyric)), 
            lyric=lyric, cover_url=safeextractfromdict(download_result, ['data', 'cover'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        if not song_info.album or song_info.album in {'NULL'}: song_info.album = legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname'))
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for imp_func in [self._parsewithvkeysapi, self._parsewithtangapi, self._parsewithnkiapi, self._parsewithxianyuwapi, self._parsewithlittleyouziapi]:
            try: song_info_flac = imp_func(search_result, request_overrides); assert song_info_flac.with_valid_download_url; break
            except: song_info_flac = SongInfo(source=self.source)
        return song_info_flac
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('mid') or search_result.get('songmid'))): return song_info
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            # --non-vip / vip users using enc_endpoint
            if self.use_encrypted_endpoint:
                for quality in EncryptedSongFileType.SORTED_QUALITIES.value:
                    params = {"filename": [f"{quality[0]}{song_id}{song_id}{quality[1]}"], "guid": QQMusicClientUtils.randomguid(), "songmid": [song_id], 'songtype': [0]}
                    current_rule = QQMusicClientUtils.buildrequestdata(params=params, module="music.vkey.GetEVkey", method="CgiGetEVkey", credential=Credential().fromcookiesdict(self.default_cookies or request_overrides.get('cookies', {})), common_override={"ct": "19"})
                    try: (resp := self.post(QQMusicClientUtils.enc_endpoint, data=json.dumps(current_rule, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), params={"sign": QQMusicClientUtils.sign(current_rule)}, **request_overrides)).raise_for_status()
                    except Exception: continue
                    download_url = safeextractfromdict((download_result := resp2json(resp)), ['music.vkey.GetEVkey.CgiGetEVkey', 'data', "midurlinfo", 0, "purl"], "") or safeextractfromdict(download_result, ['music.vkey.GetEVkey.CgiGetEVkey', 'data', "midurlinfo", 0, "wifiurl"], "")
                    ekey = safeextractfromdict(download_result, ['music.vkey.GetEVkey.CgiGetEVkey', 'data', "midurlinfo", 0, "ekey"], "")
                    if not download_url: continue
                    download_url = QQMusicClientUtils.music_domain + download_url
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'ekey': ekey}, source=self.source, song_name=legalizestring(search_result.get('title') or search_result.get('songname')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name')])), 
                        album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname', None)), ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=None, file_size=None, identifier=str(song_id), duration_s=search_result.get('interval', 0), duration=seconds2hms(search_result.get('interval', 0)), lyric=None, cover_url=None, 
                        download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                    )
                    song_info.cover_url = f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{safeextractfromdict(search_result, ['album', 'mid'], '') or search_result.get('albummid')}.jpg"
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    '''
                    # encrypted audio extension, not conduct this part
                    if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                    elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
                    '''
                    if song_info.with_valid_download_url: break
            # --non-vip / vip users using endpoint
            else:
                for quality in SongFileType.SORTED_QUALITIES.value:
                    params = {"filename": [f"{quality[0]}{song_id}{song_id}{quality[1]}"], "guid": QQMusicClientUtils.randomguid(), "songmid": [song_id], 'songtype': [0]}
                    current_rule = QQMusicClientUtils.buildrequestdata(params=params, module="music.vkey.GetVkey", method="UrlGetVkey", credential=Credential().fromcookiesdict(self.default_cookies or request_overrides.get('cookies', {})), common_override={"ct": "19"})
                    try: (resp := self.post(QQMusicClientUtils.endpoint, data=json.dumps(current_rule, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), **request_overrides)).raise_for_status()
                    except Exception: continue
                    download_url = safeextractfromdict((download_result := resp2json(resp)), ['music.vkey.GetVkey.UrlGetVkey', 'data', "midurlinfo", 0, "purl"], "") or safeextractfromdict(download_result, ['music.vkey.GetVkey.UrlGetVkey', 'data', "midurlinfo", 0, "wifiurl"], "")
                    if not download_url: continue
                    download_url = QQMusicClientUtils.music_domain + download_url
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title') or search_result.get('songname')), singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name')])), 
                        album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None) or search_result.get('albumname', None)), ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=None, file_size=None, identifier=str(song_id), duration_s=search_result.get('interval', 0), duration=seconds2hms(search_result.get('interval', 0)), lyric=None, 
                        cover_url=None, download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                    )
                    song_info.cover_url = f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{safeextractfromdict(search_result, ['album', 'mid'], '') or search_result.get('albummid')}.jpg"
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                    elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
                    if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                    if song_info.with_valid_download_url: break
        if not song_info.with_valid_download_url: song_info = song_info_flac
        if not song_info.with_valid_download_url: return song_info
        # supplement lyric results
        params = {'songmid': str(song_id), 'g_tk': '5381', 'loginUin': '0', 'hostUin': '0', 'format': 'json', 'inCharset': 'utf8', 'outCharset': 'utf-8', 'platform': 'yqq'}
        lyric_request_overrides = copy.deepcopy(request_overrides); lyric_request_overrides.pop('headers', {})
        try: (resp := self.get('https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg', headers={'Referer': 'https://y.qq.com/portal/player.html'}, params=params, **lyric_request_overrides)).raise_for_status(); lyric = (lyric_result := resp2json(resp)).get('lyric'); lyric = 'NULL' if not lyric else cleanlrc(base64.b64decode(lyric).decode('utf-8'))
        except Exception: lyric_result, lyric = {}, "NULL"
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = {}, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        search_meta, request_overrides = copy.deepcopy(search_url), request_overrides or {}; search_url = search_meta.pop('url')
        # successful
        try:
            # --search results
            (resp := self.post(search_url, **search_meta, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp)['music.search.SearchCgiService.DoSearchForQQMusicMobile']['data']['body']['item_song']:
                # --parse with third part apis
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
                # --parse with official apis
                lossless_quality_is_sufficient = False if self.default_cookies or request_overrides.get('cookies') else True
                try: song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                except Exception: song_info = SongInfo(source=self.source)
                # --append to song_infos
                if not song_info.with_valid_download_url: song_info = song_info_flac
                if not song_info.with_valid_download_url: continue
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
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        # init
        request_overrides = request_overrides or {}
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **request_overrides).url
        try: playlist_id, song_infos = parse_qs(urlparse(playlist_url).query, keep_blank_values=False).get('id')[0], []; assert playlist_id
        except: playlist_id, song_infos = urlparse(playlist_url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm'), []
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, QQ_MUSIC_HOSTS)): return song_infos
        # get tracks in playlist
        (resp := self.get("https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg", headers={"Referer": f"https://y.qq.com/n/ryqq/playlist/{playlist_id}"}, params={"disstid": str(playlist_id), "type": "1", "json": "1", "utf8": "1", "onlysong": "0", "format": "json"}, **request_overrides)).raise_for_status()
        tracks_in_playlist = (safeextractfromdict((playlist_result := resp2json(resp=resp)), ['cdlist', 0, 'songlist'], []) or safeextractfromdict(playlist_result, ['cdlist', 0, 'list'], []) or safeextractfromdict(playlist_result, ['songlist'], []) or [])
        # parse track by track in playlist
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed (0/{len(tracks_in_playlist)})", total=len(tracks_in_playlist))
            for idx, track_info in enumerate(tracks_in_playlist):
                if idx > 0: main_process_context.advance(main_progress_id, 1)
                main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed ({idx}/{len(tracks_in_playlist)})")
                song_info_flac = self._parsewiththirdpartapis(search_result=track_info, request_overrides=request_overrides)
                lossless_quality_is_sufficient = False if self.default_cookies or request_overrides.get('cookies') else True
                try: song_info = self._parsewithofficialapiv1(search_result=track_info, song_info_flac=song_info_flac, lossless_quality_is_sufficient=lossless_quality_is_sufficient, request_overrides=request_overrides)
                except Exception: song_info = song_info_flac
                if not song_info.with_valid_download_url: song_info = song_info_flac
                if song_info.with_valid_download_url: song_infos.append(song_info)
            main_process_context.advance(main_progress_id, 1)
            main_process_context.update(main_progress_id, description=f"{len(tracks_in_playlist)} songs found in playlist {playlist_id} >>> completed ({idx+1}/{len(tracks_in_playlist)})")
        # post processing
        playlist_name = safeextractfromdict(playlist_result, ['cdlist', 0, 'dissname'], None)
        song_infos = self._removeduplicates(song_infos=song_infos); work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        # return results
        return song_infos