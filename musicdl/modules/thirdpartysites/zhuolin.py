'''
Function:
    Implementation of ZhuolinMusicClient: https://music.zhuolin.wang/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
from urllib.parse import urlsplit
from rich.progress import Progress
from ..sources import BaseMusicClient
from ..utils import resp2json, legalizestring, safeextractfromdict, usesearchheaderscookies, extractdurationsecondsfromlrc, cleanlrc, SongInfo, LanZouYParser, AudioLinkTester, SongInfoUtils


'''ZhuolinMusicClient'''
class ZhuolinMusicClient(BaseMusicClient):
    source = 'ZhuolinMusicClient'
    MUSIC_QUALITIES = {'128', '320', '2000'}
    def __init__(self, **kwargs):
        super(ZhuolinMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        (default_rule := {"types": "search", 'count': "20", 'source': "freemp3", 'pages': "1", 'name': keyword}).update(rule)
        # construct search urls
        base_url = 'https://music.zhuolin.wang/plugns/api.php'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            (page_rule := copy.deepcopy(default_rule))['count'] = page_size
            page_rule['pages'] = int(count // page_size) + 1
            search_urls.append({'url': base_url, 'data': page_rule})
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = None, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}; search_url = (search_meta := copy.deepcopy(search_url)).pop('url')
        # successful
        try:
            # --search results
            (resp := self.post(search_url, verify=False, **search_meta, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp=resp):
                # --download results
                if not isinstance(search_result, dict) or (not (song_id := search_result.get('id'))): continue
                download_url, download_result = safeextractfromdict(search_result, ['url'], ""), {}
                if (not download_url) or (not str(download_url).startswith('http')): continue
                if 'lanzouy.com' in urlsplit(str(download_url)).hostname: download_result, download_url = LanZouYParser.parsefromurl(download_url)
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(', '.join(search_result.get('artist') or [])), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None)), ext=download_url_status['ext'], 
                    file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric=None, cover_url=search_result.get('pic'), download_url=download_url_status['download_url'], download_url_status=download_url_status,
                )
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                # --lyric results
                try:
                    (resp := self.post('https://music.zhuolin.wang/plugns/api.php', verify=False, data={'types': 'lyric', 'id': song_id, 'source': 'freemp3'})).raise_for_status()
                    lyric_result = resp2json(resp=resp); lyric = safeextractfromdict(lyric_result, ['lyric'], '')
                    if lyric.startswith('http'): lyric = cleanlrc(self.get(lyric, **request_overrides).text)
                    lyric = lyric or 'NULL'; song_info.duration_s = extractdurationsecondsfromlrc(lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
                except:
                    lyric_result, lyric = {}, 'NULL'
                song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
                song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
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