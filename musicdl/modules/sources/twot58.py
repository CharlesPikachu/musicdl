'''
Function:
    Implementation of TwoT58MusicClient: https://www.2t58.com/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import copy
from bs4 import BeautifulSoup
from .base import BaseMusicClient
from rich.progress import Progress
from urllib.parse import urljoin, urlparse
from ..utils import legalizestring, usesearchheaderscookies, extractdurationsecondsfromlrc, seconds2hms, cleanlrc, SongInfo, RandomIPGenerator


'''TwoT58MusicClient'''
class TwoT58MusicClient(BaseMusicClient):
    source = 'TwoT58MusicClient'
    def __init__(self, **kwargs):
        super(TwoT58MusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", "priority": "u=0, i", "referer": "https://www.2t58.com/so/%E5%8F%AF%E6%83%9C.html",
            "cookie": "Hm_tf_hx9umupwu8o=1766942296; Hm_lvt_b8f2e33447143b75e7e4463e224d6b7f=1766942296; cac9054cc9568db7fa51d16ee602cd7b=fd6762f9a63b502fda3befef86ea6460; server_name_session=91a76d925399962c481089ef4a83ce4e; Hm_lvt_hx9umupwu8o=1766942296,1768900847; Hm_lpvt_hx9umupwu8o=1768901202",
            "sec-ch-ua": "\"Not(A:Brand\";v=\"8\", \"Chromium\";v=\"144\", \"Google Chrome\";v=\"144\"", "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document", "sec-fetch-mode": "navigate", "sec-fetch-site": "same-origin", "sec-fetch-user": "?1", "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        }
        self.default_download_headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        # construct search urls
        self.search_size_per_page = min(self.search_size_per_source, 68)
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            if int(count // page_size) + 1 == 1: search_urls.append(f'https://www.2t58.com/so/{keyword}.html')
            else: search_urls.append(f'https://www.2t58.com/so/{keyword}/{int(count // page_size) + 1}.html')
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        soup = BeautifulSoup(html_text, "lxml")
        search_results, base_url = [], 'https://www.2t58.com/'
        for a in soup.select(".play_list ul li .name a"):
            title, href = a.get_text(strip=True), a.get("href", "")
            song_id = urlparse(urljoin(base_url, href)).path.strip('/').split('/')[-1].split('.')[0]
            search_results.append({"title": title, "url": urljoin(base_url, href) if base_url else href, "path": href, "id": song_id})
        return search_results
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
            search_results = self._parsesearchresultsfromhtml(resp.text)
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('url' not in search_result) or ('id' not in search_result): continue
                song_info = SongInfo(source=self.source)
                for quality in ['flac', 'wav', '320']:
                    headers = copy.deepcopy(self.default_headers)
                    RandomIPGenerator().addrandomipv4toheaders(headers=headers)
                    try: download_url = self.get(f"https://www.2t58.com/plug/down.php?ac=music&id={search_result['id']}&k={quality}", allow_redirects=True, headers=headers, **request_overrides).url
                    except: continue
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(((m.group(1) if (m := re.search(r"《(.*?)》", (s := re.sub(r"\s*\[[^\]]*\]\s*$", "", str(search_result.get("title") or "NULL"))))) else s).strip())), 
                        singers=legalizestring(re.sub(r"\s*\[[^\]]*\]\s*$", "", str(search_result.get("title") or "NULL")).split("《", 1)[0].strip()), album='NULL', ext=download_url.split('?')[0].split('.')[-1] or 'mp3', file_size='NULL', identifier=search_result['id'], duration='-:-:-', 
                        lyric='NULL', cover_url=None, download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides),
                    )
                    if not song_info.with_valid_download_url: continue
                    song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
                    if song_info.with_valid_download_url: break
                if not song_info.with_valid_download_url: continue
                # --lyric results
                try:
                    resp = self.get(f"https://www.2t58.com/plug/down.php?ac=music&lk=lrc&id={search_result['id']}", **request_overrides)
                    resp.raise_for_status()
                    song_info.lyric = cleanlrc(resp.text.replace('[00:00.00]欢迎来访爱听音乐网 www.2t58.com\r\n', ''))
                    song_info.duration_s = extractdurationsecondsfromlrc(song_info.lyric)
                    song_info.duration = seconds2hms(song_info.duration_s)
                except:
                    song_info.lyric, song_info.duration = 'NULL', '-:-:-'
                # --cover results
                try:
                    resp = self.get(search_result['url'], **request_overrides)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text)
                    cover = soup.select_one("#mcover")
                    song_info.cover_url = cover["src"] if cover and cover.has_attr("src") else None
                except:
                    song_info.cover_url = None
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