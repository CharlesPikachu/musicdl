'''
Function:
    Implementation of YouTubeMusicClient: https://music.youtube.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import random
from ytmusicapi import YTMusic
from .base import BaseMusicClient
from rich.progress import Progress
from ..utils import legalizestring, resp2json, isvalidresp, usesearchheaderscookies, AudioLinkTester, WhisperLRC


'''YouTubeMusicClient'''
class YouTubeMusicClient(BaseMusicClient):
    source = 'YouTubeMusicClient'
    def __init__(self, **kwargs):
        super(YouTubeMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {}
        self.default_download_headers = {}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_searchwithytsearchanddownloadmp3rapidapi'''
    def _searchwithytsearchanddownloadmp3rapidapi(self, keyword: str, request_overrides: dict = None):
        # init
        request_overrides = request_overrides or {}
        repaidapi_keys = [
            "1556f6ccb2msh64b807485156b33p12a66djsn7e197bc23f19", "323be663ccmsh35173cb3c5403c2p10f08fjsnad5cf7b49fa9",
            "7ca8a11abdmsh7eb89d767db710cp191ce7jsnf0274562b5b9", "14a93bf7a5msh51f11db7d121aeap1c4625jsn5cfbb89ff05b", 
            "6111b62d2dmshd13d20b55abbbe8p1f8551jsn2e425d987b94", "fcdf2c5ba1msh397175bf89fe87ep19fe51jsn76bc6eddb936",
            "ab47a3c2camsh4097dc8ff0fb89fp1d95e6jsna047ccc76ab6", "3b6e8de0bfmshf1110629d4a95b0p11b000jsn264f29acc2b0",
            "9203689df7msh9f35abfe7467ce8p12ca71jsn625743a17f66", "ef908b5eeamsh50984dd5b890d6ep1ab791jsn2fb248ebf19a",
        ]
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "X-Rapidapi-Host": "youtube-music-api3.p.rapidapi.com",
            "X-Rapidapi-Key": random.choice(repaidapi_keys),
            "Referer": "https://music-download-lake.vercel.app/",
            "Origin": "https://music-download-lake.vercel.app",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self.default_search_headers = self.default_headers
        # search
        params = {'q': keyword, 'type': 'song', 'limit': self.search_size_per_source}
        for repaidapi_key in repaidapi_keys:
            try:
                self.default_headers['X-Rapidapi-Key'] = repaidapi_key
                resp = self.get(f'https://youtube-music-api3.p.rapidapi.com/search', params=params, **request_overrides)
                resp.raise_for_status()
                search_results = resp2json(resp=resp)['result'][:self.search_size_per_source]
                assert len(search_results) > 0
                break
            except:
                continue
        # return
        return search_results
    '''_parsewithytsearchanddownloadmp3rapidapi'''
    def _parsewithytsearchanddownloadmp3rapidapi(self, vid: str, request_overrides: dict = None):
        # init
        request_overrides = request_overrides or {}
        repaidapi_keys = [
            "1556f6ccb2msh64b807485156b33p12a66djsn7e197bc23f19", "323be663ccmsh35173cb3c5403c2p10f08fjsnad5cf7b49fa9",
            "7ca8a11abdmsh7eb89d767db710cp191ce7jsnf0274562b5b9", "14a93bf7a5msh51f11db7d121aeap1c4625jsn5cfbb89ff05b", 
            "6111b62d2dmshd13d20b55abbbe8p1f8551jsn2e425d987b94", "fcdf2c5ba1msh397175bf89fe87ep19fe51jsn76bc6eddb936",
            "ab47a3c2camsh4097dc8ff0fb89fp1d95e6jsna047ccc76ab6", "3b6e8de0bfmshf1110629d4a95b0p11b000jsn264f29acc2b0",
            "9203689df7msh9f35abfe7467ce8p12ca71jsn625743a17f66", "ef908b5eeamsh50984dd5b890d6ep1ab791jsn2fb248ebf19a",
        ]
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "X-Rapidapi-Host": "yt-search-and-download-mp3.p.rapidapi.com",
            "X-Rapidapi-Key": random.choice(repaidapi_keys),
            "Referer": "https://music-download-lake.vercel.app/",
            "Origin": "https://music-download-lake.vercel.app",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self.default_search_headers = self.default_headers
        # parse
        for repaidapi_key in repaidapi_keys:
            try:
                self.default_headers['X-Rapidapi-Key'] = repaidapi_key
                resp = self.get(f'https://yt-search-and-download-mp3.p.rapidapi.com/mp3?url=https://www.youtube.com/watch?v={vid}', **request_overrides)
                resp.raise_for_status()
                download_result = resp2json(resp=resp)
                download_url = download_result['download']
                download_url_status = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).test(download_url, request_overrides)
                if download_url_status['ok']: break
            except:
                continue
        # return
        return download_result, download_url, download_url_status
    '''_parsvidewithmp3youtube'''
    def _parsvidewithmp3youtube(self, vid: str, request_overrides: dict = None):
        # init
        request_overrides = request_overrides or {}
        self.default_headers = {
            "Content-Type": "application/json", "Origin": "https://iframe.y2meta-uk.com", "Accept": "*/*",
        }
        self.default_search_headers = self.default_headers
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
            # --search results, if search scale not very large, try rapid api first
            if self.search_size_per_source <= 5:
                try:
                    search_results = self._searchwithytsearchanddownloadmp3rapidapi(keyword=keyword, request_overrides=request_overrides)
                except:
                    search_results = ytmusic_api.search(**search_rule)
                    search_results = [s for s in search_results if s['resultType'] in ['song']]
            else:
                search_results = ytmusic_api.search(**search_rule)
                search_results = [s for s in search_results if s['resultType'] in ['song']]
            for search_result in search_results:
                # --download results
                if 'videoId' not in search_result: continue
                # --init download related results
                download_result, download_url, download_url_status, ext, file_size, duration = {}, "", {}, 'mp3', 'NULL', search_result.get('duration')
                # --parse with _parsewithytsearchanddownloadmp3rapidapi
                try:
                    download_result, download_url, download_url_status = self._parsewithytsearchanddownloadmp3rapidapi(vid=search_result['videoId'], request_overrides=request_overrides)
                    try:
                        download_result_suppl = AudioLinkTester(headers=self.default_download_headers, cookies=self.default_download_cookies).probe(download_url, request_overrides)
                    except:
                        download_result_suppl = {'download_url': download_url, 'file_size': 'NULL', 'ext': 'NULL'}
                    download_result['download_result_suppl'] = download_result_suppl
                    ext, file_size = download_result_suppl['ext'], download_result_suppl['file_size']
                    if ext in ['NULL']: ext = 'mp3'
                except:
                    download_result, download_url, download_url_status, ext, file_size, duration = {}, "", {}, 'mp3', 'NULL', search_result.get('duration')
                # --parse with _parsvidewithmp3youtube
                if not download_result or not download_url:
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
                        download_result, download_url, download_url_status, ext, file_size, duration = {}, "", {}, 'mp3', 'NULL', search_result.get('duration')
                # --fail to parse
                if not download_result or not download_url: continue
                # --lyric
                try:
                    if os.environ.get('ENABLE_WHISPERLRC', 'False').lower() == 'true':
                        lyric_result = WhisperLRC(model_size_or_path='small').fromurl(
                            download_url, headers=self.default_download_headers, cookies=self.default_download_cookies, request_overrides=request_overrides
                        )
                        lyric = lyric_result['lyric']
                    else:
                        lyric_result, lyric = dict(), 'NULL'
                except:
                    lyric_result, lyric = dict(), 'NULL'
                # --construct song_info
                singers = ', '.join([singer.get('name', 'NULL') for singer in search_result.get('artists', [])]) if search_result.get('artists') else search_result.get('author', 'NULL')
                format_duration = lambda d: "{:02}:{:02}:{:02}".format(*([0] * (3 - len(d.split(":"))) + list(map(int, d.split(":")))))
                song_info = dict(
                    source=self.source, raw_data=dict(search_result=search_result, download_result=download_result, lyric_result=lyric_result), 
                    download_url_status=download_url_status, download_url=download_url, ext=ext, file_size=file_size, lyric=lyric, duration=format_duration(duration),
                    song_name=legalizestring(search_result.get('title', 'NULL'), replace_null_string='NULL'), 
                    singers=legalizestring(singers, replace_null_string='NULL'), 
                    album=legalizestring(search_result.get('album', 'NULL'), replace_null_string='NULL'),
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