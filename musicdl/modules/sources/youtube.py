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
import base64
import random
from typing import Any
from ytmusicapi import YTMusic
from contextlib import suppress
from .base import BaseMusicClient
from rich.progress import Progress
from pathvalidate import sanitize_filepath
from ..utils.youtubeutils import YouTube, Stream as YouTubeStreamObj, REPAIDAPI_KEYS
from ..utils import legalizestring, resp2json, usesearchheaderscookies, usedownloadheaderscookies, safeextractfromdict, SongInfo, SongInfoUtils, AudioLinkTester, LyricSearchClient, IOUtils


'''YouTubeMusicClient'''
class YouTubeMusicClient(BaseMusicClient):
    source = 'YouTubeMusicClient'
    def __init__(self, **kwargs):
        super(YouTubeMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"}
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0, auto_supplement_song: bool = True):
        # fallback to general music download method
        if isinstance(song_info.download_url, str): return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id, auto_supplement_song=auto_supplement_song)
        # deal with youtube stream object
        song_info, request_overrides = copy.deepcopy(song_info), copy.deepcopy(request_overrides or {}); assert isinstance(song_info.download_url, YouTubeStreamObj)
        song_info._save_path = sanitize_filepath(song_info.save_path); song_info.work_dir = os.path.dirname(song_info.save_path); IOUtils.touchdir(song_info.work_dir)
        try:
            total_size, chunk_size, downloaded_size = int(song_info.download_url.filesize), song_info.chunk_size, 0
            progress.update(song_progress_id, total=total_size if total_size > 0 else None)
            with open(song_info.save_path, "wb") as fp:
                for chunk in song_info.download_url.iterchunks(chunk_size=chunk_size):
                    if chunk: fp.write(chunk); downloaded_size += len(chunk)
                    downloading_text = "%0.2fMB/%0.2fMB" % (downloaded_size / 1024 / 1024, total_size / 1024 / 1024) if total_size > 0 else "%0.2fMB/%0.2fMB" % (downloaded_size / 1024 / 1024, downloaded_size / 1024 / 1024)
                    (total_size == 0) and progress.update(song_progress_id, total=downloaded_size); progress.advance(song_progress_id, len(chunk))
                    progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Downloading: {downloading_text})")
            progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Success)")
            downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(song_info, logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else song_info)
        except Exception as err:
            progress.update(song_progress_id, description=f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})")
            self.logger_handle.error(f"{self.source}._download >>> {song_info.song_name[:15] + '...' if len(song_info.song_name) > 18 else song_info.song_name[:18]} (Error: {err})", disable_print=self.disable_print)
        # return
        return downloaded_song_infos
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, decrypt_func = rule or {}, request_overrides or {}, lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        ytmusic_search_api = YTMusic(auth=rule.get('auth'), user=rule.get('user'), requests_session=None, proxies=request_overrides.get('proxies') or self._autosetproxies(), language=rule.get('language', 'en'), location=rule.get('location', ''), oauth_credentials=rule.get('oauth_credentials')).search
        rapidapi_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36", "X-Rapidapi-Host": "youtube-music-api3.p.rapidapi.com", "X-Rapidapi-Key": decrypt_func(random.choice(REPAIDAPI_KEYS)), "Referer": "https://music-download-lake.vercel.app/", "Origin": "https://music-download-lake.vercel.app", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"}
        # construct search urls
        self.search_size_per_page = self.search_size_per_source
        ytmusic_search_rule = {'query': keyword, 'filter': rule.get('filter'), 'scope': rule.get('scope'), 'limit': self.search_size_per_source, 'ignore_spelling': rule.get('ignore_spelling', False)}
        rapidapi_search_rule = {'headers': rapidapi_headers, 'params': {'q': keyword, 'type': 'song', 'limit': self.search_size_per_source}, 'url': 'https://youtube-music-api3.p.rapidapi.com/search'}
        search_urls = [{'candidate_apis': [{'api': self.get, 'inputs': rapidapi_search_rule, 'method': 'rapidapi'}, {'api': ytmusic_search_api, 'inputs': ytmusic_search_rule, 'method': 'ytmusicapi'}]}]
        # return
        return search_urls
    '''_parsewithyt1s'''
    def _parsewithyt1s(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info, MUSIC_QUALITIES = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source), ['320', '256', '128', '96'][:2]
        transform_search_duration_func = lambda d: "{:02}:{:02}:{:02}".format(*([0] * (3 - len(str(d).split(":"))) + list(map(int, str(d).split(":")))))
        headers = {
            "accept": "*/*", "referer": f"https://embed.dlsrv.online/v1/full?videoId={song_id}", "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "empty", 
            "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "sec-fetch-storage-access": "active", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
        }
        (token_resp := self.get('https://embed.dlsrv.online/api/session-token', headers=headers, **request_overrides)).raise_for_status()
        # parse
        for music_quality in MUSIC_QUALITIES:
            with suppress(Exception): resp = None; (resp := self.post('https://embed.dlsrv.online/api/download/audio227', json={"videoId": song_id, "format": "mp3", "quality": music_quality}, headers={**headers, "X-Session-Token": resp2json(resp=token_resp)['token']}, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := (download_result := resp2json(resp=resp)).get('url')) or not str(download_url).startswith('http'): continue
            with suppress(Exception): resp = None; (resp := self.get(download_url, allow_redirects=True, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            if download_url_status['file_size_bytes'] == 0: download_url_status['file_size_bytes'], download_url_status['file_size'] = resp.content.__sizeof__(), SongInfoUtils.byte2mb(resp.content.__sizeof__())
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=song_id, duration_s=int(float(search_result.get('duration_seconds', 0) or 0)), duration=transform_search_duration_func(search_result.get('duration', '0:00') or '0:00'), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=self.default_download_headers,
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithclipto'''
    def _parsewithclipto(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source)
        transform_search_duration_func = lambda d: "{:02}:{:02}:{:02}".format(*([0] * (3 - len(str(d).split(":"))) + list(map(int, str(d).split(":")))))
        # parse
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36", "content-type": "application/json", "origin": "https://www.clipto.com", "referer": "https://www.clipto.com/media-downloader/"}
        (resp := self.post('https://www.clipto.com/api/youtube', json={"url": f"https://www.youtube.com/watch?v={song_id}"}, headers=headers, **request_overrides)).raise_for_status()
        medias: list[dict[str, Any]] = (download_result := resp2json(resp=resp))['medias']
        medias = [dr for dr in medias if isinstance(dr, dict) and (dr.get('type') in ('audio',) or 'audio' in dr.get('mimeType'))]
        for media in sorted(medias, key=lambda x: int(float(x.get('contentLength', 0) or 0)), reverse=True):
            if not (download_url := media.get('url')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(download_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(download_result.get('duration') or 0))), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers,
            )
            song_info.ext = 'm4a' if song_info.ext in {'mp4', 'm4a', 'weba'} else song_info.ext
            if not song_info.duration or song_info.duration == '-:-:-': transform_search_duration_func(search_result.get('duration', '0:00') or '0:00')
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithmp3youtube'''
    def _parsewithmp3youtube(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info, MUSIC_QUALITIES = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source), ['320', '256', '128', '96'][:2]
        transform_search_duration_func = lambda d: "{:02}:{:02}:{:02}".format(*([0] * (3 - len(str(d).split(":"))) + list(map(int, str(d).split(":")))))
        mp3youtube_request_key = resp2json(resp=self.get('https://api.mp3youtube.cc/v2/sanity/key', headers={"Content-Type": "application/json", "Origin": "https://iframe.y2meta-uk.com", "Accept": "*/*"}, timeout=10, **request_overrides))['key']
        # parse
        for music_quality in MUSIC_QUALITIES:
            audio_payload = {"link": f"https://youtu.be/{song_id}", "format": "mp3", "audioBitrate": music_quality, "videoQuality": "720", "vCodec": "h264"}
            with suppress(Exception): resp = None; (resp := self.post('https://api.mp3youtube.cc/v2/converter', json=audio_payload, headers={"Content-Type": "application/json", "Origin": "https://iframe.y2meta-uk.com", "Accept": "*/*", "key": mp3youtube_request_key}, timeout=10, **request_overrides)).raise_for_status()
            if not (download_url := (download_result := resp2json(resp=resp)).get('url')) or not str(download_url).startswith('http'): continue
            with suppress(Exception): resp = None; (resp := self.get(download_url, allow_redirects=True, **request_overrides)).raise_for_status()
            if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            if download_url_status['file_size_bytes'] == 0: download_url_status['file_size_bytes'], download_url_status['file_size'] = resp.content.__sizeof__(), SongInfoUtils.byte2mb(resp.content.__sizeof__())
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=song_id, duration_s=int(float(search_result.get('duration_seconds', 0) or 0)), duration=transform_search_duration_func(search_result.get('duration', '0:00') or '0:00'), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, downloaded_contents=resp.content, default_download_headers=self.default_download_headers,
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithnoteai'''
    def _parsewithnoteai(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source)
        transform_search_duration_func = lambda d: "{:02}:{:02}:{:02}".format(*([0] * (3 - len(str(d).split(":"))) + list(map(int, str(d).split(":")))))
        # parse
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36", "content-type": "application/json", "origin": "https://www.noteai.io", "referer": "https://www.noteai.io/youtube-audio-downloader"}
        (resp := self.post('https://www.noteai.io/api/tools/youtube/info', json={"video": f"https://www.youtube.com/watch?v={song_id}"}, headers=headers, **request_overrides)).raise_for_status()
        medias: list[dict[str, Any]] = (download_result := resp2json(resp=resp))['audio_formats']
        for media in sorted(medias, key=lambda x: int(float(x.get('filesize', 0) or 0)), reverse=True):
            if not (download_url := media.get('url')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(download_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(download_result.get('duration') or 0))), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers,
            )
            song_info.ext = 'm4a' if song_info.ext in {'mp4', 'm4a', 'weba'} else song_info.ext
            if not song_info.duration or song_info.duration == '-:-:-': transform_search_duration_func(search_result.get('duration', '0:00') or '0:00')
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewithacethinker'''
    def _parsewithacethinker(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source)
        transform_search_duration_func = lambda d: "{:02}:{:02}:{:02}".format(*([0] * (3 - len(str(d).split(":"))) + list(map(int, str(d).split(":")))))
        (resp := self.get('https://www.acethinker.ai/downloader/api/get_csrf_token.php', **request_overrides)).raise_for_status()
        # parse
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36", "accept": "application/json, text/plain, */*", "referer": "https://www.acethinker.ai/freemp3finder", "x-csrf-token": resp2json(resp=resp)['token']}
        (resp := self.get(f'https://www.acethinker.ai/downloader/api/dlapinewv2.php?url=https://www.youtube.com/watch?v={song_id}', headers=headers, **request_overrides)).raise_for_status()
        medias: list[dict[str, Any]] = (download_result := resp2json(resp=resp)['res_data'])['formats']
        medias = [a for a in medias if isinstance(a, dict) and str(a.get('vcodec')).lower() in {"", "none"}]
        for media in sorted(medias, key=lambda x: int(float(x.get('filesize', 0) or 0)), reverse=True):
            if not (download_url := media.get('url')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(download_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(download_result.get('duration') or 0))), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers,
            )
            song_info.ext = 'm4a' if song_info.ext in {'mp4', 'm4a', 'weba'} else song_info.ext
            if not song_info.duration or song_info.duration == '-:-:-': transform_search_duration_func(search_result.get('duration', '0:00') or '0:00')
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
            with suppress(Exception): (resp := self.get(f'https://www.acethinker.ai/downloader/api/newytdlapi/youtube_mp3_audio_video_downloader.php?url=https://www.youtube.com/watch?v={song_id}', headers=headers, **request_overrides)).raise_for_status()
            if not (download_url := resp2json(resp=resp).get('download_url')) or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                file_size=download_url_status['file_size'], identifier=song_id, duration_s=int(float(download_result.get('duration') or 0)), duration=SongInfoUtils.seconds2hms(int(float(download_result.get('duration') or 0))), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers,
            )
            song_info.ext = 'm4a' if song_info.ext in {'mp4', 'm4a', 'weba'} else song_info.ext
            if not song_info.duration or song_info.duration == '-:-:-': transform_search_duration_func(search_result.get('duration', '0:00') or '0:00')
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for parser_func in [self._parsewithyt1s, self._parsewithmp3youtube, self._parsewithacethinker, self._parsewithnoteai, self._parsewithclipto]:
            song_info_flac = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
            with suppress(Exception): song_info_flac = parser_func(search_result, request_overrides)
            if song_info_flac.with_valid_download_url and song_info_flac.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        return song_info_flac
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('videoId'))): return song_info
        codec_to_ext_func = lambda c: next((str(ext).removeprefix('.') for k, ext in {"mp4a": ".m4a", "flac": ".flac", "opus": ".opus", "vorbis": ".ogg", "mp3": ".mp3", "aac": ".aac", "alac": ".m4a", "pcm": ".wav", "wav": ".wav"}.items() if str((c[0] if isinstance(c, (list, tuple)) else c)).lower().startswith(k)), None)
        # parse download url based on arguments
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            download_url: YouTubeStreamObj = (cli := YouTube(video_id=search_result['videoId'])).streams.getaudioonly()
            duration_in_secs = (float(download_url.durationMs) / 1000) or search_result.get('duration_seconds') or 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': cli.vid_info, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(search_result.get('album')), ext=codec_to_ext_func(download_url.audio_codec), 
                file_size_bytes=download_url.filesize, file_size=SongInfoUtils.byte2mb(download_url.filesize), identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url, download_url_status={'ok': True}, 
            )
        # compare and select the best
        song_info = song_info_flac if song_info_flac.with_valid_download_url and (not song_info.with_valid_download_url or song_info_flac.largerthan(song_info)) else song_info
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # supplement lyric results
        lyric_result, lyric = LyricSearchClient().search(artist_name=song_info.singers, track_name=song_info.song_name, request_overrides=request_overrides)
        song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
        song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
        # return
        return song_info
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = {}, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, candidate_apis = request_overrides or {}, copy.deepcopy(search_url)['candidate_apis']
        # successful
        try:
            # --search results
            ytmusicapi_candidate_api: dict = [c for c in candidate_apis if c['method'] in {'ytmusicapi'}][0]; rapidapi_candidate_api: dict = [c for c in candidate_apis if c['method'] in {'rapidapi'}][0]
            with suppress(Exception): search_results = None; resp = ytmusicapi_candidate_api['api'](**ytmusicapi_candidate_api['inputs']); search_results = [s for s in resp if s['resultType'] == 'song']
            if not search_results: resp = rapidapi_candidate_api['api'](**rapidapi_candidate_api['inputs']); search_results = resp2json(resp=resp)['result']
            for search_result in (search_results or list()):
                # --init song info
                song_info = SongInfo(source=self.source, raw_data={'search': search_result, 'download': {}, 'lyric': {}})
                # --parse with third part apis
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
                # --parse with official apis
                with suppress(Exception): song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=song_info_flac, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                # --append to song_infos
                if (song_info := song_info if song_info.with_valid_download_url else song_info_flac).with_valid_download_url: song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
            # --update progress
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Success)")
        # failure
        except Exception as err:
            progress.update(progress_id, description=f"{self.source}._search >>> {search_url} (Error: {err})")
            self.logger_handle.error(f"{self.source}._search >>> {search_url} (Error: {err})", disable_print=self.disable_print)
        # return
        return song_infos