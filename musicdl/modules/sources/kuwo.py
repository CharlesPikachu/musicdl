'''
Function:
    Implementation of KuwoMusicClient: http://www.kuwo.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import legalizestring, seconds2hms, probesongurl


'''KuwoMusicClient'''
class KuwoMusicClient(BaseMusicClient):
    source = 'KuwoMusicClient'
    def __init__(self, **kwargs):
        super(KuwoMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = {}):
        # search rules
        default_rule = {
            "vipver": "1", "client": "kt", "ft": "music", "cluster": "0", "strategy": "2012", "encoding": "utf8",
            "rformat": "json", "mobi": "1", "issubtitle": "1", "show_copyright_off": "1", "pn": "1", "rn": "20",
            "all": keyword,
        }
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'http://www.kuwo.cn/search/searchMusicBykeyWord?'
        search_urls, page_size, count = [], 20, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['pn'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    def _search(self, search_url: str, request_overrides: dict = {}, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp.json()['abslist']
            for search_result in search_results:
                # --download results
                params = {
                    'format': 'aac|mp3', 'rid': search_result['MUSICRID'], 'type': 'convert_url', 'response': 'url'
                }
                resp = self.get('http://antiserver.kuwo.cn/anti.s', params=params, **request_overrides)
                if (resp is None) or (resp.status_code not in [200]):
                    continue
                download_url = resp.text.strip()
                if (not download_url) or (not (download_url.startswith('http://') or download_url.startswith('https://'))):
                    continue
                try:
                    download_result = probesongurl(download_url)
                except:
                    download_result = {'download_url': download_url}
                if 'ext' not in download_result or download_result['ext'] == 'NULL':
                    download_result['ext'] = download_url.split('.')[-1]
                duration = int(search_result.get('DURATION', 0))
                if duration <= 15: continue
                duration = seconds2hms(duration)
                # --lyric results
                params = {'musicId': search_result['MUSICRID'].strip('MUSIC_'), 'httpsStatus': '1'}
                resp = self.get('http://m.kuwo.cn/newh5/singles/songinfoandlrc', params=params, **request_overrides)
                if (resp is not None) and (resp.status_code in [200]):
                    lyric_result: dict = resp.json() or {'data': {}}
                    try:
                        lyric = lyric_result.get('data', {}).get('lrclist', []) or 'NULL'
                    except:
                        lyric = 'NULL'
                else:
                    lyric_result, lyric = {}, 'NULL'
                # --construct song_info
                song_info = dict(
                    source=self.source, raw_data=dict(search_result=search_result, download_result=download_result, lyric_result=lyric_result), 
                    download_url=download_url, ext=download_result['ext'], file_size=download_result['file_size'], lyric=lyric, duration=duration,
                    song_name=legalizestring(search_result.get('SONGNAME', 'NULL'), replace_null_string='NULL'), 
                    singers=legalizestring(search_result.get('ARTIST', 'NULL'), replace_null_string='NULL'), 
                    album=legalizestring(search_result.get('ALBUM', 'NULL'), replace_null_string='NULL')
                )
                # --append to song_infos
                song_infos.append(song_info)
            # --update progress
            progress.advance(progress_id, 1)
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} [success]")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} [error: {err}]")
        # return
        return song_infos