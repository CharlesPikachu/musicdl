'''
Function:
    Implementation of BilibiliMusicClient: https://www.bilibili.com/audio/home/?type=9
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import legalizestring, resp2json, usesearchheaderscookies, seconds2hms, safeextractfromdict, SongInfo, AudioLinkTester


'''BilibiliMusicClient'''
class BilibiliMusicClient(BaseMusicClient):
    source = 'BilibiliMusicClient'
    def __init__(self, **kwargs):
        super(BilibiliMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0", "Sec-Ch-Ua": '"Not A(Brand";v="99", "Microsoft Edge";v="121", "Chromium";v="121"', "Referer": "https://www.bilibili.com/", "Sec-Ch-Ua-Mobile": "?0", 
            "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "none", "Sec-Fetch-User": "?1", "Accept-Encoding": "gzip, deflate", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-TW;q=0.5", "Sec-Ch-Ua-Platform": '"Windows"', "Cache-Control": "max-age=0", "Upgrade-Insecure-Requests": "1", 
        }
        self.default_download_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0", "Sec-Ch-Ua": '"Not A(Brand";v="99", "Microsoft Edge";v="121", "Chromium";v="121"', "Referer": "https://www.bilibili.com/", "Sec-Ch-Ua-Mobile": "?0", 
            "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "none", "Sec-Fetch-User": "?1", "Accept-Encoding": "gzip, deflate", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-TW;q=0.5", "Sec-Ch-Ua-Platform": '"Windows"', "Cache-Control": "max-age=0", "Upgrade-Insecure-Requests": "1", 
        }
        self.default_headers = self.default_search_headers
        default_cookies = {
            "buvid3": "2E109C72-251F-3827-FA8E-921FA0D7EC5291319infoc", "b_nut": "1676213591", "i-wanna-go-back": "-1", "_uuid": "2B2D7A6C-8310C-1167-F548-2F1095A6E93F290252infoc", "buvid4": "31696B5F-BB23-8F2B-3310-8B3C55FB49D491966-023021222-WcoPnBbwgLUAZ6TJuAUN8Q%3D%3D", "CURRENT_FNVAL": "4048", "nostalgia_conf": "-1", 
            "bili_jct": "4c583b61b86b16d812a7804078828688", "sid": "8dt1ioao", "bili_ticket": "eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MDQ2MjUzNjAsImlhdCI6MTcwNDM2NjEwMCwicGx0IjotMX0.4E-V4K2y452cy6eexwY2x_q3-xgcNF2qtugddiuF8d4", "rpdid": "|(JY))RmR~|u0J'uY~YkuJ~Ru", "buvid_fp_plain": "undefined", 
            "b_ut": "5", "DedeUserID__ckMd5": "66450f2302095cc5", "DedeUserID": "520271156", "FEED_LIVE_VERSION": "V8", "header_theme_version": "CLOSE", "CURRENT_QUALITY": "80", "enable_web_push": "DISABLE", "buvid_fp": "52ad4773acad74caefdb23875d5217cd", "PVID": "1", "CURRENT_PID": "418c8490-cadb-11ed-b23b-dd640f2e1c14",
            "home_feed_column": "5", "SESSDATA": "8036f42c%2C1719895843%2C19675%2A12CjATThdxG8TyQ2panBpBQcmT0gDKjexwc-zXNGiMnIQ2I9oLVmOiE9YkLao2_aawEhoSVlhGY05PVjVkZWM0T042Z2hZRXBOdElYWXhJa3RpVmZ0M3NvcWw1N0tPcGRVSmRoOVNQZnNHT1JHS05yR1Y1MUFLX3RXeXVJa3NjbEVBQkUxRVN6RFRRIIEC", "fingerprint": "847f1839b443252d91ff0df7465fa8d9", 
            "hit-dyn-v2": "1", "LIVE_BUVID": "AUTO8716766313471956", "hit-new-style-dyn": "1", "bili_ticket_expires": "1704625300", "browser_resolution": "1912-924", "bp_video_offset_520271156": "883089613008142344",
        }
        self.default_search_cookies = self.default_search_cookies or copy.deepcopy(default_cookies)
        self.default_download_cookies = self.default_download_cookies or copy.deepcopy(default_cookies)
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {'__refresh__': 'true', '_extra': '', 'page': 1, 'page_size': self.search_size_per_page, 'platform': 'pc', 'highlight': '1', 'context': '', 'single_column': '0', 'keyword': keyword, 'category_id': '', 'search_type': 'video', 'dynamic_offset': '0', 'preload': 'true', 'com2co': 'true'}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://api.bilibili.com/x/web-interface/search/type?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['page_size'] = page_size
            page_rule['page'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not search_result.get('id')) or (not (song_bvid := search_result.get('bvid'))): return song_info
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            (resp := self.get(f"https://api.bilibili.com/x/web-interface/view?bvid={song_bvid}", **request_overrides)).raise_for_status()
            pages, root_title, song_info = resp2json(resp=resp)['data']['pages'], resp2json(resp=resp)['data']['title'], []
            episodes = [(page["cid"], page["part"]) for page in pages if isinstance(page, dict) and page.get("cid") and page.get("part")]
            for cid, episode_name in episodes:
                try: (resp := self.get(f"https://api.bilibili.com/x/player/playurl?fnval=16&bvid={song_bvid}&cid={cid}")).raise_for_status()
                except Exception: continue
                download_result = resp2json(resp=resp)
                audios = [a for a in (safeextractfromdict(download_result, ['data', 'dash', 'flac', 'audio'], []) or []) if isinstance(a, dict) and (a.get('baseUrl') or a.get('base_url') or a.get('backupUrl') or a.get('backup_url'))]
                if not audios: audios = [a for a in (safeextractfromdict(download_result, ['data', 'dash', 'dolby', 'audio'], []) or []) if isinstance(a, dict) and (a.get('baseUrl') or a.get('base_url') or a.get('backupUrl') or a.get('backup_url'))]
                if not audios: audios = [a for a in (safeextractfromdict(download_result, ['data', 'dash', 'audio'], []) or []) if isinstance(a, dict) and (a.get('baseUrl') or a.get('base_url') or a.get('backupUrl') or a.get('backup_url'))]
                if not audios: continue
                audios_sorted = sorted(audios, key=lambda x: (x.get("bandwidth", 0) or 0, x.get("filesize", 0) or 0), reverse=True)
                if not (download_url := audios_sorted[0].get('baseUrl') or audios_sorted[0].get('base_url') or audios_sorted[0].get('backupUrl') or audios_sorted[0].get('backup_url')): continue
                if isinstance(download_url, list): download_url = download_url[0]
                eps_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(episode_name if episode_name == root_title else f'{root_title}-{episode_name}'), singers=legalizestring(search_result.get('author')), 
                    album=legalizestring(str(song_bvid)), ext='m4a', file_size=None, identifier=cid, duration_s=safeextractfromdict(download_result, ['data', 'dash', 'duration'], 0), duration=seconds2hms(safeextractfromdict(download_result, ['data', 'dash', 'duration'], 0)),
                    lyric=None, cover_url=search_result.get('pic'), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                )
                if eps_info.cover_url and (not eps_info.cover_url.startswith('http')): eps_info.cover_url = f'https:{eps_info.cover_url}'
                eps_info.download_url_status['probe_status'] = self.audio_link_tester.probe(eps_info.download_url, request_overrides)
                eps_info.file_size = eps_info.download_url_status['probe_status']['file_size']; eps_info.ext = eps_info.download_url_status['probe_status']['ext']
                if eps_info.ext in {'m4s', 'mp4'}: eps_info.ext = 'm4a'
                if (eps_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (eps_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): eps_info.ext = eps_info.download_url_status['probe_status']['ext']
                elif (eps_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): eps_info.ext = 'mp3'
                if eps_info.with_valid_download_url: song_info.append(eps_info)
                if self.strict_limit_search_size_per_page and len(song_info) >= self.search_size_per_page: break
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            for search_result in resp2json(resp)['data']['result']:
                # --parse with official apis
                try: song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=None, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                except Exception: song_info = SongInfo(source=self.source)
                # --append to song_infos
                if isinstance(song_info, list) and (not song_info): continue
                if isinstance(song_info, SongInfo) and (not song_info.with_valid_download_url): continue
                if isinstance(song_info, list): song_infos.extend(song_info)
                elif isinstance(song_info, SongInfo): song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: song_infos = song_infos[:self.search_size_per_page]; break
            # --update progress
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}.search >>> {search_url} (Error: {err})")
        # return
        return song_infos