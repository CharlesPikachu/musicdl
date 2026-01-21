'''
Function:
    Implementation of KKWSMusicClient: https://www.kkws.cc/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .base import BaseMusicClient
from rich.progress import Progress
from ..utils import legalizestring, usesearchheaderscookies, seconds2hms, searchdictbykey, safeextractfromdict, extractdurationsecondsfromlrc, cleanlrc, SongInfo, QuarkParser


'''KKWSMusicClient'''
class KKWSMusicClient(BaseMusicClient):
    source = 'KKWSMusicClient'
    MUSIC_QUALITY_RANK = {"DSD": 100, "DSF": 100, "DFF": 100, "WAV": 95, "AIFF": 95, "FLAC": 90, "ALAC": 90, "APE": 88, "WV": 88, "OPUS": 70, "AAC": 65, "M4A": 65, "OGG": 60, "VORBIS": 60, "MP3": 50, "WMA": 45}
    def __init__(self, **kwargs):
        super(KKWSMusicClient, self).__init__(**kwargs)
        assert self.quark_parser_config.get('cookies'), f'{self.source}.__init__ >>> "quark_parser_config" is not configured, so the songs cannot be downloaded.'
        self.default_search_headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
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
        self.search_size_per_page = min(self.search_size_per_source, 15)
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            search_urls.append(f'https://www.kkws.cc/search.html?key={keyword}&page={int(count // page_size) + 1}')
            count += page_size
        # return
        return search_urls
    '''_parsesearchresultsfromhtml'''
    def _parsesearchresultsfromhtml(self, html_text: str):
        soup = BeautifulSoup(html_text, "lxml")
        search_results, base_url = [], 'https://www.kkws.cc/'
        for li in soup.select("ul.listbox > li"):
            a = li.select_one("h2 a[href]")
            if not a: continue
            href = urljoin(base_url, a["href"])
            title_attr = (a.get("title") or "").strip()
            full_text = a.get_text(" ", strip=True)
            name = title_attr.replace("免费下载", "").strip() if title_attr else full_text
            name = re.sub(r"\s*\[[^\]]+\]\s*", " ", name).strip()
            name = re.sub(r"\s*-\s*\d+(\.\d+)?[KMG]?\s*$", "", name).strip()
            m_fmt = re.search(r"\[([^\]]+)\]", full_text)
            file_format = m_fmt.group(1).strip() if m_fmt else ""
            m_size = re.search(r"-\s*([0-9.]+\s*[KMG]?)", full_text, re.IGNORECASE)
            size = (m_size.group(1).replace(" ", "") if m_size else "").strip()
            ems = li.select("small em")
            share_time, singer = "", ""
            if len(ems) >= 1: share_time = ems[0].get_text(strip=True).replace("分享时间：", "").strip()
            if len(ems) >= 2: singer = ems[-1].get_text(strip=True).replace("演唱：", "").strip()
            m_id = re.search(r"/detail/(\d+)\.html", href)
            item_id = m_id.group(1) if m_id else ""
            search_results.append({"id": item_id, "name": name, "format": file_format, "size": size, "share_time": share_time, "singer": singer, "detail_url": href})
        return search_results
    '''_extractlyricsandquark'''
    def _extractlyricsandquark(self, html_text: str):
        soup = BeautifulSoup(html_text, "lxml")
        tb = soup.select_one("#textbox")
        to_mmss_func = lambda t: (lambda s: f"{s//60:02d}:{s%60:02d}")(int(float(t.split(":",1)[0])*60+float(t.split(":",1)[1])) if ":" in t else int(float(t)))
        lyrics = "" if not tb else "\n".join((f"[{to_mmss_func(m.group(1))}] {m.group(2).strip()}" if (m:=re.match(r"^\[(\d+(?:\.\d+)?|\d{1,2}:\d{2}(?:\.\d+)?)\]\s*(.*)$", line)) else f"{line}") for line in (l.strip() for l in tb.get_text("\n").splitlines()) if line)
        url_map, rank = {}, KKWSMusicClient.MUSIC_QUALITY_RANK
        for a in soup.select("div.downbox a[onclick]"):
            onclick = (a.get("onclick") or "").strip()
            if not onclick: continue
            args = re.findall(r"'([^']*)'", onclick)
            name = fmt = url = None
            if onclick.startswith("openModel") and len(args) >= 4: name_fmt, url, fmt = args[1], args[2], (args[3] or None)
            elif onclick.startswith("mbgotourl") and len(args) >= 3: name_fmt, url, fmt = args[1], args[2], None
            else: continue
            if "|" in name_fmt: name, fmt2 = map(str.strip, name_fmt.split("|", 1)); fmt = fmt or fmt2
            else: name = name_fmt.strip()
            if not (url and "pan.quark.cn" in url): continue
            e = url_map.setdefault(url, {"url": url, "formats": set(), "names": set()})
            if fmt:
                for k in rank: fmt = k if k.lower() in fmt.lower() else fmt
                e["formats"].add(fmt)
            if name: e["names"].add(name)
        quark_links = sorted(({"url": e["url"], "formats": sorted(e["formats"]), "names": sorted(e["names"])} for e in url_map.values()), key=lambda x: rank.get(x["formats"][0] if x["formats"] else "UNKNOWN", 0), reverse=True)
        quark_links = [q for q in quark_links if isinstance(q, dict) and q.get('url')]
        return {"lyrics": lyrics, "quark_links": quark_links}
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
                if not isinstance(search_result, dict) or ('detail_url' not in search_result) or ('id' not in search_result): continue
                song_info = SongInfo(source=self.source)
                try: resp = self.get(search_result['detail_url'], **request_overrides); resp.raise_for_status(); download_result = self._extractlyricsandquark(resp.text)
                except: continue
                for quark_info in download_result['quark_links']:
                    quark_download_url = quark_info['url']
                    download_result['quark_parse_result'], download_url = QuarkParser.parsefromurl(quark_download_url, **self.quark_parser_config)
                    if not download_url or not str(download_url).startswith('http'): continue
                    duration = [int(float(d)) for d in searchdictbykey(download_result, 'duration') if int(float(d)) > 0]
                    duration_s = duration[0] if duration else 0
                    song_info = SongInfo(
                        raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)),
                        singers=legalizestring(safeextractfromdict(search_result, ['singer'], None)), album='NULL', ext='mp3', file_size='NULL', identifier=search_result['id'], duration_s=duration_s,
                        duration=seconds2hms(duration_s), lyric=cleanlrc(safeextractfromdict(download_result, ['lyrics'], '')), cover_url=None, download_url=download_url,
                        download_url_status=self.quark_audio_link_tester.test(download_url, request_overrides), default_download_headers=self.quark_default_download_headers,
                    )
                    song_info.download_url_status['probe_status'] = self.quark_audio_link_tester.probe(song_info.download_url, request_overrides)
                    song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                    song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
                    if song_info.with_valid_download_url: break
                if not song_info.lyric or '歌词获取失败' in song_info.lyric: song_info.lyric = 'NULL'
                if not song_info.duration or song_info.duration == '-:-:-': song_info.duration = seconds2hms(extractdurationsecondsfromlrc(song_info.lyric))
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