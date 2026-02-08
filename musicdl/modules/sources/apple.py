'''
Function:
    Implementation of AppleMusicClient: https://music.apple.com/{geo}/new
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import os
import copy
import shutil
from types import SimpleNamespace
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils.appleutils import AppleMusicClientDownloadSongUtils, AppleMusicClientAPIUtils, AppleMusicClientItunesApiUtils, DownloadItem, SongCodec, RemuxMode
from ..utils import touchdir, legalizestring, resp2json, seconds2hms, usesearchheaderscookies, safeextractfromdict, usedownloadheaderscookies, cleanlrc, SongInfo, SongInfoUtils


'''AppleMusicClient'''
class AppleMusicClient(BaseMusicClient):
    source = 'AppleMusicClient'
    def __init__(self, **kwargs):
        use_wrapper, wrapper_account_url, language, codec, wrapper_decrypt_ip = kwargs.pop('use_wrapper', False), kwargs.pop('wrapper_account_url', "http://127.0.0.1:30020/"), kwargs.pop('language', "en-US"), kwargs.pop('codec', None), kwargs.pop('wrapper_decrypt_ip', "127.0.0.1:10020")
        super(AppleMusicClient, self).__init__(**kwargs)
        if (not self.default_cookies or 'media-user-token' not in self.default_cookies) and (not use_wrapper): self.logger_handle.warning(f'{self.source}.__init__ >>> both "media-user-token" and "use_wrapper" are not configured, so song downloads are restricted and only the preview portion of the track can be downloaded.')
        self.apple_music_api, self.itunes_api, self.use_wrapper, self.wrapper_account_url, self.language, self.account_info, self.codec, self.wrapper_decrypt_ip = None, None, use_wrapper, wrapper_account_url, language, {}, codec, wrapper_decrypt_ip
        if self.codec is None and use_wrapper: self.codec = SongCodec.ALAC
        if self.codec is None and (not use_wrapper) and (self.default_cookies and 'media-user-token' in self.default_cookies): self.codec = SongCodec.AAC_LEGACY
        self.default_search_headers = {
            "accept": "*/*", "accept-language": "en-US", "origin": "https://music.apple.com", "priority": "u=1, i", "referer": "https://music.apple.com", "sec-fetch-site": "same-site",
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"', "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"', "sec-fetch-mode": "cors", 
            "sec-fetch-dest": "empty", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0):
        if isinstance(song_info.download_url, str): return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id)
        request_overrides = request_overrides or {}
        try:
            touchdir(song_info.work_dir)
            tmp_dir = f'apple_id_{str(song_info.identifier)}'
            touchdir(tmp_dir)
            download_item: DownloadItem = song_info.download_url
            progress.update(song_progress_id, total=1, kind='overall')
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Downloading)")
            AppleMusicClientDownloadSongUtils.download(download_item=download_item, work_dir=tmp_dir, silent=self.disable_print, codec=self.codec, wrapper_decrypt_ip=self.wrapper_decrypt_ip, artist=song_info.singers, use_wrapper=self.use_wrapper, remux_mode=RemuxMode.FFMPEG)
            shutil.move(download_item.staged_path, song_info.save_path)
            progress.update(song_progress_id, total=os.path.getsize(song_info.save_path), kind='download')
            progress.advance(song_progress_id, os.path.getsize(song_info.save_path))
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name} (Success)")
            downloaded_song_infos.append(SongInfoUtils.fillsongtechinfo(copy.deepcopy(song_info), logger_handle=self.logger_handle, disable_print=self.disable_print))
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception as err:
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name} (Error: {err})")
        return downloaded_song_infos
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # init apple_music_api
        if self.use_wrapper and (not self.apple_music_api): self.apple_music_api = AppleMusicClientAPIUtils.createfromwrapper(wrapper_account_url=self.wrapper_account_url, request_overrides=request_overrides, language=self.language)
        elif self.default_cookies and ('media-user-token' in self.default_cookies) and (not self.apple_music_api): self.apple_music_api = AppleMusicClientAPIUtils.createfromnetscapecookies(cookies=self.default_cookies, request_overrides=request_overrides, language=self.language)
        # init itunes_api
        if self.apple_music_api and (not self.itunes_api): self.itunes_api = AppleMusicClientItunesApiUtils(storefront=self.apple_music_api.storefront, language=self.apple_music_api.language)
        # init default_search_headers
        if self.apple_music_api and ('authorization' not in self.default_headers):
            self.default_search_headers = copy.deepcopy(self.apple_music_api.client.headers)
            self.default_headers = self.default_search_headers
            self._initsession()
            self.account_info = self.apple_music_api.account_info
        elif ('authorization' not in self.default_headers):
            virtual_client = SimpleNamespace(client=self.session, language=self.language)
            self.default_search_headers.update({"authorization": f"Bearer {AppleMusicClientAPIUtils.gettoken(virtual_client, request_overrides=request_overrides)}"})
            self.default_headers = self.default_search_headers
            self._initsession()
        # search rules
        default_rule = {
            "groups": "song", "l": "en-US", "offset": "0", "term": keyword, "types": "activities,albums,apple-curators,artists,curators,editorial-items,music-movies,music-videos,playlists,record-labels,songs,stations,tv-episodes,uploaded-videos",
            "art[url]": "f", "extend": "artistUrl", "fields[albums]": "artistName,artistUrl,artwork,contentRating,editorialArtwork,editorialNotes,name,playParams,releaseDate,url,trackCount", "fields[artists]": "url,name,artwork",
            "format[resources]": "map", "include[editorial-items]": "contents", "include[songs]": "artists", "limit": "10", "omit[resource]": "autos", "platform": "web", "relate[albums]": "artists", "relate[editorial-items]": "contents",
            "relate[songs]": "albums", "types": "activities,albums,apple-curators,artists,curators,music-movies,music-videos,playlists,songs,stations,tv-episodes,uploaded-videos", "with": "lyrics,serverBubbles", 
        }
        default_rule.update(rule)
        geo = safeextractfromdict(self.account_info, ['meta', 'subscription', 'storefront'], 'us')
        # construct search urls based on search rules
        base_url = f'https://amp-api-edge.music.apple.com/v1/catalog/{geo}/search?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['limit'] = page_size
            page_rule['offset'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_parsewithnonvipofficialapi'''
    def _parsewithnonvipofficialapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info = request_overrides or {}, SongInfo(source=self.source)
        # parse
        download_url: str = safeextractfromdict(search_result, ['attributes', 'previews', 0, 'url'], '')
        if not download_url or not download_url.startswith('http'): return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['attributes', 'name'], None)),
            singers=legalizestring(safeextractfromdict(search_result, ['attributes', 'artistName'], None)), album=legalizestring(safeextractfromdict(search_result, ['attributes', 'albumName'], None)),
            ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=search_result['id'], duration_s=float(safeextractfromdict(search_result, ['attributes', 'durationInMillis'], 0)) / 1000,
            duration=seconds2hms(float(safeextractfromdict(search_result, ['attributes', 'durationInMillis'], 0)) / 1000), lyric=None, cover_url=safeextractfromdict(search_result, ['attributes', 'artwork', 'url'], ""),
            download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
        )
        if not song_info.with_valid_download_url: return song_info
        if song_info.cover_url and song_info.cover_url.startswith('http'): song_info.cover_url = song_info.cover_url.format(w=600, h=600, f='jpg')
        song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
        song_info.file_size = song_info.download_url_status['probe_status']['file_size']
        song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL',)) else song_info.ext
        # return
        return song_info
    '''_parsewithvipofficialapi'''
    def _parsewithvipofficialapi(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, codec = request_overrides or {}, SongInfo(source=self.source), self.codec
        # parse
        geo = safeextractfromdict(self.account_info, ['meta', 'subscription', 'storefront'], 'us')
        params = {"extend": "extendedAssetUrls", "include": "lyrics,albums"}
        resp = self.get(f'https://amp-api.music.apple.com/v1/catalog/{geo}/songs/{search_result["id"]}', params=params, **request_overrides)
        resp.raise_for_status()
        download_result = resp2json(resp=resp)
        download_item: DownloadItem = AppleMusicClientDownloadSongUtils.getdownloaditem(
            song_metadata=download_result['data'][0], playlist_metadata=None, codec=codec, apple_music_api=self.apple_music_api, itunes_api=self.itunes_api, request_overrides=request_overrides, use_wrapper=self.use_wrapper
        )
        try: resp = self.get(download_item.stream_info.audio_track.stream_url, **request_overrides); resp.raise_for_status()
        except Exception: return song_info
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['attributes', 'name'], None)),
            singers=legalizestring(safeextractfromdict(search_result, ['attributes', 'artistName'], None)), album=legalizestring(safeextractfromdict(search_result, ['attributes', 'albumName'], None)),
            ext=download_item.stream_info.file_format.value, file_size='HLS', identifier=search_result['id'], duration_s=float(safeextractfromdict(search_result, ['attributes', 'durationInMillis'], 0)) / 1000,
            duration=seconds2hms(int(float(safeextractfromdict(search_result, ['attributes', 'durationInMillis'], 0)) / 1000)), lyric=cleanlrc(str(download_item.lyrics.synced)) or 'NULL', 
            cover_url=safeextractfromdict(search_result, ['attributes', 'artwork', 'url'], ""), download_url=download_item, download_url_status={'ok': True},
        )
        if not song_info.with_valid_download_url: return song_info
        if song_info.cover_url and song_info.cover_url.startswith('http'): song_info.cover_url = song_info.cover_url.format(w=600, h=600, f='jpg')
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
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results: dict = resp2json(resp)['resources']['songs']
            for song_key, search_result in search_results.items():
                # --download results
                if not isinstance(search_result, dict) or ('id' not in search_result) or (search_result.get('type') not in {'songs'}): continue
                search_result['song_key'], song_info = song_key, SongInfo(source=self.source)
                # ----non-vip users
                if (not self.default_cookies or 'media-user-token' not in self.default_cookies) and (not self.use_wrapper):
                    try: song_info = self._parsewithnonvipofficialapi(search_result=search_result, request_overrides=request_overrides)
                    except Exception: continue
                # ----vip users
                else:
                    try: song_info = self._parsewithvipofficialapi(search_result=search_result, request_overrides=request_overrides)
                    except Exception: continue
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