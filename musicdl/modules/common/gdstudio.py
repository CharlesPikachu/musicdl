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
import struct
from typing import Dict, Any
from contextlib import suppress
from rich.progress import Progress
from ..sources import BaseMusicClient
from urllib.parse import quote, urljoin
from ..utils import resp2json, legalizestring, usesearchheaderscookies, safeextractfromdict, extractdurationsecondsfromlrc, cleanlrc, SongInfo, AudioLinkTester, SongInfoUtils, LyricSearchClient


'''GDStudioMusicClient'''
class GDStudioMusicClient(BaseMusicClient):
    source = 'GDStudioMusicClient'
    VERSION = "2026.07.21"
    HOST = "music.gdstudio.xyz"
    BASE_URL = "https://music.gdstudio.xyz/"
    TIME_URL = "https://music.gdstudio.xyz/time"
    API_URL = "https://music.gdstudio.xyz/api.php"
    MUSIC_QUALITIES = [999, 740, 320, 192, 128]
    SUPPORTED_SITES = ['netease', 'joox', 'tidal', 'qobuz', 'apple', 'bilibili', 'ytmusic', 'spotify', 'kuwo', 'tencent']
    def __init__(self, **kwargs):
        self.allowed_music_sources = list(set(kwargs.pop('allowed_music_sources', GDStudioMusicClient.SUPPORTED_SITES[:-4])))
        super(GDStudioMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://music.gdstudio.xyz/", "X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/javascript, */*; q=0.01", "Origin": "https://music.gdstudio.xyz", 
        }
        self.default_download_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'}
        self.default_bilibili_download_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36', 'Referer': 'https://www.bilibili.com/'}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''jsencodeuricomponent'''
    @staticmethod
    def jsencodeuricomponent(value: str) -> str:
        text = quote(str(value), safe="-_.!~*'()")
        return (text.replace("(", "%28").replace(")", "%29").replace("*", "%2A").replace("'", "%27").replace("!", "%21"))
    '''leftrotate'''
    @staticmethod
    def leftrotate(x: int, amount: int) -> int:
        x &= 0xFFFFFFFF
        return ((x << amount) | (x >> (32 - amount))) & 0xFFFFFFFF
    '''gdstudiomd5'''
    @staticmethod
    def gdstudiomd5(message: str) -> str:
        bit_len = (len((data := message.encode("utf-8"))) * 8) & 0xFFFFFFFFFFFFFFFF; data += b"\x80"
        while len(data) % 64 != 56: data += b"\x00"
        data += struct.pack("<Q", bit_len); a0 = 0x67452301; b0 = 0xEFCDAB89; c0 = 0x98BADCFE; d0 = 0x10325476
        shifts = [7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21]
        table = [
            0xD76AA478, 0xE8C7B756, 0x242070DB, 0xC1BDCEEE, 0xF57C0FAF, 0x4787C62A, 0xA8304613, 0xFD469501, 0x698098D8, 0x8B44F7AF, 0xFFFF5BB1, 0x895CD7BE, 0x6B901122, 0xFD987193, 0xA679438E, 0x49B40821,
            0xF61E2562, 0xC040B340, 0x265E5A51, 0xE9B6C7AA, 0xD62F105D, 0x02441453, 0xD8A1E681, 0xE7D3FBC8, 0x21E1CDE6, 0xC33707D6, 0xF4D50D87, 0x455A14ED, 0xA9E3E905, 0xFCEFA3F8, 0x676F02D9, 0x8D2A4C8A,
            0xFFFA3942, 0x8771F681, 0x6D9D6123, 0xFDE5380C, 0xA4BEEA44, 0x4BDECFA9, 0xF6BB4B60, 0xBEBFBC70, 0x289B7EC6, 0xEAA127FA, 0xD4EF3085, 0x04881D05, 0xD9D4D039, 0xE6DB99E5, 0x1FA27CF8, 0xC4AC5665,
            0xF4292244, 0x432AFF97, 0xAB9423A7, 0xFC93A039, 0x655B59C3, 0x8F0CCC92, 0xFFEFF47D, 0x85845DD1, 0x6FA87E4F, 0xFE2CE6E0, 0xA3014314, 0x4E0811A1, 0xF7537E82, 0xBD3AF235, 0x2AD7D2BB, 0xEB86D391,
        ]
        for offset in range(0, len(data), 64):
            words = list(struct.unpack("<16I", data[offset: offset + 64])); a, b, c, d = a0, b0, c0, d0
            for i in range(64):
                f, g = (((b & c) | ((~b) & d), i) if i < 16 else ((d & b) | (c & (~d)), (5 * i + 1) % 16) if i < 32 else (b ^ c ^ d, (3 * i + 5) % 16) if i < 48 else (c ^ (b | (~d)), (7 * i) % 16))
                f = (f + a + table[i] + words[g]) & 0xFFFFFFFF; a, d, c, b = d, c, b, (b + GDStudioMusicClient.leftrotate(f, shifts[i])) & 0xFFFFFFFF
            a0 = (a0 + a) & 0xFFFFFFFF; b0 = (b0 + b) & 0xFFFFFFFF; c0 = (c0 + c) & 0xFFFFFFFF; d0 = (d0 + d) & 0xFFFFFFFF
        return struct.pack("<4I", a0, b0, c0, d0).hex()
    '''normalizeversion'''
    @staticmethod
    def normalizeversion(version: str) -> str:
        return "".join(part.zfill(2) if len(part) == 1 else part for part in version.split("."))
    '''makesign'''
    @staticmethod
    def makesign(payload: str, server_time: str | int, host: str = "music.gdstudio.xyz", version: str = "2026.06.16") -> str:
        time_prefix, version_text = str(server_time)[:9], GDStudioMusicClient.normalizeversion(version)
        return GDStudioMusicClient.gdstudiomd5(f"{time_prefix}|{host}|{version_text}|{payload}")[-8:].upper()
    '''_getservertime'''
    def _getservertime(self, request_overrides: dict = None) -> str:
        with suppress(Exception): (resp := self.get(GDStudioMusicClient.TIME_URL, **(request_overrides or {}))).raise_for_status()
        ts = str(int(time.time()) if not locals().get('resp') or not hasattr(locals().get('resp'), 'text') else resp.text.strip())
        return ts
    '''_sign'''
    def _sign(self, payload: str, request_overrides: dict = None) -> str:
        return GDStudioMusicClient.makesign(payload=payload, server_time=self._getservertime(request_overrides), host=GDStudioMusicClient.HOST, version=GDStudioMusicClient.VERSION)
    '''_getsongurl'''
    def _getsongurl(self, song_id: str, source: str = "netease", br: int = 999, request_overrides: dict = None) -> Dict[str, Any]:
        encoded_id = GDStudioMusicClient.jsencodeuricomponent((song_id := str(song_id)))
        data = {"types": "url", "id": song_id, "source": source, "br": str(br), "s": self._sign(encoded_id, request_overrides)}
        (resp := self.post(GDStudioMusicClient.API_URL, data=data, timeout=10, **(request_overrides or {}))).raise_for_status()
        return resp2json(resp=resp)
    '''_getpic'''
    def _getpic(self, pic_id: str, source: str = "netease", size: int = 300, request_overrides: dict = None) -> Dict[str, Any]:
        kuwo_cover_cdn_hosts = ["http://img1.kwcdn.kuwo.cn/star/albumcover/", "http://img2.kwcdn.kuwo.cn/star/albumcover/", "http://img3.kwcdn.kuwo.cn/star/albumcover/"]
        if source in {'kuwo'}: return {'url': urljoin(kuwo_cover_cdn_hosts[0], f'{size}/' + str(pic_id)[4:] if str(pic_id).startswith('120/') else pic_id)}
        if source in {'apple'}: return {'url': str(pic_id).format(w=size, h=size)}
        if source in {'bilibili'}: return {'url': pic_id if str(pic_id).startswith('http') else f"https:{pic_id}"}
        encoded_id = GDStudioMusicClient.jsencodeuricomponent((pic_id := str(pic_id)))
        data = {"types": "pic", "id": pic_id, "source": source, "size": str(size), "s": self._sign(encoded_id, request_overrides)}
        (resp := self.post(GDStudioMusicClient.API_URL, data=data, timeout=10, **(request_overrides or {}))).raise_for_status()
        return resp2json(resp=resp)
    '''_getlyric'''
    def _getlyric(self, lyric_id: str, source: str = "netease", request_overrides: dict = None) -> Dict[str, Any]:
        encoded_id = GDStudioMusicClient.jsencodeuricomponent((lyric_id := str(lyric_id)))
        data = {"types": "lyric", "id": lyric_id, "source": source, "s": self._sign(encoded_id, request_overrides)}
        (resp := self.post(GDStudioMusicClient.API_URL, data=data, timeout=10, **(request_overrides or {}))).raise_for_status()
        return resp2json(resp=resp)
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, allowed_music_sources, encoded_keyword = rule or {}, request_overrides or {}, copy.deepcopy(self.allowed_music_sources), GDStudioMusicClient.jsencodeuricomponent(keyword)
        (default_rule := {"types": "search", "count": str(self.search_size_per_page), "pages": "1", "name": keyword, "s": self._sign(encoded_keyword, request_overrides)}).update(rule)
        # construct search urls
        base_url, search_urls, page_size = GDStudioMusicClient.API_URL, [], int(default_rule['count'])
        for source in GDStudioMusicClient.SUPPORTED_SITES:
            if source not in allowed_music_sources: continue
            (source_default_rule := copy.deepcopy(default_rule))['source'] = source; count = 0
            while self.search_size_per_source > count:
                (rule := copy.deepcopy(source_default_rule))["pages"] = str(int(count // page_size) + 1)
                search_urls.append({'url': base_url, 'data': rule, 'page_no': str(int(count // page_size) + 1), 'source': source})
                count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = None, request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        self.default_headers, request_overrides, search_meta, search_result_idx = copy.deepcopy(self.default_headers), copy.deepcopy(request_overrides or {}), copy.deepcopy(search_url), -1
        search_url, post_data, page_no, root_source = search_meta.pop('url'), search_meta.pop('data'), search_meta.pop('page_no'), search_meta.pop('source')
        task_id = progress.add_task(f"{self.source}.{root_source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.post(GDStudioMusicClient.API_URL, data=post_data, timeout=10, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp=resp)[:self.search_size_per_page]):
                # --update progress
                progress.update(task_id, description=f"{self.source}.{root_source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}", completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('id'))) or (not (song_url_id := search_result.get('url_id'))) or (not (root_source := search_result.get('source'))): continue
                with suppress(Exception): download_result = {}; download_result = self._getsongurl(song_url_id, source=root_source, br=(br := GDStudioMusicClient.MUSIC_QUALITIES[0]), request_overrides=request_overrides)
                if not download_result.get('url') or download_result.get('size') in {0, '0'} or download_result.get('br') in {-1, '-1'}: continue
                download_url = urljoin(GDStudioMusicClient.BASE_URL, download_url) if not str((download_url := download_result.get('url'))).startswith('http') else download_url
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                if not download_url_status['ok']: download_url_status: dict = self.audio_link_tester.test(url=f'https://music-proxy.gdstudio.org/{download_url}', request_overrides=request_overrides, renew_session=True)
                default_download_headers = self.default_bilibili_download_headers if root_source in {'bilibili'} else self.default_download_headers
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join(search_result.get('artist') or [])), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                    identifier=song_id, duration_s=safeextractfromdict(search_result, ['extra_data', 'duration'], None), duration=SongInfoUtils.seconds2hms(safeextractfromdict(search_result, ['extra_data', 'duration'], None)), lyric=None, cover_url=None, download_url=download_url_status['download_url'], download_url_status=download_url_status, root_source=root_source, default_download_headers=default_download_headers
                )
                with suppress(Exception): song_info.duration_s, song_info.duration = (song_info.duration_s / 1000, SongInfoUtils.seconds2hms(song_info.duration_s / 1000)) if (root_source in {'spotify'}) else (song_info.duration_s, song_info.duration)
                song_info.ext = 'm4a' if song_info.ext in {'m4s', 'mp4'} else song_info.ext
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                # --cover results
                with suppress(Exception): download_result['cover'] = self._getpic(search_result.get('pic_id'), source=root_source, request_overrides=request_overrides)
                song_info.cover_url = safeextractfromdict(download_result, ['cover', 'url'], None)
                # --lyric results
                with suppress(Exception): lyric_result = {}; lyric_result = self._getlyric(search_result.get('lyric_id'), source=root_source, request_overrides=request_overrides)
                if not (lyric := cleanlrc(lyric_result.get('lyric') or '')) or lyric in {'NULL', 'null', 'None', 'none'} or '歌词获取失败' in lyric: lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
                song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
                song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
                # --supplement
                if song_info.duration in {'00:00:00', 'None', 'none', 'NULL', 'null', '-:-:-'}: song_info.duration_s= extractdurationsecondsfromlrc(song_info.lyric or ''); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
                if song_info.duration in {'00:00:00', 'None', 'none', 'NULL', 'null', '-:-:-'}: song_info.duration_s = SongInfoUtils.estimatedurationwithfilesizebr(song_info.file_size_bytes, float(download_result.get('br', br)), return_seconds=True); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
            # --update progress
            progress.update(task_id, description=f'{self.source}.{root_source}._search >>> {search_result_idx+1} search results processed on page {page_no}')
        # failure
        except Exception as err:
            progress.update(task_id, description=f'{self.source}.{root_source}._search >>> {keyword} on page {page_no} (Error: {err})')
            self.logger_handle.error(f'{self.source}.{root_source}._search >>> {keyword} on page {page_no} (Error: {err})', disable_print=self.disable_print)
        # return
        return song_infos