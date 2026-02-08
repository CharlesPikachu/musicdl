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
from ..utils import touchdir, resp2json, seconds2hms, legalizestring, safeextractfromdict, usesearchheaderscookies, extractdurationsecondsfromlrc, useparseheaderscookies, obtainhostname, hostmatchessuffix, cleanlrc, SongInfo


'''QQMusicClient'''
class QQMusicClient(BaseMusicClient):
    source = 'QQMusicClient'
    def __init__(self, use_encrypted_endpoint: bool = False, **kwargs):
        super(QQMusicClient, self).__init__(**kwargs)
        self.use_encrypted_endpoint = use_encrypted_endpoint
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Referer': 'https://y.qq.com/', 'Origin': 'https://y.qq.com/',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Referer': 'http://y.qq.com',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_parsewithvkeysapi'''
    def _parsewithvkeysapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id = request_overrides or {}, search_result['mid']
        # safe fetch filesize func
        safe_fetch_filesize_func = lambda meta: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(str(meta.get('size', '0.00MB')).removesuffix('MB').strip()) if isinstance(meta, dict) else 0
        # to seconds func
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        # parse
        for quality in list(ThirdPartVKeysAPISongFileType.ID_TO_NAME.value.keys())[::-1]:
            try:
                resp = self.get(f"https://api.vkeys.cn/v2/music/tencent/geturl?mid={song_id}&quality={quality}", timeout=10, **request_overrides)
                resp.raise_for_status()
                download_result = resp2json(resp=resp)
                if ('data' not in download_result) or ('url' not in download_result['data']) or (safe_fetch_filesize_func(download_result['data']) < 1): continue
            except:
                continue
            download_url: str = download_result['data']['url']
            if not download_url: continue
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result['data'], ['song'], None)),
                singers=legalizestring(safeextractfromdict(download_result['data'], ['singer'], None)), album=legalizestring(safeextractfromdict(download_result['data'], ['album'], None)), 
                ext=download_url.split('?')[0].split('.')[-1], file_size=str(safeextractfromdict(download_result['data'], ['size'], "")).removesuffix('MB').strip() + ' MB', identifier=search_result['mid'],
                duration_s=to_seconds_func(safeextractfromdict(download_result['data'], ['interval'], "")), duration=seconds2hms(to_seconds_func(safeextractfromdict(download_result['data'], ['interval'], ""))), 
                lyric=None, cover_url=safeextractfromdict(download_result['data'], ['cover'], ""), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsewithnkiapi'''
    def _parsewithnkiapi(self, search_result: dict, request_overrides: dict = None):
        # init
        decrypt_func = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        request_overrides, song_id, song_info = request_overrides or {}, search_result['mid'], SongInfo(source=self.source)
        REQUEST_KEYS = ['MjhmZWNlOTI1NDM5YjA1Mjc5MmE5Nzk4OWM4NzBjZWQzODAzYTcxYzZiNTM0ZjcxZTVhNTMzMzhiMmQzMWVmOA==', 'YzRjNGY1ZmMzNmJhZDRjYWNiOTg4MzllMTRmZWE0MDI3N2IzNWVhMmViMWJhYmRhZDdiYmRlMTI4NDAwZjNiMQ==']
        # parse
        resp = self.get(f'https://api.nki.pw/API/music_open_api.php?mid={song_id}&apikey={decrypt_func(random.choice(REQUEST_KEYS))}', **request_overrides)
        resp.raise_for_status()
        download_result = resp2json(resp=resp)
        download_url: str = download_result['song_play_url_sq'] or download_result['song_play_url']
        if not download_url or not download_url.startswith('http'): return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['song_name'], None)),
            singers=legalizestring(safeextractfromdict(download_result, ['singer_name'], None)), album=legalizestring(safeextractfromdict(download_result, ['album_name'], None)), 
            ext=download_url.split('?')[0].split('.')[-1], file_size_bytes=safeextractfromdict(download_result, ['song_size_sq_str'], 0) or safeextractfromdict(download_result, ['song_size_str'], 0),
            file_size=str(safeextractfromdict(download_result, ['song_size_sq'], "") or safeextractfromdict(download_result, ['song_size'], "")).removesuffix('MB').strip() + ' MB', 
            identifier=search_result['mid'], duration=safeextractfromdict(download_result, ['duration'], ""), lyric=cleanlrc(safeextractfromdict(download_result, ['song_lyric'], "")),
            cover_url=safeextractfromdict(download_result, ['album_pic'], ""), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        # return
        return song_info
    '''_parsewithxianyuwapi'''
    def _parsewithxianyuwapi(self, search_result: dict, request_overrides: dict = None):
        # init
        decrypt_func = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        request_overrides, song_id, song_info = request_overrides or {}, search_result['mid'], SongInfo(source=self.source)
        REQUEST_KEYS = ['c2stOTUwZTc4MTNjMzhjMmUzMWQzOWQ4NzlkMzIwNDg4OTU=', 'c2stNjJjZGIwM2UyMjcwZWIzOTY4Y2NhNzg4MTM5OWY0MTI=']
        # parse
        resp = self.get(f'https://apii.xianyuw.cn/api/v1/qq-music-search?id={song_id}&key={decrypt_func(random.choice(REQUEST_KEYS))}&no_url=0&br=hires', **request_overrides)
        resp.raise_for_status()
        download_result = resp2json(resp=resp)
        download_url: str = download_result['data']['url']
        if not download_url or not download_url.startswith('http'): return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'title'], None)),
            singers=legalizestring(safeextractfromdict(download_result, ['data', 'author'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), 
            ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=search_result['mid'], duration='-:-:-', lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lrc'], "")),
            cover_url=safeextractfromdict(download_result, ['data', 'cover'], ""), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric)
        song_info.duration = seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for imp_func in [self._parsewithvkeysapi, self._parsewithnkiapi, self._parsewithxianyuwapi]:
            try:
                song_info_flac = imp_func(search_result, request_overrides)
                if song_info_flac.with_valid_download_url: break
            except:
                song_info_flac = SongInfo(source=self.source)
        return song_info_flac
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
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = {}, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        search_meta, request_overrides = copy.deepcopy(search_url), request_overrides or {}
        search_url = search_meta.pop('url')
        safe_fetch_filesize_func = lambda size: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(size.removesuffix('MB').strip()) if isinstance(size, str) else 0
        # successful
        try:
            # --search results
            resp = self.post(search_url, **search_meta, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['music.search.SearchCgiService.DoSearchForQQMusicMobile']['data']['body']['item_song']
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('mid' not in search_result): continue
                song_info = SongInfo(source=self.source)
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
                # ----non-vip / vip users using enc_endpoint
                if self.use_encrypted_endpoint:
                    base_url = QQMusicClientUtils.enc_endpoint
                    for quality in EncryptedSongFileType.SORTED_QUALITIES.value:
                        params = {"filename": [f"{quality[0]}{search_result['mid']}{search_result['mid']}{quality[1]}"], "guid": QQMusicClientUtils.randomguid(), "songmid": [search_result['mid']], 'songtype': [0]}
                        current_rule = QQMusicClientUtils.buildrequestdata(params=params, module="music.vkey.GetEVkey", method="CgiGetEVkey", credential=Credential().fromcookiesdict(self.default_cookies or request_overrides.get('cookies', {})), common_override={"ct": "19"})
                        try:
                            resp = self.post(base_url, data=json.dumps(current_rule, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), params={"sign": QQMusicClientUtils.sign(current_rule)}, **request_overrides)
                            resp.raise_for_status()
                            download_result: dict = resp2json(resp)
                        except:
                            continue
                        download_url = safeextractfromdict(download_result, ['music.vkey.GetEVkey.CgiGetEVkey', 'data', "midurlinfo", 0, "purl"], "") or safeextractfromdict(download_result, ['music.vkey.GetEVkey.CgiGetEVkey', 'data', "midurlinfo", 0, "wifiurl"], "")
                        ekey = safeextractfromdict(download_result, ['music.vkey.GetEVkey.CgiGetEVkey', 'data', "midurlinfo", 0, "ekey"], "")
                        if not download_url: continue
                        download_url = QQMusicClientUtils.music_domain + download_url
                        song_info = SongInfo(
                            raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'ekey': ekey}, source=self.source, song_name=legalizestring(search_result.get('title')),
                            singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name')])),
                            album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None)), ext=quality[1][1:], file_size='NULL', identifier=search_result['mid'], duration_s=search_result.get('interval', 0),
                            duration=seconds2hms(search_result.get('interval', 0)), lyric=None, cover_url=None, download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                        )
                        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] != 'NULL') else song_info.ext
                        if song_info.with_valid_download_url: break
                # ----non-vip / vip users using endpoint
                else:
                    base_url = QQMusicClientUtils.endpoint
                    for quality in SongFileType.SORTED_QUALITIES.value:
                        if song_info_flac.with_valid_download_url and song_info_flac.ext in ('flac',): song_info = song_info_flac; break
                        params = {"filename": [f"{quality[0]}{search_result['mid']}{search_result['mid']}{quality[1]}"], "guid": QQMusicClientUtils.randomguid(), "songmid": [search_result['mid']], 'songtype': [0]}
                        current_rule = QQMusicClientUtils.buildrequestdata(params=params, module="music.vkey.GetVkey", method="UrlGetVkey", credential=Credential().fromcookiesdict(self.default_cookies or request_overrides.get('cookies', {})), common_override={"ct": "19"})
                        try:
                            resp = self.post(base_url, data=json.dumps(current_rule, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), **request_overrides)
                            resp.raise_for_status()
                            download_result: dict = resp2json(resp)
                        except:
                            continue
                        download_url = safeextractfromdict(download_result, ['music.vkey.GetVkey.UrlGetVkey', 'data', "midurlinfo", 0, "purl"], "") or safeextractfromdict(download_result, ['music.vkey.GetVkey.UrlGetVkey', 'data', "midurlinfo", 0, "wifiurl"], "")
                        if not download_url: continue
                        download_url = QQMusicClientUtils.music_domain + download_url
                        song_info = SongInfo(
                            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')),
                            singers=legalizestring(', '.join([singer.get('name') for singer in (search_result.get('singer', []) or []) if isinstance(singer, dict) and singer.get('name')])),
                            album=legalizestring(safeextractfromdict(search_result, ['album', 'title'], None)), ext=quality[1][1:], file_size='NULL', identifier=search_result['mid'], duration_s=search_result.get('interval', 0),
                            duration=seconds2hms(search_result.get('interval', 0)), lyric=None, cover_url=None, download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                        )
                        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] != 'NULL') else song_info.ext
                        if song_info_flac.with_valid_download_url and (safe_fetch_filesize_func(song_info.file_size) < safe_fetch_filesize_func(song_info_flac.file_size)): song_info = song_info_flac
                        if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: song_info = song_info_flac
                if not song_info.with_valid_download_url: continue
                # --lyric results
                params = {'songmid': str(search_result['mid']), 'g_tk': '5381', 'loginUin': '0', 'hostUin': '0', 'format': 'json', 'inCharset': 'utf8', 'outCharset': 'utf-8', 'platform': 'yqq'}
                request_overrides = copy.deepcopy(request_overrides)
                request_overrides.pop('headers', {})
                try:
                    resp = self.get('https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg', headers={'Referer': 'https://y.qq.com/portal/player.html'}, params=params, **request_overrides)
                    lyric_result: dict = resp2json(resp) or {'lyric': ''}
                    lyric = lyric_result.get('lyric', '')
                    lyric = 'NULL' if not lyric else cleanlrc(base64.b64decode(lyric).decode('utf-8'))
                except:
                    lyric_result, lyric = {}, "NULL"
                song_info.raw_data['lyric'], song_info.lyric = lyric_result, lyric
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
    '''parseplaylist'''
    @useparseheaderscookies
    def parseplaylist(self, playlist_url: str, request_overrides: dict = None):
        request_overrides = request_overrides or {}
        playlist_url = self.session.head(playlist_url, allow_redirects=True, **request_overrides).url
        hostname = obtainhostname(url=playlist_url)
        if not hostname or not hostmatchessuffix(hostname, QQ_MUSIC_HOSTS): return []
        try: playlist_id = parse_qs(urlparse(playlist_url).query, keep_blank_values=True).get('id')[0]
        except: playlist_id = urlparse(playlist_url).path.strip('/').split('/')[-1]
        headers = {"Referer": f"https://y.qq.com/n/ryqq/playlist/{playlist_id}"}
        resp = self.get("https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg", headers=headers, params={"disstid": str(playlist_id), "type": "1", "json": "1", "utf8": "1", "onlysong": "0", "format": "json"}, **request_overrides)
        resp.raise_for_status()
        playlist_results = resp2json(resp=resp)
        track_ids, song_infos = [str(t['songmid']) for t in (safeextractfromdict(playlist_results, ['cdlist', 0, 'songlist'], []) or safeextractfromdict(playlist_results, ['cdlist', 0, 'list'], []) or safeextractfromdict(playlist_results, ['songlist'], []) or [])], []
        with Progress(TextColumn("{task.description}"), BarColumn(bar_width=None), MofNCompleteColumn(), TimeRemainingColumn(), refresh_per_second=10) as main_process_context:
            main_progress_id = main_process_context.add_task(f"{len(track_ids)} songs found in playlist {playlist_id} >>> completed (0/{len(track_ids)})", total=len(track_ids))
            for idx, track_id in enumerate(track_ids):
                if idx > 0: main_process_context.advance(main_progress_id, 1)
                main_process_context.update(main_progress_id, description=f"{len(track_ids)} songs found in playlist {playlist_id} >>> completed ({idx}/{len(track_ids)})")
                for third_part_api in [self._parsewithvkeysapi, self._parsewithnkiapi, self._parsewithxianyuwapi]:
                    try:
                        song_info = third_part_api({'mid': track_id}, request_overrides=request_overrides)
                        if song_info.with_valid_download_url: song_infos.append(song_info); break
                    except:
                        continue
            main_process_context.advance(main_progress_id, 1)
            main_process_context.update(main_progress_id, description=f"{len(track_ids)} songs found in playlist {playlist_id} >>> completed ({idx+1}/{len(track_ids)})")
        song_infos = self._removeduplicates(song_infos=song_infos)
        work_dir = self._constructuniqueworkdir(keyword=playlist_id)
        for song_info in song_infos:
            song_info.work_dir = work_dir; episodes = song_info.episodes if isinstance(song_info.episodes, list) else []
            for eps_info in episodes: eps_info.work_dir = sanitize_filepath(os.path.join(work_dir, song_info.song_name)); touchdir(work_dir)
        return song_infos