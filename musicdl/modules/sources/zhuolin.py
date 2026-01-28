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
from .base import BaseMusicClient
from rich.progress import Progress
from ..utils import resp2json, seconds2hms, legalizestring, safeextractfromdict, usesearchheaderscookies, extractdurationsecondsfromlrc, cleanlrc, SongInfo, LanZouYParser


'''ZhuolinMusicClient'''
class ZhuolinMusicClient(BaseMusicClient):
    source = 'ZhuolinMusicClient'
    MUSIC_QUALITIES = {'128', '320', '2000'}
    def __init__(self, **kwargs):
        super(ZhuolinMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        }
        self.default_download_headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {"types": "search", 'count': "20", 'source': "freemp3", 'pages': "1", 'name': keyword}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://music.zhuolin.wang/plugns/api.php'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['count'] = page_size
            page_rule['pages'] = int(count // page_size) + 1
            search_urls.append({'url': base_url, 'data': page_rule})
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = None, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        search_meta = copy.deepcopy(search_url)
        search_url = search_meta.pop('url')
        # successful
        try:
            # --search results
            resp = self.post(search_url, verify=False, **search_meta, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp=resp)
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('id' not in search_result): continue
                download_url: str = safeextractfromdict(search_result, ['url'], "")
                if 'lanzouy.com' in urlsplit(download_url).hostname: download_result, download_url = LanZouYParser.parsefromurl(download_url)
                else: download_result = {}
                if (not download_url) or (not download_url.startswith('http')): continue
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)),
                    singers=legalizestring(', '.join(safeextractfromdict(search_result, ['artist'], []) or [])), album=legalizestring(safeextractfromdict(search_result, ['album', 'name'], None)),
                    ext=download_url.split('?')[0].split('.')[-1], file_size=None, identifier=search_result['id'], duration='-:-:-', lyric=None, cover_url=safeextractfromdict(search_result, ['pic'], None), 
                    download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                )
                song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                if not song_info.with_valid_download_url: continue
                # --lyric results
                try:
                    resp = self.post('https://music.zhuolin.wang/plugns/api.php', verify=False, data={'types': 'lyric', 'id': search_result['id'], 'source': 'freemp3'})
                    resp.raise_for_status()
                    lyric_result = resp2json(resp=resp)
                    lyric = safeextractfromdict(lyric_result, ['lyric'], '')
                    if lyric.startswith('http'): lyric = cleanlrc(self.get(lyric, **request_overrides).text)
                    lyric = lyric or 'NULL'
                    song_info.duration_s = extractdurationsecondsfromlrc(lyric)
                    song_info.duration = seconds2hms(song_info.duration_s)
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