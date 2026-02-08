'''
Function:
    Implementation of QianqianMusicClient: http://music.taihe.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import time
import copy
import hashlib
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import byte2mb, resp2json, seconds2hms, legalizestring, safeextractfromdict, usesearchheaderscookies, cookies2string, cleanlrc, SongInfo


'''QianqianMusicClient'''
class QianqianMusicClient(BaseMusicClient):
    source = 'QianqianMusicClient'
    APPID = '16073360'
    MUSIC_QUALITIES = ['3000', '320', '128', '64']
    def __init__(self, **kwargs):
        super(QianqianMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "accept": "*/*", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "from": "web", "priority": "u=1, i", "referer": "https://music.91q.com/player",
            "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"", "sec-ch-ua-mobile": "?0", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "sec-ch-ua-platform": "\"Windows\"",
        }
        if self.default_search_cookies: self.default_search_headers['authorization'] = f"access_token {self.default_search_cookies.get('access_token', '')}"
        if self.default_search_cookies: self.default_search_headers['cookie'] = cookies2string(self.default_search_cookies)
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        if self.default_download_cookies: self.default_download_headers['authorization'] = f"access_token {self.default_download_cookies.get('access_token', '')}"
        if self.default_download_cookies: self.default_download_headers['cookie'] = cookies2string(self.default_download_cookies)
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_addsignandtstoparams'''
    def _addsignandtstoparams(self, params: dict):
        secret = '0b50b02fd0d73a9c4c8c3a781c30845f'
        params['timestamp'] = str(int(time.time()))
        keys = sorted(params.keys())
        string = "&".join(f"{k}={params[k]}" for k in keys)
        params['sign'] = hashlib.md5((string + secret).encode('utf-8')).hexdigest()
        return params
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {'word': keyword, 'type': '1', 'pageNo': '1', 'pageSize': '10', 'appid': QianqianMusicClient.APPID}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://music.91q.com/v1/search?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['pageSize'] = page_size
            page_rule['pageNo'] = str(int(count // page_size) + 1)
            page_rule = self._addsignandtstoparams(params=page_rule)
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
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['data']['typeTrack']
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('TSID' not in search_result): continue
                song_info = SongInfo(source=self.source)
                for rate in QianqianMusicClient.MUSIC_QUALITIES:
                    params = self._addsignandtstoparams(params={'TSID': search_result['TSID'], 'appid': QianqianMusicClient.APPID, 'rate': rate})
                    try:
                        resp = self.get("https://music.91q.com/v1/song/tracklink", params=params, **request_overrides)
                        resp.raise_for_status()
                        download_result: dict = resp2json(resp)
                    except:
                        continue
                    download_url = safeextractfromdict(download_result, ['data', 'path'], '') or safeextractfromdict(download_result, ['data', 'trail_audio_info', 'path'], '')
                    if not download_url: continue
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['title'], None)),
                        singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['artist'], []) or []) if isinstance(singer, dict) and singer.get('name')])),
                        album=legalizestring(search_result.get('albumTitle')), ext=safeextractfromdict(download_result, ['data', 'format'], 'mp3') or download_url.split('?')[0].split('.')[-1] or 'mp3', 
                        file_size_bytes=safeextractfromdict(download_result, ['data', 'size'], 0), file_size=byte2mb(safeextractfromdict(download_result, ['data', 'size'], 0)), identifier=search_result['TSID'], 
                        duration_s=safeextractfromdict(download_result, ['data', 'duration'], 0), duration=seconds2hms(safeextractfromdict(download_result, ['data', 'duration'], 0)), lyric=None,
                        cover_url=safeextractfromdict(search_result, ['pic'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                    )
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] != 'NULL') else song_info.ext
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: continue
                # --lyric results
                try:
                    resp = self.get(search_result['lyric'], **request_overrides)
                    resp.raise_for_status()
                    resp.encoding = 'utf-8'
                    lyric = cleanlrc(resp.text) or 'NULL'
                    lyric_result = dict(lyric=lyric)
                    if song_info.singers == 'NULL': song_info.singers = (m.group(1) if (m := re.search(r'\[ar:(.*?)\]', lyric)) else 'NULL')
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