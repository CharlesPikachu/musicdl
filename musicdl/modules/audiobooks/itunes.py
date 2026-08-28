'''
Function:
    Implementation of ITunesMusicClient: https://www.apple.com/itunes/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
import xml.etree.ElementTree as ET
from functools import reduce
from contextlib import suppress
from rich.progress import Progress
from urllib.parse import urlencode
from typing_extensions import Unpack
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import legalizestring, resp2json, usesearchheaderscookies, safeextractfromdict, SongInfo, SongInfoUtils, AudioLinkTester


'''ITunesMusicClient'''
class ITunesMusicClient(BaseMusicClient):
    source = 'ITunesMusicClient'
    ALLOWED_SEARCH_TYPES = ['podcast']
    def __init__(self, allowed_search_types: list = None, **kwargs: Unpack[BaseMusicClientKwargs]):
        self.allowed_search_types = list(set(allowed_search_types or ITunesMusicClient.ALLOWED_SEARCH_TYPES))
        super(ITunesMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, self.search_size_per_page = rule or {}, request_overrides or {}, self.search_size_per_source
        (default_rule := {"term": keyword, "limit": self.search_size_per_source, "media": "podcast"}).update(rule)
        # construct search urls
        search_urls, page_size, base_url = [], max(self.search_size_per_page, 200), 'https://itunes.apple.com/search?'
        for search_type in ITunesMusicClient.ALLOWED_SEARCH_TYPES:
            if search_type not in self.allowed_search_types: continue
            (default_rule_search_type := copy.deepcopy(default_rule))['media'] = search_type
            default_rule_search_type['limit'] = page_size
            search_urls.append({search_type: base_url + urlencode(default_rule_search_type)})
        # return
        return search_urls
    '''_parsebypodcast'''
    def _parsebypodcast(self, search_results, song_infos: list = [], request_overrides: dict = None, progress: Progress = None, main_page_no: int = 1):
        # init
        to_seconds_func = lambda x: (lambda s: 0 if not s else (lambda p: p[-3]*3600+p[-2]*60+p[-1] if len(p)>=3 else p[0]*60+p[1] if len(p)==2 else p[0] if len(p)==1 else 0)([int(v) for v in re.findall(r'\d+', s.replace('：', ':'))]) if (':' in s or '：' in s) else (lambda h,m,sec,num: (lambda tot: tot if tot>0 else num)(h*3600+m*60+sec))(int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:小时|时|h|hr)', s)) else 0, int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:分钟|分|m|min)', s)) else 0, (int(mo.group(1)) if (mo:=re.search(r'(\d+)\s*(?:秒|s|sec)', s)) else (int(mo.group(1)) if (mo:=re.search(r'(?:分钟|分|m|min)\s*(\d+)\b', s)) else 0)), int(mo.group(0)) if (mo:=re.search(r'\d+', s)) else 0))(str(x).strip().lower())
        element_to_dict_func = lambda element: reduce(lambda item_dict, child: (item_dict.__setitem__("enclosure" if child.tag == "enclosure" else child.tag, child.attrib if child.tag == "enclosure" else child.text) or item_dict), element, {})
        namespaces = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd', 'dc': 'http://purl.org/dc/elements/1.1/', 'content': 'http://purl.org/rss/1.0/modules/content/'}
        # parse albums one by one
        for search_result in search_results['results']:
            if (not isinstance(search_result, dict)) or (not (album_id := search_result.get('collectionId'))): continue
            # --basic song info class
            download_results, tracks_in_this_album, request_overrides = [], [], dict(request_overrides or {})
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_results, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('collectionName') or search_result.get('trackName') or search_result.get('collectionCensoredName') or search_result.get('trackCensoredName')), singers=legalizestring(search_result.get('artistName')), 
                album=f"{safeextractfromdict(search_result, ['trackCount'], 0) or 0} Episodes", ext=None, file_size_bytes=None, file_size=None, identifier=album_id, duration_s=None, duration='-:-:-', lyric=None, cover_url=search_result.get('cover'), download_url=None, download_url_status={}, episodes=[],
            )
            # --download all pages for further processing
            download_album_pid = progress.add_task(f"{self.source}.p{main_page_no}._parsebypodcast >>> (0/1) pages downloaded in album {album_id}", total=1)
            with suppress(Exception): feed_resp = None; (feed_resp := self.get(search_result['feedUrl'], timeout=10)).raise_for_status()
            if not locals().get('feed_resp') or not hasattr(locals().get('feed_resp'), 'text'): continue
            download_results.append(feed_resp.content); progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}.p{main_page_no}._parsebypodcast >>> (1/1) pages downloaded in album {album_id}")
            # --parse tracks in this album one by one
            tracks_in_this_album, channel = (root := ET.fromstring(feed_resp.content)).findall('./channel/item'), root.find('./channel')
            album_info = {"album_title": channel.findtext('title', default='NULL'), "album_author": channel.findtext('itunes:author', namespaces=namespaces), "album_cover": None}
            if (album_image_node := channel.find('itunes:image', namespaces)) is not None: album_info["album_cover"] = album_image_node.get('href')
            download_album_pid = progress.add_task(f"{self.source}.p{main_page_no}._parsebypodcast >>> (0/{len(tracks_in_this_album)}) episodes completed in album {album_id}", total=len(tracks_in_this_album))
            for track_idx, track in enumerate(tracks_in_this_album):
                if track_idx > 0: progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}.p{main_page_no}._parsebypodcast >>> ({track_idx}/{len(tracks_in_this_album)}) episodes completed in album {album_id}")
                download_url = enclosure.get('url') if (enclosure := track.find('enclosure')) is not None else None
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                with suppress(Exception): duration_in_secs = 0; duration_in_secs = float(track.findtext('itunes:duration', namespaces=namespaces).strip())
                with suppress(Exception): duration_in_secs = duration_in_secs or to_seconds_func(track.findtext('itunes:duration', namespaces=namespaces).strip())
                eps_info = SongInfo(
                    raw_data={'search': search_result, 'download': element_to_dict_func(track), 'lyric': {}}, source=self.source, song_name=legalizestring(track.find('title').text.strip() if track.find('title') is not None else f"Episode {track_idx+1} {song_info.song_name}"), singers=legalizestring(track.findtext('dc:creator', namespaces=namespaces) or track.findtext('itunes:author', namespaces=namespaces) or album_info.get('album_author') or song_info.singers), album=legalizestring(album_info.get('album_title') or song_info.song_name), 
                    ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=f'{song_info.identifier}ep{track_idx+1}', duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=None, cover_url=(image_node.get("href") if (image_node := track.find("itunes:image", namespaces=namespaces)) is not None else None) or album_info["album_cover"], download_url=download_url_status['download_url'], download_url_status=download_url_status, 
                )
                if not eps_info.with_valid_download_url or eps_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                if eps_info.with_valid_download_url and eps_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: song_info.episodes.append(eps_info)
            progress.advance(download_album_pid, 1); progress.update(download_album_pid, description=f"{self.source}.p{main_page_no}._parsebypodcast >>> ({track_idx+1}/{len(tracks_in_this_album)}) episodes completed in album {album_id}")
            if len(song_info.episodes) == 0 or not song_info.with_valid_download_url: continue
            # --post processing
            with suppress(Exception): song_info.duration_s = sum([float(eps.duration_s) for eps in song_info.episodes]); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
            with suppress(Exception): song_info.file_size_bytes = sum([float(eps.file_size_bytes) for eps in song_info.episodes]); song_info.file_size = SongInfoUtils.byte2mb(song_info.file_size_bytes)
            if song_info.with_valid_download_url: song_info.album = f"{len(song_info.episodes)} Episodes"; song_infos.append(song_info)
            if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
        # return
        return song_infos
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = '', request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, search_type, search_url, page_no = request_overrides or {}, list(search_url.keys())[0], list(search_url.values())[0], 1
        task_id = progress.add_task(f"{self.source}.{search_type}._search >>> Start to process search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.get(search_url, **request_overrides)).raise_for_status()
            # --parse based on search type
            parsers = {'podcast': self._parsebypodcast, }
            parsers[search_type](resp2json(resp), song_infos=song_infos, request_overrides=request_overrides, progress=progress, main_page_no=page_no)
            # --update progress
            progress.update(task_id, description=f'{self.source}.{search_type}._search >>> All search results processed on page {page_no}', total=len(song_infos), completed=len(song_infos))
        # failure
        except Exception as err:
            progress.update(task_id, description=f'{self.source}.{search_type}._search >>> {keyword} on page {page_no} (Error: {err})')
            self.logger_handle.error(f'{self.source}.{search_type}._search >>> {keyword} on page {page_no} (Error: {err})', disable_print=self.disable_print)
        # return
        return song_infos