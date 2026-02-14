'''
Function:
    Implementation of MiguMusicClient: https://music.migu.cn/v5/#/musicLibrary
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
import requests
from .base import BaseMusicClient
from rich.progress import Progress
from urllib.parse import urlencode
from ..utils import byte2mb, resp2json, seconds2hms, legalizestring, safeextractfromdict, usesearchheaderscookies, cleanlrc, SongInfo


'''MiguMusicClient'''
class MiguMusicClient(BaseMusicClient):
    source = 'MiguMusicClient'
    MUSIC_QUALITIES = {'LQ': 'mp3', 'PQ': 'mp3', 'HQ': 'mp3', 'SQ': 'flac', 'ZQ': 'flac', 'Z3D': 'flac', 'ZQ24': 'flac', 'ZQ32': 'flac', }
    def __init__(self, **kwargs):
        super(MiguMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "accept": "application/json, text/plain, */*", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "activityid": "v4_zt_2022_music", "appid": "ce", "channel": "014X031", "connection": "keep-alive", "deviceid": "E60C6B2F-7F11-4362-9FCE-6F1CC86E0F18",
            "host": "c.musicapp.migu.cn", "hwid": "", "imei": "", "h5page": "", "imsi": "", "location-info": "", "mgm-user-agent": "", "oaid": "", "uid": "", "location-data": "", "logid": "h5page[1808]", "mgm-network-operators": "02", "mgm-network-standard": "03", "mgm-network-type": "03", "origin": "https://y.migu.cn",
            "recommendstatus": "1", "referer": "https://y.migu.cn/app/v4/zt/2022/music/index.html", "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", 
            "sec-fetch-site": "same-site", "subchannel": "014X031", "test": "00", "ua": "Android_migu", "version": "6.8.8", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        }
        self.default_download_headers = {
            "accept": "*/*", "accept-encoding": "identity;q=1, *;q=0", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "connection": "keep-alive", "host": "freetyst.nf.migu.cn", "range": "bytes=0-", "sec-fetch-mode": "no-cors", "sec-fetch-site": "same-site",
            "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "audio", "referer": "https://y.migu.cn/app/v4/zt/2022/music/index.html",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {"text": keyword, 'pageNo': 1, 'pageSize': 20, 'isCopyright': 1, 'sort': 1, 'searchSwitch': {"song": 1, "album": 0, "singer": 0, "tagSong": 1, "mvSong": 0, "bestShow": 1}}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://c.musicapp.migu.cn/v1.0/content/search_all.do?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['pageSize'] = page_size
            page_rule['pageNo'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        safe_fetch_filesize_func = lambda meta: (lambda s: (lambda: float(s))() if s.replace('.', '', 1).isdigit() else 0)(str(meta.get('size') or meta.get('iosSize') or meta.get('androidSize') or '0').removesuffix('MB').strip()) if isinstance(meta, dict) else 0
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['songResultData']['result']
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('copyrightId' not in search_result) or ('contentId' not in search_result): continue
                song_info = SongInfo(source=self.source)
                for rate in sorted((search_result.get('rateFormats', []) or []) + (search_result.get('newRateFormats', []) or []), key=lambda x: int(safe_fetch_filesize_func(x)), reverse=True):
                    if not isinstance(rate, dict): continue
                    if byte2mb(safe_fetch_filesize_func(rate)) == 'NULL' or (not rate.get('formatType', '')) or (not rate.get('resourceType', '')): continue
                    try:
                        resp = self.get(f"https://c.musicapp.migu.cn/MIGUM3.0/strategy/listen-url/v2.4?resourceType={rate['resourceType']}&netType=01&scene=&toneFlag={rate['formatType']}&contentId={search_result['contentId']}&copyrightId={search_result['copyrightId']}&lowerQualityContentId={search_result['contentId']}", **request_overrides)
                        resp.raise_for_status()
                        download_result = resp2json(resp=resp)
                    except:
                        continue
                    download_url = safeextractfromdict(download_result, ['data', 'url'], "") or f"https://app.pd.nf.migu.cn/MIGUM3.0/v1.0/content/sub/listenSong.do?channel=mx&copyrightId={search_result['copyrightId']}&contentId={search_result['contentId']}&toneFlag={rate['formatType']}&resourceType={rate['resourceType']}&userId=15548614588710179085069&netType=00"
                    if not download_url: continue
                    download_url = re.sub(r'(?<=/)MP3_128_16_Stero(?=/)', 'MP3_320_16_Stero', download_url)
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)),
                        singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['singers'], []) or []) if isinstance(singer, dict) and singer.get('name')])),
                        album=legalizestring(', '.join([album.get('name') for album in (safeextractfromdict(search_result, ['albums'], []) or []) if isinstance(album, dict) and album.get('name')])),
                        ext=MiguMusicClient.MUSIC_QUALITIES.get(rate['formatType'], 'mp3'), file_size='NULL', identifier=search_result['contentId'], duration_s=safeextractfromdict(download_result, ['data', 'song', 'duration'], 0),
                        duration=seconds2hms(safeextractfromdict(download_result, ['data', 'song', 'duration'], 0)), lyric=None, cover_url=safeextractfromdict(search_result, ['imgItems', -1, 'img'], None), 
                        download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                    )
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] != 'NULL') else song_info.ext
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: continue
                # --lyric results
                try:
                    lyric_url = safeextractfromdict(search_result, ['lyricUrl'], '').replace('http://', 'https://')
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "Referer": "https://y.migu.cn/"}
                    resp = requests.get(lyric_url, headers=headers, allow_redirects=True, **request_overrides)
                    resp.raise_for_status()
                    resp.encoding = 'utf-8'
                    lyric, lyric_result = cleanlrc(resp.text), {'lyric': cleanlrc(resp.text)}
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