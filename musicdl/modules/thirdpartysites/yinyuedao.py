'''
Function:
    Implementation of YinyuedaoMusicClient: https://1mp3.top/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import base64
from html import unescape
from bs4 import BeautifulSoup
from contextlib import suppress
from rich.progress import Progress
from ..sources import BaseMusicClient
from urllib.parse import urljoin, urlparse
from ..utils import legalizestring, usesearchheaderscookies, safeextractfromdict, searchdictbykey, resp2json, cleanlrc, SongInfo, QuarkParser, AudioLinkTester, SongInfoUtils


'''YinyuedaoMusicClient'''
class YinyuedaoMusicClient(BaseMusicClient):
    source = 'YinyuedaoMusicClient'
    MUSIC_QUALITY_RANK = {"DSD": 100, "DSF": 100, "DFF": 100, "WAV": 95, "AIFF": 95, "FLAC": 90, "ALAC": 90, "APE": 88, "WV": 88, "OPUS": 70, "AAC": 65, "M4A": 65, "OGG": 60, "VORBIS": 60, "MP3": 50, "WMA": 45}
    def __init__(self, **kwargs):
        super(YinyuedaoMusicClient, self).__init__(**kwargs)
        if not self.quark_parser_config.get('cookies'): self.logger_handle.warning(f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so song downloads are restricted and only mp3 files can be downloaded.')
        self.default_search_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "priority": "u=0, i", "referer": "https://1mp3.top/",
            "sec-ch-ua": "\"Chromium\";v=\"142\", \"Google Chrome\";v=\"142\", \"Not_A Brand\";v=\"99\"", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"", "sec-fetch-dest": "document", "sec-fetch-mode": "navigate", "sec-fetch-site": "same-origin", "sec-fetch-user": "?1", "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        }
        self.default_download_headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        search_urls = [f'https://1mp3.top/search.html?keyword={keyword}']
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsemusicpage'''
    def _parsemusicpage(self, html_text: str, base_url: str = ""):
        soup, lyrics, links, seen = BeautifulSoup(html_text, "html.parser"), "NULL", [], set()
        if (article := soup.select_one("section#demo article")): lyrics = re.sub(r"\n+", "\n", unescape(article.get_text("\n", strip=True))).strip()
        cover = ""; img = soup.select_one("#album-cover") or soup.select_one(".cover-art img")
        if img and img.get("src"): cover = urljoin(base_url, img["src"].strip())
        for a in soup.select("a.download-link[data-url]"):
            fmt = (a.get("data-format") or "").strip().upper(); text = a.get_text(" ", strip=True)
            if not (url := (a.get("data-url") or "").strip()): continue
            fmt = fmt or ((m.group(1).upper()) if (m := re.search(r"\b(DSD|DSF|DFF|WAV|AIFF|FLAC|ALAC|APE|WV|OPUS|AAC|M4A|OGG|VORBIS|MP3|WMA)\b", text, re.I)) else None)
            item = {"format": fmt, "score": YinyuedaoMusicClient.MUSIC_QUALITY_RANK.get(fmt, -1), "url": urljoin(base_url, url), "text": text}
            if (key := (item["format"], item["url"])) not in seen: seen.add(key); links.append(item)
        links.sort(key=lambda x: (-x["score"], x["format"], x["url"]))
        return {"lyrics": lyrics, "cover": cover, "quark_links": links}
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text, base_url="https://www.1mp3.top"):
        soup, search_results = BeautifulSoup(html_text, "html.parser"), []
        for a in soup.select('a[href^="/mdetail/"]'):
            if len((cols := a.select("div.row > div"))) < 2: continue
            token = (href := a.get("href", "")).rsplit("/", 1)[-1]
            try: music_id = base64.b64decode(token).decode(errors="ignore").split("|", 1)[0]
            except Exception: music_id = token
            search_results.append({"id": music_id, "title": cols[0].get_text(" ", strip=True), "singer": cols[1].get_text(" ", strip=True), "url": urljoin(base_url, href)})
        return search_results
    '''_parsesearchresultfromquark'''
    def _parsesearchresultfromquark(self, search_result: dict, download_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result.get('id')
        extract_duration_func = lambda s: float(re.search(r"\[\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*\]", s).group(1))
        # parse download url
        for quark_download_url in download_result['quark_links']:
            if not isinstance(quark_download_url, dict) or not quark_download_url.get('format'): continue
            download_result['quark_parse_result'], download_url = QuarkParser.parsefromurl(quark_download_url['url'], **self.quark_parser_config)
            if not download_url or not str(download_url).startswith('http'): continue
            download_url_status: dict = self.quark_audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
            duration_in_secs = duration[0] if (duration := [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]) else 0
            song_info = SongInfo(
                raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('singer')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], 
                identifier=song_id, duration_s=duration_in_secs, duration=SongInfoUtils.seconds2hms(duration_in_secs), lyric=cleanlrc(download_result.get('lyrics')), cover_url=download_result.get("cover"), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.quark_default_download_headers,
            )
            if song_info.with_valid_download_url and song_info.ext in AudioLinkTester.VALID_AUDIO_EXTS: break
        # parse lyric result
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if (not song_info.duration or song_info.duration == '-:-:-') and (re.search(r"\[\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*\]", str(song_info.lyric))): song_info.duration_s = extract_duration_func(song_info.lyric.split('\n')[-1]); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
        # return
        return song_info
    '''_parsesearchresultfromweb'''
    def _parsesearchresultfromweb(self, search_result: dict, download_result: dict, request_overrides: dict = None):
        # init
        request_overrides, song_info, song_id = request_overrides or {}, SongInfo(source=self.source), search_result.get('id')
        encrypted_id = urlparse(str(search_result["url"])).path.strip('/').split('/')[-1]
        extract_duration_func = lambda s: float(re.search(r"\[\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*\]", s).group(1))
        # parse download url
        (resp := self.get(f'https://1mp3.top/geturl?id={encrypted_id}&quality=exhigh&type=json', **request_overrides)).raise_for_status()
        download_result['geturl'] = resp2json(resp=resp); download_url = safeextractfromdict(download_result['geturl'], ['data', 'url'], None)
        if not download_url or not str(download_url).startswith('http'): return song_info
        download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
        song_info = SongInfo(
            raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('singer')), album='NULL', ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
            file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric=cleanlrc(download_result.get('lyrics')), cover_url=download_result.get("cover"), download_url=download_url_status['download_url'], download_url_status=download_url_status
        )
        if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: return song_info
        # parse lyric result
        if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
        if (not song_info.duration or song_info.duration == '-:-:-') and (re.search(r"\[\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*\]", str(song_info.lyric))): song_info.duration_s = extract_duration_func(song_info.lyric.split('\n')[-1]); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
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
            for search_result in self._parsesearchresultsfromhtml(resp.text):
                # --download results
                if not isinstance(search_result, dict) or ('id' not in search_result) or ('url' not in search_result): continue
                # ----obtain basic information
                with suppress(Exception): (resp := self.get(search_result['url'], **request_overrides)).raise_for_status()
                if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                download_result: dict = self._parsemusicpage(resp.text)
                # ----parse from quark links
                with suppress(Exception): song_info = self._parsesearchresultfromquark(search_result, download_result, request_overrides) if self.quark_parser_config.get('cookies') else SongInfo(source=self.source)
                # ----parse from play url
                with suppress(Exception): song_info = self._parsesearchresultfromweb(search_result, download_result, request_overrides) if not song_info.with_valid_download_url else song_info
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
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