'''
Function:
    Implementation of SodaMusicClient: https://www.douyin.com/qishui/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import os
import copy
import json_repair
from pathlib import Path
from .base import BaseMusicClient
from urllib.parse import urlencode
from rich.progress import Progress
from ..utils.sodautils import AudioDecryptor
from ..utils import legalizestring, byte2mb, resp2json, usesearchheaderscookies, safeextractfromdict, seconds2hms, usedownloadheaderscookies, cleanlrc, SongInfo, SodaTimedLyricsParser


'''SodaMusicClient'''
class SodaMusicClient(BaseMusicClient):
    source = 'SodaMusicClient'
    def __init__(self, **kwargs):
        super(SodaMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_download'''
    @usedownloadheaderscookies
    def _download(self, song_info: SongInfo, request_overrides: dict = None, downloaded_song_infos: list = [], progress: Progress = None, song_progress_id: int = 0):
        downloaded_song_infos = super()._download(song_info=song_info, request_overrides=request_overrides, downloaded_song_infos=downloaded_song_infos, progress=progress, song_progress_id=song_progress_id)
        with open(song_info.save_path, "rb") as fp: file_data = bytearray(fp.read())
        output_filepath = Path(song_info.save_path)
        output_filepath = output_filepath.parent / f'{output_filepath.stem}.m4a'
        AudioDecryptor.decrypt(file_data=file_data, play_auth=song_info.raw_data['play_auth'], output_filepath=str(output_filepath))
        if not os.path.samefile(song_info.save_path, str(output_filepath)): os.remove(song_info.save_path)
        return downloaded_song_infos
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        self.search_size_per_page = min(self.search_size_per_page, 20)
        # search rules
        default_rule = {
            'aid': '386088', 'app_name': '', 'region': '', 'geo_region': '', 'os_region': '', 'sim_region': '', 'device_id': '', 'cdid': '', 'iid': '', 'version_name': '',
            'version_code': '', 'channel': '', 'build_mode': '', 'network_carrier': '', 'ac': '', 'tz_name': '', 'resolution': '', 'device_platform': '', 'device_type': '',
            'os_version': '', 'fp': '', 'q': keyword, 'cursor': 0, 'search_id': '', 'search_method': 'input', 'debug_params': '', 'from_search_id': '', 'search_scene': '',
        }
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://api.qishui.com/luna/pc/search/track?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['cursor'] = count
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: str = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides = request_overrides or {}
        rank_audio_func = lambda video_list: sorted(video_list, key=lambda x: (x.get('Size'), x.get('Bitrate')), reverse=True)
        # successful
        try:
            # --search results
            resp = self.get(search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['result_groups'][0]['data']
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or not safeextractfromdict(search_result, ['entity', 'track', 'id'], None): continue
                song_info, song_id = SongInfo(source=self.source), search_result['entity']['track']['id']
                try:
                    resp = self.get(f'https://api.qishui.com/luna/pc/track_v2?track_id={song_id}&media_type=track&queue_type=', **request_overrides)
                    resp.raise_for_status()
                    download_result: dict = resp2json(resp)
                    if 'track_player' not in download_result: continue
                    resp = self.get(download_result['track_player']['url_player_info'])
                    resp.raise_for_status()
                    download_result['url_player_info_response'] = resp2json(resp)
                except:
                    continue
                audios = safeextractfromdict(download_result, ['url_player_info_response', 'Result', 'Data', 'PlayInfoList'], [])
                if not audios or not isinstance(audios, list): continue
                audios_sorted: list[dict] = rank_audio_func(audios)
                audios_sorted = [a for a in audios_sorted if (a.get('MainPlayUrl') or a.get('BackupPlayUrl'))]
                if not audios_sorted: continue
                for audio_sorted in audios_sorted:
                    download_url = audio_sorted.get('MainPlayUrl') or audio_sorted.get('BackupPlayUrl')
                    play_auth = safeextractfromdict(audio_sorted, ['PlayAuth'], '')
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}, 'play_auth': play_auth}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['entity', 'track', 'name'], None)),
                        singers=legalizestring(', '.join([singer.get('name') for singer in (safeextractfromdict(search_result, ['entity', 'track', 'artists'], []) or []) if isinstance(singer, dict) and singer.get('name')])),
                        album=legalizestring(safeextractfromdict(search_result, ['entity', 'track', 'album', 'name'], None)), ext=safeextractfromdict(audio_sorted, ['Format'], 'm4a'), file_size_bytes=safeextractfromdict(audio_sorted, ['Size'], 0), 
                        file_size=byte2mb(safeextractfromdict(audio_sorted, ['Size'], 0)), identifier=song_id, duration_s=safeextractfromdict(audio_sorted, ['Duration'], 0), duration=seconds2hms(safeextractfromdict(audio_sorted, ['Duration'], 0)), 
                        lyric=cleanlrc(SodaTimedLyricsParser.tolrclinelevel(SodaTimedLyricsParser.parsetimedlyrics(safeextractfromdict(download_result, ['lyric', 'content'], "")))) or 'NULL', 
                        cover_url=str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'urls', 0], '')) + str(safeextractfromdict(search_result, ['entity', 'track', 'album', 'url_cover', 'uri'], '')) + '~c5_375x375.jpg', 
                        download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                    )
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL',)) else song_info.ext
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: continue
                # --lyric results
                try:
                    resp = self.get(f'https://music.douyin.com/qishui/share/track?track_id={song_id}', **request_overrides)
                    resp.raise_for_status()
                    lyric_result = json_repair.loads(re.search(r'_ROUTER_DATA\s*=\s*({[\s\S]*?});', resp.text).group(1).strip())
                    sentences, lrc_list = lyric_result['loaderData']['track_page']['audioWithLyricsOption']['lyrics']['sentences'], []
                    for sentence in sentences:
                        if not isinstance(sentence, dict): continue
                        start_ms = sentence.get('startMs', 0)
                        sentence_text = "".join([w.get('text', '') for w in sentence.get('words', []) if isinstance(w, dict)])
                        minutes, seconds, m_seconds = start_ms // 60000, (start_ms % 60000) // 1000, start_ms % 1000
                        time_tag = f"[{minutes:02d}:{seconds:02d}.{m_seconds:03d}]"
                        lrc_list.append(f"{time_tag}{sentence_text}")
                    lyric = cleanlrc("\n".join(lrc_list)) or 'NULL'
                except:
                    lyric_result, lyric = {}, 'NULL'
                # --update song_info
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
        return song_infos