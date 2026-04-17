'''
Function:
    Implementation of HTQYYMusicClient: http://www.htqyy.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
from html import unescape
from bs4 import BeautifulSoup
from contextlib import suppress
from urllib.parse import urljoin
from rich.progress import Progress
from ..sources import BaseMusicClient
from ..utils import legalizestring, usesearchheaderscookies, SongInfo, AudioLinkTester


'''HTQYYMusicClient'''
class HTQYYMusicClient(BaseMusicClient):
    source = 'HTQYYMusicClient'
    def __init__(self, **kwargs):
        super(HTQYYMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36", "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "cache-control": "max-age=0", "host": "www.htqyy.com", "proxy-connection": "keep-alive", "referer": "http://www.htqyy.com/", "upgrade-insecure-requests": "1",
        }
        self.default_download_headers = {"accept-encoding": "identity;q=1, *;q=0", "referer": "http://www.htqyy.com/", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        search_urls = [f'http://www.htqyy.com/home/search?wd={keyword}']
        self.search_size_per_page = self.search_size_per_source
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        base_url, soup, search_results = "http://www.htqyy.com", BeautifulSoup(html_text, "html.parser"), []
        for li in soup.select("ul#musicList li.musicItem"):
            song_id = chk["value"].strip() if (chk := li.select_one('input[type="checkbox"][name="checked"]')) and chk.has_attr("value") else None
            play_url = urljoin(base_url, play_href) if (play_href := a_title["href"].strip() if (a_title := li.select_one("span.title a")) and a_title.has_attr("href") else None) else None
            artist = a_artist.get_text(" ", strip=True) if (a_artist := li.select_one("span.artistName a")) else None; artist_url = urljoin(base_url, a_artist["href"]) if a_artist and a_artist.has_attr("href") else None
            album = a_album.get_text(" ", strip=True) if (a_album := li.select_one("span.albumName a")) else None; album_url = urljoin(base_url, a_album["href"]) if a_album and a_album.has_attr("href") else None
            search_results.append({"id": song_id, "sid": a_title.get("sid") if a_title else None, "title": a_title.get_text(" ", strip=True) if a_title else None, "title_attr": a_title.get("title") if a_title else None, "artist": artist, "artist_url": artist_url, "album": album, "album_url": album_url, "play_url": play_url})
        return search_results
    '''_extractplayscriptinfo'''
    def _extractplayscriptinfo(self, html_text: str):
        unescape_func, script_text, pagedata = lambda x: unescape(x) if isinstance(x, str) else x, None, {}
        for s in BeautifulSoup(html_text, "lxml").find_all("script"):
            if not (txt := s.string or s.get_text()): continue
            if ("PageData." in txt or "var PageData" in txt) and ("fileHost" in txt or "var mp3" in txt): script_text = txt; break
        if not script_text or 'PageData' not in str(script_text): return {}
        t = script_text; grabvar_func = lambda name: (None if (m := re.search(rf'\bvar\s+{re.escape(name)}\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([0-9]+))\s*;', t)) is None else (int(v) if m.group(3) is not None else v) if (v := (m.group(1) or m.group(2) or m.group(3))) is not None else None)
        for m in re.finditer(r'PageData\.(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([0-9]+))\s*;', t):
            key = m.group(1); pagedata[key] = m.group(2) or m.group(3) or m.group(4)
            if m.group(4) is not None: pagedata[key] = int(pagedata[key])
        file_format, ip = grabvar_func("format") or pagedata.get("format"), grabvar_func("ip")
        file_host, mp3_path, bd_text, bd_text2, img_url, mp3_url = grabvar_func("fileHost"), grabvar_func("mp3"), grabvar_func("bdText"), grabvar_func("bdText2"), grabvar_func("imgUrl"), None
        if file_host and mp3_path and re.search(r'\bmp3\s*=\s*fileHost\s*\+\s*mp3\s*;', t): mp3_url = file_host + mp3_path
        return {"format": unescape_func(file_format), "PageData": {k: unescape_func(v) for k, v in pagedata.items()}, "ip": unescape_func(ip), "fileHost": unescape_func(file_host), "mp3_path": unescape_func(mp3_path), "mp3_url": unescape_func(mp3_url), "bdText": unescape_func(bd_text), "bdText2": unescape_func(bd_text2), "imgUrl": unescape_func(img_url)}
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
                if not isinstance(search_result, dict) or ('play_url' not in search_result): continue
                song_info, song_id = SongInfo(source=self.source), search_result.get('id') or search_result.get('sid')
                with suppress(Exception): (resp := self.get(search_result['play_url'], **request_overrides)).raise_for_status()
                if not locals().get('resp') or not hasattr(locals().get('resp'), 'text'): continue
                download_url: str = (download_result := self._extractplayscriptinfo(resp.text)).get('mp3_url')
                if not download_url or not str(download_url).startswith('http'): continue
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('title')), singers=legalizestring(search_result.get('artist')), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], file_size_bytes=download_url_status['file_size_bytes'], 
                    file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric='NULL', cover_url=download_result.get('imgUrl'), download_url=download_url_status['download_url'], download_url_status=download_url_status, default_download_headers=self.default_download_headers
                )
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
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