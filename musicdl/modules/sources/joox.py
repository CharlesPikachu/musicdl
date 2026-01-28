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
from rich.progress import Progress
from urllib.parse import urlencode, urlparse, parse_qs
from ..utils import legalizestring, resp2json, seconds2hms, usesearchheaderscookies, safeextractfromdict, extractdurationsecondsfromlrc, cleanlrc, SongInfo


'''JooxMusicClient'''
class JooxMusicClient(BaseMusicClient):
    source = 'JooxMusicClient'
    FUZZY_MUSIC_QUALITIES = [
        "master_tapeUrl", "master_tapeURL", "master_tape_url", "masterTapeUrl", "masterTapeURL", "rMasterTapeUrl", "rMasterTapeURL", "hiresUrl", "hiresURL", "hires_url", "hiResUrl", "hiResURL", "rHiresUrl", "rHiResUrl", "flacUrl", "flacURL", "flac_url", "rFlacUrl", "rflacUrl", "rFLACUrl", 
        "apeUrl", "apeURL", "ape_url", "rApeUrl", "rapeUrl", "stereo_atmosUrl", "stereo_atmosURL", "stereo_atmos_url", "stereoAtmosUrl", "stereoAtmosURL", "atmosUrl", "atmosURL", "atmos_url", "rStereoAtmosUrl", "rAtmosUrl", "dolby448Url", "dolby448URL", "dolby448_url", "rDolby448Url", 
        "rDolby448URL", "dolby256Url", "dolby256URL", "dolby256_url", "rDolby256Url", "rDolby256URL", "r320Url", "r320url", "r320_url", "320Url", "320URL", "320_url", "url320", "mp3320Url", "mp3_320_url", "highUrl", "high_url", "r320oggUrl", "r320OggUrl", "r320OggURL", "r320_ogg_url", 
        "320oggUrl", "320OggUrl", "ogg320Url", "ogg_320_url", "r192oggUrl", "r192OggUrl", "r192OggURL", "r192_ogg_url", "192oggUrl", "192OggUrl", "ogg192Url", "ogg_192_url", "r192k_mnacUrl", "r192k_mnacURL", "r192k_mnac_url", "r192kMnacUrl", "r192kMnacURL", "192k_mnacUrl", "192kMnacUrl",
        "mnac192Url", "mnac_192_url", "r192mnacUrl", "r192Url", "r192url", "r192_url", "192Url", "192URL", "192_url", "url192", "m4a192Url", "aac192Url", "aac_192_url", "mp3Url", "r128Url", "r128url", "r128_url", "128Url", "128URL", "128_url", "url128", "m4a128Url", "aac128Url", "mp3128Url", 
        "m4aUrl", "r96Url", "r96url", "r96_url", "96Url", "96URL", "96_url", "url96", "r48Url", "r48url", "r48_url", "48Url", "48URL", "48_url", "url48", "r24Url", "r24url", "r24_url", "24Url", "24URL", "24_url", "url24", "lowUrl", "low_url", "previewUrl", "preview_url", "refrainUrl", "refrainURL", 
        "refrain_url", "chorusUrl", "chorus_url", "clipUrl", "clip_url", "snippetUrl", "snippet_url", "trialUrl", "trial_url",
    ]
    MUSIC_QUALITIES = [('r320Url', '320'), ('r192Url', '192'), ('mp3Url', '128'), ('m4aUrl', '96')]
    def __init__(self, **kwargs):
        super(JooxMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Cookie': 'wmid=142420656; user_type=1; country=id; session_key=2a5d97d05dc8fe238150184eaf3519ad;', 'X-Forwarded-For': '36.73.34.109',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {'country': 'hk', 'lang': 'zh_TW', 'key': keyword, 'type': '0'}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://cache.api.joox.com/openjoox/v2/search_type?'
        page_rule = copy.deepcopy(default_rule)
        search_urls = [base_url + urlencode(page_rule)]
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        parsed_search_url = parse_qs(urlparse(search_url).query, keep_blank_values=True)
        lang, country = parsed_search_url['lang'][0], parsed_search_url['country'][0]
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp=resp)['tracks']
            for search_result in search_results:
                # --download results
                search_result = search_result[0]
                if not isinstance(search_result, dict) or ('id' not in search_result): continue
                song_info = SongInfo(source=self.source)
                params = {'songid': search_result['id'], 'lang': lang, 'country': country}
                try: resp = self.get('https://api.joox.com/web-fcgi-bin/web_get_songinfo', params=params, **request_overrides); resp.raise_for_status()
                except: continue
                download_result = json_repair.loads(resp.text.removeprefix('MusicInfoCallback(')[:-1])
                candidates = [{'quality': fmq, 'url': download_result.get(fmq)} for fmq in JooxMusicClient.FUZZY_MUSIC_QUALITIES if download_result.get(fmq)]
                for candidate in candidates:
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)),
                        singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['artist_list'], []) or []) if isinstance(singer, dict) and singer.get('name')])),
                        album=legalizestring(safeextractfromdict(search_result, ['album_name'], None)), ext=str(candidate['url']).split('?')[0].split('.')[-1], file_size='NULL', identifier=search_result['id'],
                        duration_s=download_result.get('minterval') or 0, duration=seconds2hms(download_result.get('minterval') or 0), lyric=None, cover_url=safeextractfromdict(download_result, ['imgSrc'], None), 
                        download_url=candidate['url'], download_url_status=self.audio_link_tester.test(candidate['url'], request_overrides),
                    )
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL',)) else song_info.ext
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: continue
                # --lyric results
                params = {'musicid': search_result['id'], 'country': country, 'lang': lang}
                try:
                    resp = self.get('https://api.joox.com/web-fcgi-bin/web_lyric', params=params, **request_overrides)
                    resp.raise_for_status()
                    lyric_result: dict = json_repair.loads(resp.text.replace('MusicJsonCallback(', '')[:-1]) or {}
                    lyric = cleanlrc(base64.b64decode(lyric_result.get('lyric', '')).decode('utf-8')) or 'NULL'
                except:
                    lyric_result, lyric = dict(), 'NULL'
                song_info.raw_data['lyric'] = lyric_result
                song_info.lyric = lyric
                if not song_info.duration or song_info.duration == '-:-:-': song_info.duration = seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
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