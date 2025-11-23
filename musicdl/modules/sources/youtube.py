'''
Function:
    Implementation of YouTubeMusicClient: https://music.youtube.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
from ytmusicapi import YTMusic
from .base import BaseMusicClient
from rich.progress import Progress
from ..utils import legalizestring, resp2json, isvalidresp, seconds2hms, usesearchheaderscookies, AudioLinkTester


'''YouTubeMusicClient'''
class YouTubeMusicClient(BaseMusicClient):
    source = 'YouTubeMusicClient'
    def __init__(self, **kwargs):
        super(YouTubeMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {}
        self.default_download_headers = {}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_parsvidewithmp3youtube'''
    def _parsvidewithmp3youtube(self, vid: str, request_overrides: dict = None):
        # init
        request_overrides = request_overrides or {}
        self.default_headers = {
            "Content-Type": "application/json", "Origin": "https://iframe.y2meta-uk.com", "Accept": "*/*",
        }
        self.default_download_headers = {
            "Content-Type": "application/json", "Origin": "https://iframe.y2meta-uk.com", "Accept": "*/*", "Referer": "https://iframe.y2meta-uk.com/"
        }
        # get key
        resp = self.get('https://api.mp3youtube.cc/v2/sanity/key', **request_overrides)
        resp.raise_for_status()
        key = resp2json(resp)['key']
        # parse
        self.default_headers.update(dict(key=key))
        for quality in ['320', '256', '192', '128', '64']:
            audio_payload = {"link": f"https://youtu.be/{vid}", "format": "mp3", "audioBitrate": quality, "videoQuality": "720", "vCodec": "h264"}
            resp = self.post('https://api.mp3youtube.cc/v2/converter', json=audio_payload, **request_overrides)
            if not isvalidresp(resp): continue
            download_result = resp2json(resp=resp)
            if not download_result.get('url'): continue
            download_url = download_result['url']
            download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).test(download_url, request_overrides)
            if download_url_status['ok']: break
        # return
        return download_result, download_url, download_url_status
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # adapt ytmusicapi to conduct music file search
        proxies = None
        if self.proxied_session_client is not None: proxies = self.proxied_session_client.getrandomproxy()
        ytmusic_api = YTMusic(
            auth=rule.get('rule', None), user=rule.get('user', None), requests_session=None, proxies=request_overrides.get('proxies', None) or proxies,
            language=rule.get('language', 'en'), location=rule.get('location', ''), oauth_credentials=rule.get('oauth_credentials', ''), 
        )
        # search rules
        search_rule = {
            'query': keyword, 'filter': rule.get('filter', None), 'scope': rule.get('scope', None), 'limit': self.search_size_per_source,
            'ignore_spelling': rule.get('ignore_spelling', False)
        }
        search_urls = [{'ytmusic_api': ytmusic_api, 'search_rule': search_rule}]
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = {}, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        search_meta = copy.deepcopy(search_url)
        ytmusic_api, search_rule = search_meta['ytmusic_api'], search_meta['search_rule']
        # successful
        try:
            # --search results
            search_results = ytmusic_api.search(**search_rule)
            for search_result in search_results:
                # --only consider specific search results
                if search_result['resultType'] not in ['song']: continue
                # --download results
                if 'videoId' not in search_result: continue
                # --init download related results
                download_result, download_url, download_url_status, ext, file_size = {}, "", {}, 'mp3', 'NULL'
                # --parse with _parsvidewithmp3youtube
                try:
                    download_result, download_url, download_url_status = self._parsvidewithmp3youtube(vid=search_result['videoId'], request_overrides=request_overrides)
                    try:
                        download_result_suppl = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).probe(download_url, request_overrides)
                    except:
                        download_result_suppl = {'download_url': download_url, 'file_size': 'NULL', 'ext': 'NULL'}
                    download_result['download_result_suppl'] = download_result_suppl
                    ext, file_size = download_result_suppl['ext'], download_result_suppl['file_size']
                    if ext in ['NULL']: ext = 'mp3'
                except:
                    download_result, download_url, download_url_status, ext, file_size = {}, "", {}, 'mp3', 'NULL'
                # --fail to parse
                if not download_result or not download_url: continue
                # --lyric
                lyric_result, lyric = {}, 'NULL'
                # --construct song_info
                song_info = dict(
                    source=self.source, raw_data=dict(search_result=search_result, download_result=download_result, lyric_result=lyric_result), 
                    download_url_status=download_url_status, download_url=download_url, ext=ext, file_size=file_size, lyric=lyric, duration=seconds2hms(search_result.get('duration_seconds', 0)),
                    song_name=legalizestring(search_result.get('title', 'NULL'), replace_null_string='NULL'), 
                    singers=legalizestring(', '.join([singer.get('name', 'NULL') for singer in search_result.get('artists', [])]), replace_null_string='NULL'), 
                    album=legalizestring(lyric_result.get('data', {}).get('albumName', 'NULL'), replace_null_string='NULL'),
                    identifier=search_result['videoId'],
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