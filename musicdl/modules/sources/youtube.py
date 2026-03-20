'''
Function:
    Implementation of YouTubeMusicClient: https://music.youtube.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
import base64
import random
from ytmusicapi import YTMusic
from .base import BaseMusicClient
from rich.progress import Progress
from ..utils.youtubeutils import YouTube, REPAIDAPI_KEYS
from ..utils import legalizestring, resp2json, usesearchheaderscookies, byte2mb, seconds2hms, usedownloadheaderscookies, touchdir, safeextractfromdict, SongInfo, SongInfoUtils, AudioLinkTester, LyricSearchClient


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
        if isinstance(song_info.download_url, str): return super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id, auto_supplement_song=auto_supplement_song)
        request_overrides = request_overrides or {}
        try:
            touchdir(song_info.work_dir)
            total_size, chunk_size, downloaded_size = int(song_info.download_url.filesize), song_info.get('chunk_size', 1024 * 1024), 0
            progress.update(song_progress_id, total=total_size)
            with open(song_info.save_path, "wb") as fp:
                for chunk in song_info.download_url.iterchunks(chunk_size=chunk_size):
                    if not chunk: continue
                    fp.write(chunk); downloaded_size = downloaded_size + len(chunk)
                    if total_size > 0: downloading_text = "%0.2fMB/%0.2fMB" % (downloaded_size / 1024 / 1024, total_size / 1024 / 1024)
                    else: progress.update(song_progress_id, total=downloaded_size); downloading_text = "%0.2fMB/%0.2fMB" % (downloaded_size / 1024 / 1024, downloaded_size / 1024 / 1024)
                    progress.advance(song_progress_id, len(chunk))
                    progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Downloading: {downloading_text})")
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Success)")
            downloaded_song_infos.append(SongInfoUtils.supplsonginfothensavelyricsthenwritetags(copy.deepcopy(song_info), logger_handle=self.logger_handle, disable_print=self.disable_print) if auto_supplement_song else copy.deepcopy(song_info))
        except Exception as err:
            progress.update(song_progress_id, description=f"{self.source}.download >>> {song_info.song_name[:10] + '...' if len(song_info.song_name) > 13 else song_info.song_name[:13]} (Error: {err})")
        return downloaded_song_infos
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        decrypt_func = lambda t: base64.b64decode(str(t).encode('utf-8')).decode('utf-8')
        # adapt ytmusicapi to conduct music file search
        ytmusic_search_api = YTMusic(auth=rule.get('auth', None), user=rule.get('user', None), requests_session=None, proxies=request_overrides.get('proxies', None) or self._autosetproxies(), language=rule.get('language', 'en'), location=rule.get('location', ''), oauth_credentials=rule.get('oauth_credentials', '')).search
        ytmusic_search_rule = {'query': keyword, 'filter': rule.get('filter', None), 'scope': rule.get('scope', None), 'limit': self.search_size_per_source, 'ignore_spelling': rule.get('ignore_spelling', False)}
        # adapt rapidapi to conduct music file search
        rapidapi_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36", "X-Rapidapi-Host": "youtube-music-api3.p.rapidapi.com", "X-Rapidapi-Key": decrypt_func(random.choice(REPAIDAPI_KEYS)),
            "Referer": "https://music-download-lake.vercel.app/", "Origin": "https://music-download-lake.vercel.app", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        rapidapi_params = {'q': keyword, 'type': 'song', 'limit': self.search_size_per_source}
        rapidapi_search_rule = {'headers': rapidapi_headers, 'params': rapidapi_params, 'url': 'https://youtube-music-api3.p.rapidapi.com/search'}
        # construct search urls
        search_urls = [{'candidate_apis': [{'api': self.get, 'inputs': rapidapi_search_rule, 'method': 'rapidapi'}, {'api': ytmusic_search_api, 'inputs': ytmusic_search_rule, 'method': 'ytmusicapi'}]}]
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsewithyt1s'''
    def _parsewithyt1s(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info, MUSIC_QUALITIES = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source), ['320', '256', '128', '96'][:2]
        transform_search_duration_func = lambda d: "{:02}:{:02}:{:02}".format(*([0] * (3 - len(str(d).split(":"))) + list(map(int, str(d).split(":")))))
        # parse
        for quality in MUSIC_QUALITIES:
            try: (resp := self.post('https://embed.dlsrv.online/api/download/mp3', json={"videoId": song_id, "format": "mp3", "quality": quality}, headers={"Content-Type": "application/json", "Origin": "https://embed.dlsrv.online", "Accept": "*/*"}, timeout=10, **request_overrides)).raise_for_status()
            except Exception: continue
            download_url: str = (download_result := resp2json(resp=resp)).get('url')
            if not download_url or not str(download_url).startswith('http'): continue
            try: (resp := self.get(download_url, allow_redirects=True, **request_overrides)).raise_for_status()
            except Exception: continue
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(search_result.get('album')), 
                ext='mp3', file_size_bytes=resp.content.__sizeof__(), file_size=byte2mb(resp.content.__sizeof__()), identifier=song_id, duration_s=search_result.get('duration_seconds', 0) or 0, duration=transform_search_duration_func(search_result.get('duration', '0:00') or '0:00'), lyric='NULL', cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), 
                download_url=download_url, download_url_status={'ok': True}, downloaded_contents=resp.content, default_download_headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"},
            )
            if song_info.file_size_bytes < 100: song_info.download_url_status = {'ok': False}
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsewithmp3youtube'''
    def _parsvidewithmp3youtube(self, search_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_id, song_info, MUSIC_QUALITIES = request_overrides or {}, search_result['videoId'], SongInfo(source=self.source), ['320', '256', '128', '96'][:2]
        transform_search_duration_func = lambda d: "{:02}:{:02}:{:02}".format(*([0] * (3 - len(str(d).split(":"))) + list(map(int, str(d).split(":")))))
        (resp := self.get('https://api.mp3youtube.cc/v2/sanity/key', headers={"Content-Type": "application/json", "Origin": "https://iframe.y2meta-uk.com", "Accept": "*/*"}, timeout=10, **request_overrides)).raise_for_status()
        mp3youtube_request_key = resp2json(resp)['key']
        # parse
        for quality in MUSIC_QUALITIES:
            audio_payload = {"link": f"https://youtu.be/{song_id}", "format": "mp3", "audioBitrate": quality, "videoQuality": "720", "vCodec": "h264"}
            try: (resp := self.post('https://api.mp3youtube.cc/v2/converter', json=audio_payload, headers={"Content-Type": "application/json", "Origin": "https://iframe.y2meta-uk.com", "Accept": "*/*", "key": mp3youtube_request_key}, timeout=10, **request_overrides)).raise_for_status()
            except Exception: continue
            download_url: str = (download_result := resp2json(resp=resp)).get('url')
            if not download_url or not str(download_url).startswith('http'): continue
            try: (resp := self.get(download_url, allow_redirects=True, **request_overrides)).raise_for_status()
            except Exception: continue
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(search_result.get('album')), 
                ext='mp3', file_size_bytes=resp.content.__sizeof__(), file_size=byte2mb(resp.content.__sizeof__()), identifier=song_id, duration_s=search_result.get('duration_seconds', 0) or 0, duration=transform_search_duration_func(search_result.get('duration', '0:00') or '0:00'), lyric='NULL', cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), 
                download_url=download_url, download_url_status={'ok': True}, downloaded_contents=resp.content, default_download_headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"},
            )
            if song_info.file_size_bytes < 100: song_info.download_url_status = {'ok': False}
            if song_info.with_valid_download_url: break
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
        download_result = resp2json(resp=resp)
        medias = [dr for dr in download_result['medias'] if isinstance(dr, dict) and (dr.get('type') in ('audio',) or 'audio' in dr.get('mimeType'))]
        medias = sorted(medias, key=lambda x: int(float(x.get('contentLength', 0) or 0)), reverse=True)
        for media in medias:
            download_url: str = media.get('url')
            if not download_url or not str(download_url).startswith('http'): continue
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), 
                album=legalizestring(search_result.get('album')), ext=media.get('extension', 'm4a') or 'm4a', file_size_bytes=int(float(media.get('contentLength', 0) or 0)), file_size=byte2mb(int(float(media.get('contentLength', 0) or 0))), identifier=song_id, duration_s=download_result.get('duration'), duration=seconds2hms(download_result.get('duration')), 
                lyric='NULL', cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']; song_info.ext = song_info.download_url_status['probe_status']['ext']
            if song_info.ext in {'mp4', 'm4a', 'weba'}: song_info.ext = 'm4a'
            if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
            elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
            if not song_info.duration or song_info.duration == '-:-:-': transform_search_duration_func(search_result.get('duration', '0:00') or '0:00')
            if song_info.with_valid_download_url: break
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
        download_result: dict = resp2json(resp=resp)['res_data']
        medias = [a for a in download_result['formats'] if isinstance(a, dict) and str(a.get('vcodec')).lower() in {"", "none"}]
        medias = sorted(medias, key=lambda x: int(float(x.get('filesize', 0) or 0)), reverse=True)
        for media in medias:
            if not (download_url := media.get('url')) or not str(download_url).startswith('http'): continue
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), 
                album=legalizestring(search_result.get('album')), ext=media.get('ext', 'm4a') or 'm4a', file_size_bytes=int(float(media.get('filesize', 0) or 0)), file_size=byte2mb(int(float(media.get('filesize', 0) or 0))), identifier=song_id, duration_s=download_result.get('duration', 0) or 0, duration=seconds2hms(download_result.get('duration', 0) or 0),
                lyric='NULL', cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
            )
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']; song_info.ext = song_info.download_url_status['probe_status']['ext']
            if song_info.ext in {'mp4', 'm4a', 'weba'}: song_info.ext = 'm4a'
            if (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS) and (song_info.download_url_status['probe_status']['ext'] in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = song_info.download_url_status['probe_status']['ext']
            elif (song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS): song_info.ext = 'mp3'
            if not song_info.duration or song_info.duration == '-:-:-': transform_search_duration_func(search_result.get('duration', '0:00') or '0:00')
            if song_info.with_valid_download_url: break
            try: (resp := self.get(f'https://www.acethinker.ai/downloader/api/newytdlapi/youtube_mp3_audio_video_downloader.php?url=https://www.youtube.com/watch?v={song_id}', headers=headers, **request_overrides)).raise_for_status()
            except Exception: continue
            if not (parsed_in_no_us_area := resp2json(resp=resp)).get('download_url'): continue
            song_info.update(dict(download_url=parsed_in_no_us_area.get('download_url'), download_url_status=self.audio_link_tester.test(parsed_in_no_us_area.get('download_url'), request_overrides)))
            song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
            song_info.file_size = song_info.download_url_status['probe_status']['file_size']
            if song_info.with_valid_download_url: break
        # return
        return song_info
    '''_parsewiththirdpartapis'''
    def _parsewiththirdpartapis(self, search_result: dict, request_overrides: dict = None):
        if self.default_cookies or request_overrides.get('cookies'): return SongInfo(source=self.source)
        for imp_func in [self._parsewithyt1s, self._parsvidewithmp3youtube, self._parsewithacethinker, self._parsewithclipto]:
            try: song_info_flac = imp_func(search_result, request_overrides); assert song_info_flac.with_valid_download_url; break
            except: song_info_flac = SongInfo(source=self.source)
        return song_info_flac
    '''_parsewithofficialapiv1'''
    def _parsewithofficialapiv1(self, search_result: dict, song_info_flac: SongInfo = None, lossless_quality_is_sufficient: bool = True, lossless_quality_definitions: set | list | tuple = {'flac'}, request_overrides: dict = None) -> "SongInfo":
        # init
        song_info, request_overrides, song_info_flac = SongInfo(source=self.source), request_overrides or {}, song_info_flac or SongInfo(source=self.source)
        if (not isinstance(search_result, dict)) or (not (song_id := search_result.get('videoId'))): return song_info
        # obtain basic song_info
        if lossless_quality_is_sufficient and song_info_flac.with_valid_download_url and (song_info_flac.ext in lossless_quality_definitions): song_info = song_info_flac
        else:
            download_url = (cli := YouTube(video_id=search_result['videoId'])).streams.getaudioonly()
            duration_in_secs = (float(download_url.durationMs) / 1000) or search_result.get('duration_seconds', 0) or 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': cli.vid_info, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('author') or (', '.join([singer.get('name') for singer in (search_result.get('artists') or []) if isinstance(singer, dict) and singer.get('name')]))), album=legalizestring(search_result.get('album')), 
                ext='mp3', file_size_bytes=download_url.filesize, file_size=byte2mb(download_url.filesize), identifier=song_id, duration_s=duration_in_secs, duration=seconds2hms(duration_in_secs), lyric='NULL', cover_url=search_result.get('thumbnail') or safeextractfromdict(search_result, ['thumbnails', -1, 'url'], None), download_url=download_url, download_url_status={'ok': True}, 
            )
            if song_info.file_size_bytes < 100: song_info.download_url_status = {'ok': False}
        # compare and select the best
        song_info = song_info_flac if song_info_flac.with_valid_download_url and (not song_info.with_valid_download_url or song_info_flac.largerthan(song_info)) else song_info
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
        request_overrides = request_overrides or {}
        candidate_apis = copy.deepcopy(search_url)['candidate_apis']
        # successful
        try:
            # --search results
            for candidate_api in candidate_apis[1:]:
                try: resp = candidate_api['api'](**candidate_api['inputs']); candidate_api['method'] in ('rapidapi',) and resp.raise_for_status(); search_results = resp2json(resp=resp)['result'] if candidate_api['method'] in ('rapidapi',) else [s for s in resp if s['resultType'] == 'song'] if candidate_api['method'] in ('ytmusicapi',) else (_ for _ in ()).throw(ValueError(f"Unsupported method: {candidate_api['method']}")); assert len(search_results) > 0; break
                except Exception: continue
            for search_result in search_results:
                # --parse with third part apis
                song_info_flac = self._parsewiththirdpartapis(search_result=search_result, request_overrides=request_overrides)
                # --parse with official apis
                try: song_info = self._parsewithofficialapiv1(search_result=search_result, song_info_flac=song_info_flac, lossless_quality_is_sufficient=False, request_overrides=request_overrides)
                except Exception: song_info = SongInfo(source=self.source)
                # --append to song_infos
                if not song_info.with_valid_download_url: song_info = song_info_flac
                if not song_info.with_valid_download_url: continue
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