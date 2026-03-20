'''
Function:
    Implementation of KugouMusicClient: http://www.kugou.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import re
import copy
import time
import random
import base64
import hashlib
import warnings
import json_repair
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from pathvalidate import sanitize_filepath
from ..utils.hosts import KUGOU_MUSIC_HOSTS
from urllib.parse import urlparse, parse_qs, urljoin
from ..utils.kugouutils import KugouMusicClientUtils, MUSIC_QUALITIES
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
from ..utils import touchdir, legalizestring, byte2mb, resp2json, seconds2hms, usesearchheaderscookies, safeextractfromdict, optionalimport, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo, AudioLinkTester
warnings.filterwarnings('ignore')


'''KugouMusicClient'''
class KugouMusicClient(BaseMusicClient):
    source = 'KugouMusicClient'
    def __init__(self, **kwargs):
        super(KugouMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_parse_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_download_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'}
        self.default_headers = self.default_search_headers
        self._initsession()
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
    '''_parsewithcggapi'''
    def _parsewithcggapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        curl_cffi, request_overrides, file_hash, MUSIC_QUALITIES = optionalimport('curl_cffi'), request_overrides or {}, search_result['hash'], ['lossless', 'exhigh', 'hires', 'standard', 'ogg']
        safe_obtain_filesize_func = lambda meta: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(str(meta.get('size', '0.00MB')).removesuffix('MB').strip()) if isinstance(meta, dict) else 0
        # parse
        for quality in MUSIC_QUALITIES:
            try: (resp := curl_cffi.requests.get(f"https://music-api2.cenguigui.cn/?kg=&id={file_hash}&type=song&format=json&level={quality}", timeout=10, impersonate="chrome131", verify=False, **request_overrides)).raise_for_status()
            except Exception: break
            if 'data' not in (download_result := json_repair.loads(resp.text)) or (safe_obtain_filesize_func(download_result['data']) < 0.01): continue
            if not (download_url := safeextractfromdict(download_result, ['data', 'url'], '')) or not str(download_url).startswith('http'): continue
            try: duration_in_secs = search_result.get('duration') or (float(search_result.get('timelen', 0) or 0) / 1000)
            except Exception: duration_in_secs = 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(search_result.get('album_name') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), 
                ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=None, file_size=str(safeextractfromdict(download_result, ['data', 'size'], "") or "0.00 MB").removesuffix('MB').strip() + ' MB', identifier=file_hash, duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric='NULL', cover_url=safeextractfromdict(download_result, ['data', 'pic'], None), download_url=download_url, 
                download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if song_info.ext.startswith('m'): continue # encrypted format like mgg, skip by default
            if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
            elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsewithjbsouapi'''
    def _parsewithjbsouapi(self, search_result: dict, request_overrides: dict = None) -> "SongInfo":
        # init
        request_overrides, file_hash, base_url = request_overrides or {}, search_result['hash'], 'https://www.jbsou.cn/'
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "content-type": "application/x-www-form-urlencoded; charset=UTF-8", "origin": "https://www.jbsou.cn", 
            "priority": "u=1, i", "referer": "https://www.jbsou.cn/", "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"', "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"', "sec-fetch-dest": "empty", "x-requested-with": "XMLHttpRequest", 
            "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36", 
        }
        # parse
        (resp := self.post('https://www.jbsou.cn/', data={'input': file_hash, 'filter': 'id', 'type': 'kugou', 'page': '1'}, headers=headers, **request_overrides)).raise_for_status()
        download_url = urljoin(base_url, safeextractfromdict((download_result := resp2json(resp=resp)), ['data', 0, 'url'], ''))
        try: download_url = self.session.head(download_url, headers=headers, allow_redirects=True, **request_overrides).url
        except Exception: return SongInfo(source=self.source)
        if not download_url or not str(download_url).startswith('http'): return SongInfo(source=self.source)
        try: duration_in_secs = search_result.get('duration') or (float(search_result.get('timelen', 0) or 0) / 1000)
        except Exception: duration_in_secs = 0
        try: cover_url = self.session.head(urljoin(base_url, safeextractfromdict(download_result, ['data', 0, 'cover'], "")), headers=headers, allow_redirects=True, **request_overrides).url
        except Exception: cover_url = None
        if not cover_url: cover_url = safeextractfromdict(search_result, ['trans_param', 'union_cover'], None)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 0, 'name'], None)), singers=legalizestring(safeextractfromdict(download_result, ['data', 0, 'artist'], None)), 
            album=legalizestring(search_result.get('album_name') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), ext=download_url.split('?')[0].split('.')[-1], file_size=None, identifier=str(file_hash), duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), 
            lyric='NULL', cover_url=cover_url, download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        if song_info.cover_url and isinstance(song_info.cover_url, str) and ('{size}' in song_info.cover_url): song_info.cover_url = song_info.cover_url.format(size=300)
        if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
        elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
        if not song_info.with_valid_download_url: return song_info
        lyric_url = urljoin(base_url, safeextractfromdict(download_result, ['data', 0, 'lrc'], ""))
        try: (resp := self.get(lyric_url, headers=headers, allow_redirects=True, **request_overrides)).raise_for_status(); lyric = cleanlrc(resp.text)
        except Exception: lyric = 'NULL'
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for imp_func in [self._parsewithcggapi, self._parsewithjbsouapi]:
            try: song_info_flac = imp_func(search_result, request_overrides); assert song_info_flac.with_valid_download_url; break
            except: song_info_flac = SongInfo(source=self.source)
        return song_info_flac
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('hash'))): return song_info
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            try: duration_in_secs = search_result.get('duration') or (float(search_result.get('timelen', 0) or 0) / 1000)
            except Exception: duration_in_secs = 0
            for quality in MUSIC_QUALITIES:
                if ('impersonate' not in (per_request_overrides := copy.deepcopy(request_overrides))) and self.enable_curl_cffi: per_request_overrides['impersonate'] = random.choice(self.cc_impersonates)
                per_request_overrides['proxies'] = per_request_overrides.pop('proxies', None) or self._autosetproxies()
                try: download_result: dict = KugouMusicClientUtils.getsongurl(self.session, hash_value=song_id, quality=quality, request_overrides=per_request_overrides, cookies=copy.deepcopy(per_request_overrides.pop('cookies', None) or self.default_cookies))
                except Exception: download_result, download_url = {}, None
                download_url = safeextractfromdict(download_result, ['url'], '') or safeextractfromdict(download_result, ['backupUrl'], '')
                if not download_url:
                    md5_hex = hashlib.md5((str(song_id) + 'kgcloudv2').encode("utf-8")).hexdigest()
                    try: (resp := self.get(f"https://trackercdn.kugou.com/i/v2/?cdnBackup=1&behavior=download&pid=1&cmd=21&appid=1001&hash={song_id}&key={md5_hex}", **request_overrides)).raise_for_status(); download_result: dict = resp2json(resp)
                    except Exception: continue
                    download_url = safeextractfromdict(download_result, ['url'], '') or safeextractfromdict(download_result, ['backup_url'], '') or safeextractfromdict(download_result, ['backupUrl'], '') or safeextractfromdict(download_result, ['mp3Url'], '') or safeextractfromdict(download_result, ['backupMp3Url'], '')
                if download_url and isinstance(download_url, (list, tuple)): download_url = list(download_url)[0]
                if not download_url or not str(download_url).startswith('http'): continue
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('songname', None) or search_result.get('songname_original') or search_result.get('filename') or search_result.get('name')), singers=legalizestring(search_result.get('singername') or ', '.join([singer.get('name') for singer in (search_result.get('singerinfo') or []) if isinstance(singer, dict) and singer.get('name')])), 
                    album=legalizestring(search_result.get('album_name') or safeextractfromdict(search_result, ['albuminfo', 'name'], None)), ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=download_result.get('fileSize', 0), file_size=byte2mb(download_result.get('fileSize', 0)), identifier=song_id, duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric='NULL', cover_url=safeextractfromdict(search_result, ['trans_param', 'union_cover'], None), 
                    download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                )
                song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                if song_info.cover_url and isinstance(song_info.cover_url, str) and ('{size}' in song_info.cover_url): song_info.cover_url = song_info.cover_url.format(size=300)
                if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
                elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
                if song_info_flac.with_valid_download_url and song_info_flac.largerthan(song_info): song_info = song_info_flac
                if song_info.with_valid_download_url: break
        if not song_info.with_valid_download_url: song_info = song_info_flac
        if not song_info.with_valid_download_url: return song_info
        # supplement lyric results
        params = {'keyword': search_result.get('filename', ''), 'duration': search_result.get('duration', '99999'), 'hash': song_id}
        try: (resp := self.get('http://lyrics.kugou.com/search', params=params, **request_overrides)).raise_for_status(); lyric_result = resp2json(resp=resp); (resp := self.get(f"http://lyrics.kugou.com/download?ver=1&client=pc&id={lyric_result['candidates'][0]['id']}&accesskey={lyric_result['candidates'][0]['accesskey']}&fmt=lrc&charset=utf8", **request_overrides)).raise_for_status(); lyric_result['lyrics.kugou.com/download'] = resp2json(resp=resp); lyric = cleanlrc(base64.b64decode(lyric_result['lyrics.kugou.com/download']['content']).decode('utf-8')) or 'NULL'
        except: lyric_result, lyric = dict(), 'NULL'
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp)['data']['info']:
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
        if (not (hostname := obtainhostname(url=playlist_url))) or (not hostmatchessuffix(hostname, KUGOU_MUSIC_HOSTS)): return song_infos
        assert 'special/single/' in urlparse(playlist_url).path, 'kugou playlist link must look like "https://www.kugou.com/yy/special/single/6914288.html"'
        headers = {'User-Agent': 'Android9-AndroidPhone-11239-18-0-playlist-wifi', 'Host': 'gatewayretry.kugou.com', 'x-router': 'pubsongscdn.kugou.com', 'mid': '239526275778893399526700786998289824956', 'dfid': '-', 'clienttime': str(time.time()).split('.')[0]}
        # get tracks in playlist
        tracks_in_playlist, page, playlist_result_first = [], 1, {}
        while True:
            api_url = f'http://gatewayretry.kugou.com/v2/get_other_list_file?specialid={playlist_id}&need_sort=1&module=CloudMusic&clientver=11239&pagesize=300&specalidpgc={playlist_id}&userid=0&page={page}&type=0&area_code=1&appid=1005'
            kugou_signature_func = lambda api_url: hashlib.md5(("OIlwieks28dk2k092lksi2UIkp" + "".join(sorted(str(api_url).split("?", 1)[1].split("&"))) + "OIlwieks28dk2k092lksi2UIkp").encode("utf-8")).hexdigest()
            try: (resp := self.get(api_url + '&signature=' + kugou_signature_func(api_url), headers=headers, **request_overrides)).raise_for_status()
            except Exception: continue
            if (not safeextractfromdict((playlist_result := resp2json(resp=resp)), ['data', 'info'], [])): break
            tracks_in_playlist.extend(safeextractfromdict(playlist_result, ['data', 'info'], [])); page += 1
            if not playlist_result_first: playlist_result_first = copy.deepcopy(playlist_result)
            if (float(safeextractfromdict(playlist_result, ['data', 'count'], 0)) <= len(tracks_in_playlist)): break
        tracks_in_playlist = list({d["hash"]: d for d in tracks_in_playlist}.values())
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
        try: (resp := self.get(playlist_url, headers={'referer': 'https://www.kugou.com/songlist/'}, **request_overrides)).raise_for_status(); playlist_name = json_repair.loads(re.search(r'var\s+specialInfo\s*=\s*(\{.*?\});', resp.text, re.S).group(1))['name']
        except: playlist_name = None
        song_infos = self._removeduplicates(song_infos=song_infos); work_dir = self._constructuniqueworkdir(keyword=legalizestring(playlist_name or f"playlist-{playlist_id}"))
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        # return results
        return song_infos