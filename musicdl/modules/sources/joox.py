'''
Function:
    Implementation of JooxMusicClient: https://www.joox.com/intl
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
import base64
import json_repair
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import legalizestring, byte2mb, resp2json, isvalidresp, seconds2hms, usesearchheaderscookies, AudioLinkTester


'''JooxMusicClient'''
class JooxMusicClient(BaseMusicClient):
    source = 'JooxMusicClient'
    def __init__(self, **kwargs):
        super(JooxMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Cookie': 'wmid=142420656; user_type=1; country=id; session_key=2a5d97d05dc8fe238150184eaf3519ad;',
            'X-Forwarded-For': '36.73.34.109'
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = {}, request_overrides: dict = {}):
        # search rules
        default_rule = {'country': 'sg', 'lang': 'zh_cn', 'keyword': keyword}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://cache.api.joox.com/openjoox/v3/search?'
        search_urls, page_size, count = [], self.search_size_per_source, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = {}, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # successful
        try:
            # --search results
            resp = self.session.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = []
            for section in resp2json(resp)['section_list']:
                for items in section['item_list']:
                    search_results.extend(items.get('song', []))
            for search_result in search_results:
                # --download results
                if 'song_info' not in search_result or 'id' not in search_result['song_info']:
                    continue
                params = {'songid': search_result['song_info']['id'], 'lang': 'zh_cn', 'country': 'sg'}
                resp = self.get('https://api.joox.com/web-fcgi-bin/web_get_songinfo', params=params, **request_overrides)
                download_result = json_repair.loads(resp.text.replace('MusicInfoCallback(', '')[:-1])
                kbps_map = json_repair.loads(download_result['kbps_map'])
                for quality in [('r320Url', '320'), ('r192Url', '192'), ('mp3Url', '128'), ('m4aUrl', '96')]:
                    if (not kbps_map.get(quality[1])) or (not download_result.get(quality[0])):
                        continue
                    download_url: str = download_result.get(quality[0])
                    file_size = byte2mb(kbps_map.get(quality[1], '0'))
                    ext = download_url.split('.')[-1].split('?')[0]
                    duration = seconds2hms(download_result.get('minterval', '0'))
                    download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).test(download_url, request_overrides)
                    if download_url_status['ok']: break
                if not download_url: continue
                if not download_url_status['ok']: continue
                # --lyric results
                params = {'musicid': search_result['song_info']['id'], 'country': 'sg', 'lang': 'zh_cn'}
                resp = self.get('https://api.joox.com/web-fcgi-bin/web_lyric', params=params, **request_overrides)
                if isvalidresp(resp):
                    lyric_result: dict = json_repair.loads(resp.text.replace('MusicJsonCallback(', '')[:-1])
                else:
                    lyric_result = {}
                try:
                    lyric = base64.b64decode(lyric_result.get('lyric', '')).decode('utf-8') or 'NULL'
                except:
                    lyric = 'NULL'
                # --construct song_info
                song_info = dict(
                    source=self.source, raw_data=dict(search_result=search_result, download_result=download_result, lyric_result=lyric_result), 
                    download_url_status=download_url_status, download_url=download_url, ext=ext, file_size=file_size, lyric=lyric, duration=duration,
                    song_name=legalizestring(search_result['song_info'].get('name', 'NULL'), replace_null_string='NULL'), 
                    singers=legalizestring(', '.join([singer.get('name', 'NULL') for singer in search_result['song_info'].get('artist_list', [])]), replace_null_string='NULL'), 
                    album=legalizestring(search_result['song_info'].get('album_name', 'NULL'), replace_null_string='NULL'),
                    identifier=search_result['song_info']['id'],
                )
                # --append to song_infos
                song_infos.append(song_info)
            # --update progress
            progress.advance(progress_id, 1)
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Error: {err})")
        # return
        return song_infos