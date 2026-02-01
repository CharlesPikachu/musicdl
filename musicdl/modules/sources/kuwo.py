'''
Function:
    Implementation of KuwoMusicClient: http://www.kuwo.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
import random
import base64
from .base import BaseMusicClient
from rich.progress import Progress
from ..utils.kuwoutils import KuwoMusicClientUtils
from urllib.parse import urlencode, urlparse, parse_qs
from ..utils import legalizestring, resp2json, seconds2hms, usesearchheaderscookies, safeextractfromdict, kuwolyricslisttolrc, cleanlrc, SongInfo


'''KuwoMusicClient'''
class KuwoMusicClient(BaseMusicClient):
    source = 'KuwoMusicClient'
    MUSIC_QUALITIES = [(22000, 'flac'), (320, 'mp3')] # playable flac and mp3 formats
    ENC_MUSIC_QUALITIES = [(4000, '4000kflac'), (2000, '2000kflac'), (320, '320kmp3'), (192, '192kmp3'), (128, '128kmp3')] # encrypted mgg format
    def __init__(self, **kwargs):
        super(KuwoMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_download_headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_parsewithyaohudapi'''
    def _parsewithyaohudapi(self, keyword: str, search_result: dict, request_overrides: dict = None, page_no: int = 1, num: int = 1):
        # init
        if page_no > 1: return SongInfo(source=self.source)
        decrypt_func = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        request_overrides, song_id = request_overrides or {}, str(search_result['MUSICRID']).removeprefix('MUSIC_')
        REQUEST_KEYS = ['em41NHhnUzNOVTBjT0tFTzB5UQ==', 'eHdUNVl6UkV2SXdLOExWWjcybg==']
        MUSIC_QUALITIES = ["hires", "lossless", "SQ", "exhigh", "standard"]
        # parse
        for quality in MUSIC_QUALITIES:
            try:
                resp = self.get(f"https://api.yaohud.cn/api/music/kuwo?key={decrypt_func(random.choice(REQUEST_KEYS))}&msg={keyword}&n={num}&size={quality}", timeout=10, **request_overrides)
                resp.raise_for_status()
                download_result = resp2json(resp=resp)
                if 'data' not in download_result: continue
            except:
                continue
            download_url = safeextractfromdict(download_result, ['data', 'vipmusic', 'url'], '')
            if not download_url: continue
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)),
                singers=legalizestring(safeextractfromdict(download_result, ['data', 'songname'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), 
                ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=song_id, duration_s=safeextractfromdict(search_result, ['DURATION'], 0), duration=seconds2hms(safeextractfromdict(search_result, ['DURATION'], 0)),
                lyric='NULL', cover_url=safeextractfromdict(download_result, ['data', 'picture'], ""), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if song_info.with_valid_download_url: break
        return song_info
    '''_parsewithcggapi'''
    def _parsewithcggapi(self, keyword: str, search_result: dict, request_overrides: dict = None, page_no: int = 1, num: int = 1):
        # init
        request_overrides, song_id = request_overrides or {}, str(search_result['MUSICRID']).removeprefix('MUSIC_')
        MUSIC_QUALITIES = ["acc", "wma", "ogg", "standard", "exhigh", "ape", "lossless", "hires", "zp", "hifi", "sur", "jymaster"]
        # safe fetch filesize func
        safe_fetch_filesize_func = lambda meta: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(str(meta.get('size', '0.00MB')).removesuffix('MB').strip()) if isinstance(meta, dict) else 0
        # parse
        for quality in MUSIC_QUALITIES[::-1][3:]:
            try:
                resp = self.get(f"https://kw-api.cenguigui.cn/?id={song_id}&type=song&level={quality}&format=json", timeout=10, **request_overrides)
                resp.raise_for_status()
                download_result = resp2json(resp=resp)
                if 'data' not in download_result or (safe_fetch_filesize_func(download_result['data']) < 1): continue
            except:
                continue
            download_url = safeextractfromdict(download_result, ['data', 'url'], '')
            if not download_url: continue
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['data', 'name'], None)),
                singers=legalizestring(safeextractfromdict(download_result, ['data', 'artist'], None)), album=legalizestring(safeextractfromdict(download_result, ['data', 'album'], None)), 
                ext=download_url.split('?')[0].split('.')[-1], file_size=str(safeextractfromdict(download_result, ['data', 'size'], "")).removesuffix('MB').strip() + ' MB', identifier=song_id,
                duration_s=safeextractfromdict(download_result, ['data', 'duration'], 0), duration=seconds2hms(safeextractfromdict(download_result, ['data', 'duration'], 0)),
                lyric=cleanlrc(safeextractfromdict(download_result, ['data', 'lyric'], "")), cover_url=safeextractfromdict(download_result, ['data', 'pic'], ""), download_url=download_url,
                download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if song_info.with_valid_download_url: break
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, keyword: str, search_result: dict, request_overrides: dict = None, page_no: int = 1, num: int = 1):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for imp_func in [self._parsewithcggapi, self._parsewithyaohudapi]:
            try:
                song_info_flac = imp_func(keyword, search_result, request_overrides, page_no, num)
                if song_info_flac.with_valid_download_url: break
            except:
                song_info_flac = SongInfo(source=self.source)
        return song_info_flac
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {
            "vipver": "1", "client": "kt", "ft": "music", "cluster": "0", "strategy": "2012", "encoding": "utf8", "rformat": "json", "mobi": "1", "issubtitle": "1", "show_copyright_off": "1", "pn": "0", "rn": "10", "all": keyword,
        }
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'http://www.kuwo.cn/search/searchMusicBykeyWord?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['rn'] = page_size
            page_rule['pn'] = str(int(count // page_size))
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        page_no = int(parse_qs(urlparse(search_url).query, keep_blank_values=True).get('pn')[0]) + 1
        safe_fetch_filesize_func = lambda size: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(size.removesuffix('MB').strip()) if isinstance(size, str) else 0
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['abslist']
            for search_result_idx, search_result in enumerate(search_results):
                # --download results
                if not isinstance(search_result, dict) or ('MUSICRID' not in search_result): continue
                song_info = SongInfo(source=self.source)
                song_info_flac = self._parsewiththirdpartapis(keyword=keyword, search_result=search_result, request_overrides=request_overrides, page_no=page_no, num=search_result_idx+1)
                for quality in KuwoMusicClient.MUSIC_QUALITIES:
                    if song_info_flac.with_valid_download_url and song_info_flac.ext in ('flac',): song_info = song_info_flac; break
                    query = f"user=0&corp=kuwo&source=kwplayer_ar_5.1.0.0_B_jiakong_vh.apk&p2p=1&type=convert_url2&sig=0&format={quality[1]}&rid={search_result['MUSICRID'].removeprefix('MUSIC_')}"
                    try: (resp := self.get(f"http://mobi.kuwo.cn/mobi.s?f=kuwo&q={KuwoMusicClientUtils.encryptquery(query)}", headers={"user-agent": "okhttp/3.10.0"}, **request_overrides)).raise_for_status(); download_result = resp.text
                    except Exception: continue
                    download_url = re.search(r'http[^\s$\"]+', download_result)
                    if not download_url: continue
                    download_url = download_url.group(0)
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['SONGNAME'], None)),
                        singers=legalizestring(safeextractfromdict(search_result, ['ARTIST'], None)), album=legalizestring(safeextractfromdict(search_result, ['ALBUM'], None)), ext=download_url.split('?')[0].split('.')[-1], 
                        file_size='NULL', identifier=search_result['MUSICRID'].removeprefix('MUSIC_'), duration_s=safeextractfromdict(search_result, ['DURATION'], 0), duration=seconds2hms(safeextractfromdict(search_result, ['DURATION'], 0)),
                        lyric='NULL', cover_url=safeextractfromdict(search_result, ['hts_MVPIC'], ""), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                    )
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] != 'NULL') else song_info.ext
                    if song_info_flac.with_valid_download_url and (safe_fetch_filesize_func(song_info.file_size) < safe_fetch_filesize_func(song_info_flac.file_size)): song_info = song_info_flac
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: song_info = song_info_flac
                if not song_info.with_valid_download_url: continue
                # --lyric results
                params = {'musicId': search_result['MUSICRID'].removeprefix('MUSIC_'), 'httpsStatus': '1'}
                try:
                    resp = self.get('http://m.kuwo.cn/newh5/singles/songinfoandlrc', params=params, **request_overrides)
                    resp.raise_for_status()
                    lyric_result: dict = resp2json(resp)
                    lyric = cleanlrc(kuwolyricslisttolrc(safeextractfromdict(lyric_result, ['data', 'lrclist'], [])))
                except:
                    lyric_result, lyric = {}, 'NULL'
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