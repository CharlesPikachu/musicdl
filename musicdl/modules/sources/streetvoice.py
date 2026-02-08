'''
Function:
    Implementation of StreetVoiceMusicClient: https://www.streetvoice.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
import time
from bs4 import BeautifulSoup
from .base import BaseMusicClient
from rich.progress import Progress
from urllib.parse import urlencode, urljoin
from ..utils import legalizestring, resp2json, usesearchheaderscookies, seconds2hms, safeextractfromdict, cleanlrc, SongInfo


'''StreetVoiceMusicClient'''
class StreetVoiceMusicClient(BaseMusicClient):
    source = 'StreetVoiceMusicClient'
    def __init__(self, **kwargs):
        super(StreetVoiceMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
            "Referer": "https://www.streetvoice.cn/", "x-requested-with": "XMLHttpRequest", 
        }
        self.default_download_headers = copy.deepcopy(self.default_search_headers)
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        self.search_size_per_page = min(10, self.search_size_per_page)
        rule, request_overrides = rule or {}, request_overrides or {}
        # search rules
        default_rule = {'page': 1, 'q': keyword, 'type': 'song', '_pjax': '#pjax-container'}
        default_rule.update(rule)
        # construct search urls based on search rules
        base_url = 'https://www.streetvoice.cn/search/?'
        search_urls, page_size, count = [], self.search_size_per_page, 0
        while self.search_size_per_source > count:
            page_rule = copy.deepcopy(default_rule)
            page_rule['page'] = int(count // page_size) + 1
            search_urls.append(base_url + urlencode(page_rule))
            count += page_size
        # return
        return search_urls
    '''_extractonepage'''
    def _extractonepage(self, html: str, page_url: str):
        soup, items = BeautifulSoup(html, "html.parser"), []
        for li in soup.select("ul.list-group-song li.work-item.item_box"):
            title_a = li.select_one(".work-item-info h4 a"); artist_a = li.select_one(".work-item-info h5 a")
            img = li.select_one(".cover-block img"); play_btn = li.select_one("button.js-search[data-id]")
            like_btn = li.select_one("button.js-like-btn[data-like-count]"); like_raw = like_btn.get("data-like-count") if like_btn else None
            song_href = title_a.get("href") if title_a else None; artist_href = artist_a.get("href") if artist_a else None
            items.append({
                "song_id": play_btn.get("data-id") if play_btn else None, "title": title_a.get_text(strip=True) if title_a else None, "artist": artist_a.get_text(strip=True) if artist_a else None, "song_url": urljoin(page_url, song_href) if song_href else None, 
                "artist_url": urljoin(page_url, artist_href) if artist_href else None, "cover_url": img.get("src") if img else None, "like_raw": like_raw,
            })
        return items
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
            search_results = self._extractonepage(resp.text, search_url)
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('song_id' not in search_result): continue
                song_info = SongInfo(source=self.source)
                try: resp = self.get(f"https://www.streetvoice.cn/api/v5/song/{search_result['song_id']}/?_={int(time.time() * 1000)}", **request_overrides); resp.raise_for_status()
                except Exception: continue
                download_result = resp2json(resp=resp)
                try: resp = self.post(f"https://www.streetvoice.cn/api/v5/song/{search_result['song_id']}/hls/file/", **request_overrides); resp.raise_for_status()
                except Exception: continue
                download_result['download_url'] = resp2json(resp=resp).get('file')
                if not download_result['download_url'] or not str(download_result['download_url']).startswith('http'): continue
                download_url = download_result['download_url']
                try: resp = self.session.head(download_url, **request_overrides); resp.raise_for_status(); download_url_status = {'ok': True}
                except Exception: continue
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': download_result, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(download_result, ['name'], None)),
                    singers=legalizestring(safeextractfromdict(download_result, ['user', 'profile', 'nickname'], None)), album=legalizestring(safeextractfromdict(download_result, ['album', 'name'], None)),
                    ext=download_url.removesuffix('.m3u8').split('?')[0].split('.')[-1], file_size='HLS', identifier=search_result['song_id'], duration_s=safeextractfromdict(download_result, ['length'], 0),
                    duration=seconds2hms(safeextractfromdict(download_result, ['length'], 0)), lyric=cleanlrc(safeextractfromdict(download_result, ['lyrics'], 'NULL')), cover_url=download_result.get('image'), 
                    download_url=download_url, download_url_status=download_url_status, protocol='HLS'
                )
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