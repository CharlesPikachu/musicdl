'''
Function:
    Implementation of KugouMusicClient: http://www.kugou.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
import base64
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import legalizestring, byte2mb, resp2json, isvalidresp, seconds2hms, usesearchheaderscookies, AudioLinkTester


'''KugouMusicClient'''
class KugouMusicClient(BaseMusicClient):
    source = 'KugouMusicClient'
    def __init__(self, **kwargs):
        super(KugouMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = {}, request_overrides: dict = {}):
        # search rules
        default_rule = {'keyword': keyword, 'page': 1, 'pagesize': 10}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'http://songsearch.kugou.com/song_search_v2?'
        search_urls, page_size, count = [], 10, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['page'] = int(count // page_size) + 1
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
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['data']['lists']
            for search_result in search_results:
                # --download results
                if 'FileHash' not in search_result:
                    continue
                resp = self.get(f"http://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash={search_result['FileHash']}", **request_overrides)
                if not isvalidresp(resp): continue
                download_result: dict = resp2json(resp)
                download_url = download_result.get('url') or download_result.get('backup_url')
                if not download_url: continue
                if isinstance(download_url, list): download_url = download_url[0]
                download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).test(download_url, request_overrides)
                if not download_url_status['ok']: continue
                file_size = byte2mb(download_result.get('fileSize', '0'))
                duration = seconds2hms(download_result.get('timeLength', '0'))
                # --lyric results
                params = {'keyword': search_result.get('FileName', ''), 'duration': search_result.get('Duration', '99999'), 'hash': search_result['FileHash']}
                resp = self.get('http://lyrics.kugou.com/search', params=params, **request_overrides)
                if isvalidresp(resp):
                    lyric_result, lyric = resp2json(resp), 'NULL'
                    try:
                        id = lyric_result['candidates'][0]['id']
                        accesskey = lyric_result['candidates'][0]['accesskey']
                        lyric = self.get(f'http://lyrics.kugou.com/download?ver=1&client=pc&id={id}&accesskey={accesskey}&fmt=lrc&charset=utf8').json()['content']
                        lyric = base64.b64decode(lyric).decode('utf-8')
                    except:
                        lyric = 'NULL'
                else:
                    lyric_result, lyric = dict(), 'NULL'
                # --construct song_info
                song_info = dict(
                    source=self.source, raw_data=dict(search_result=search_result, download_result=download_result, lyric_result=lyric_result), 
                    download_url_status=download_url_status, download_url=download_url, ext=download_result.get('extName', 'mp3'), file_size=file_size, 
                    lyric=lyric, duration=duration, song_name=legalizestring(search_result.get('SongName', 'NULL'), replace_null_string='NULL'), 
                    singers=legalizestring(search_result.get('SingerName', 'NULL'), replace_null_string='NULL'), 
                    album=legalizestring(search_result.get('AlbumName', 'NULL'), replace_null_string='NULL'),
                    identifier=search_result['FileHash'],
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