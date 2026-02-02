'''
Function:
    Implementation of SoundCloudMusicClient: https://soundcloud.com/discover
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils import legalizestring, resp2json, usesearchheaderscookies, seconds2hms, safeextractfromdict, SongInfo


'''SoundCloudMusicClient'''
class SoundCloudMusicClient(BaseMusicClient):
    source = 'SoundCloudMusicClient'
    def __init__(self, **kwargs):
        super(SoundCloudMusicClient, self).__init__(**kwargs)
        if self.default_cookies: assert ("oauth_token" in self.default_cookies), '"oauth_token" should be configured, refer to https://developers.soundcloud.com/docs#authentication'
        self.client_id = None
        self.default_search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        }
        self.default_download_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        }
        self.default_headers = self.default_search_headers
        if self.default_search_cookies: self.default_search_headers.update({'Authorization': f'OAuth {self.default_cookies["oauth_token"]}'})
        if self.default_download_cookies: self.default_download_headers.update({'Authorization': f'OAuth {self.default_cookies["oauth_token"]}'})
        self._initsession()
    '''_updateclientid'''
    def _updateclientid(self, request_overrides: dict = None):
        if self.client_id: return
        request_overrides = request_overrides or {}
        try: resp = self.session.get('https://soundcloud.com/', **request_overrides); resp.raise_for_status()
        except: self.client_id = '9jZvetLfDs6An08euQgJ0lYlHkKdGFzV'; return
        script_urls = re.findall(r'<script[^>]+src="([^"]+)"', resp.text)
        for url in reversed(script_urls):
            try: resp = self.session.get(url, **request_overrides); m = re.search(r'client_id\s*:\s*"([0-9a-zA-Z]{32})"', resp.text) if resp.status_code == 200 else None
            except Exception: continue
            if m: self.client_id = m.group(1); return
        self.client_id = '9jZvetLfDs6An08euQgJ0lYlHkKdGFzV'; return
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        self._updateclientid(request_overrides=request_overrides)
        # search rules
        default_rule = {
            'q': keyword, 'sc_a_id': 'ab15798461680579b387acf67441b40149e528cd', 'facet': 'genre', 'user_id': '704923-225181-486085-807554', 'client_id': self.client_id,
            'limit': '20', 'offset': '0', 'linked_partitioning': '1', 'app_version': '1769771069', 'app_locale': 'en',
        }
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://api-v2.soundcloud.com/search/tracks?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['limit'] = page_size
            page_rule['offset'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        guess_codec_func = lambda t: ((lambda preset, mime: "opus" if ("opus" in preset or "opus" in mime) else "aac" if ("aac" in preset or "mp4a" in mime or "audio/mp4" in mime or "m4a" in mime) else "mp3" if ("mp3" in preset or "audio/mpeg" in mime) else "abr" if ("abr" in preset) else "unknown")(
            (safeextractfromdict(t, ["preset"], "") or "").lower(), (safeextractfromdict(t, ["format", "mime_type"], "") or "").lower()
        ))
        guess_bitrate_kbps_func = lambda t: (lambda preset: (lambda m: int(m.group(1)) if m else 128 if preset == "mp3_0_1" else 64 if preset == "opus_0_0" else 128 if preset.startswith("abr") else 0)(re.search(r"(\d+)\s*k", preset)))(
            (safeextractfromdict(t, ["preset"], "") or "").lower()
        )
        quality_rank_func = lambda t: {"hq": 2, "sq": 1}.get((safeextractfromdict(t, ["quality"], "") or "").lower(), 0)
        codec_rank_func = lambda codec: {"opus": 4, "aac": 3, "abr": 2, "mp3": 1, "unknown": 0}.get((codec or "").lower(), 0)
        protocol_rank_func = lambda t: {"progressive": 2, "hls": 1}.get((safeextractfromdict(t, ["format", "protocol"], "") or "").lower(), 0)
        sort_key_func = lambda t: (lambda c, br: (quality_rank_func(t), br, codec_rank_func(c), protocol_rank_func(t)))(guess_codec_func(t), guess_bitrate_kbps_func(t))
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['collection']
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('id' not in search_result): continue
                for transcoding in sorted((safeextractfromdict(search_result, ['media', 'transcodings'], []) or []), key=sort_key_func, reverse=True):
                    if not isinstance(transcoding, dict): continue
                    preset, mime_type = transcoding.get('preset', '') or '', safeextractfromdict(transcoding, ['format', 'mime_type'], None) or ''
                    download_url, protocol = transcoding.get('url'), safeextractfromdict(transcoding, ['format', 'protocol'], None)
                    if str(protocol).startswith(('ctr-', 'cbc-')): continue # TODO: Solve DRM issues in SoundCloud
                    ext = (('opus' if ('opus' in preset or 'opus' in mime_type) else None) or ('m4a' if ('aac' in preset or 'm4a' in mime_type) else None) or 'mp3')
                    if f"{protocol}_{preset}" in {"original_download"}:
                        try: resp = self.get(f'https://api-v2.soundcloud.com/tracks/{search_result["id"]}/download', params={'client_id': self.client_id}, **request_overrides); resp.raise_for_status()
                        except Exception: continue
                        download_result = resp2json(resp=resp)
                        download_url = download_result.get('redirectUri')
                        if not download_url or not str(download_url).startswith('http'): continue
                    else:
                        try: resp = self.get(download_url, params={'client_id': self.client_id}, **request_overrides); resp.raise_for_status()
                        except Exception: continue
                        download_result = resp2json(resp=resp)
                        download_url = download_result.get('url')
                        if not download_url or not str(download_url).startswith('http'): continue
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['title'], None)),
                        singers=legalizestring(safeextractfromdict(search_result, ['publisher_metadata', 'artist'], None) or safeextractfromdict(search_result, ['user', 'username'], None)),
                        album=legalizestring(safeextractfromdict(search_result, ['publisher_metadata', 'album_title'], None)), ext=ext, file_size='NULL', identifier=search_result['id'],
                        duration_s=safeextractfromdict(search_result, ['duration'], 0), duration=seconds2hms(safeextractfromdict(search_result, ['duration'], 0)), lyric='NULL',
                        cover_url=search_result.get('artwork_url'), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                    )
                    if not song_info.with_valid_download_url: continue
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: continue
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