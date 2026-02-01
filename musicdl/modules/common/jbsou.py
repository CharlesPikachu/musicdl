'''
Function:
    Implementation of JBSouMusicClient: https://www.jbsou.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
from urllib.parse import urljoin
from rich.progress import Progress
from ..sources import BaseMusicClient
from ..utils import legalizestring, resp2json, usesearchheaderscookies, seconds2hms, extractdurationsecondsfromlrc, safeextractfromdict, cleanlrc, SongInfo


'''JBSouMusicClient'''
class JBSouMusicClient(BaseMusicClient):
    source = 'JBSouMusicClient'
    ALLOWED_SITES = ['netease', 'qq', 'kugou', 'kuwo', 'migu', 'qianqian'][:-2] # it seems qianqian and migu are useless, recorded in 2026-01-29
    def __init__(self, **kwargs):
        self.allowed_music_sources = list(set(kwargs.pop('allowed_music_sources', JBSouMusicClient.ALLOWED_SITES)))
        super(JBSouMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36", 
            "accept": "application/json, text/javascript, */*; q=0.01", "accept-encoding": "gzip, deflate, br, zstd", "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "origin": "https://www.jbsou.cn", "x-requested-with": "XMLHttpRequest", "referer": "https://www.jbsou.cn/"
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        }
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides = rule or {}, request_overrides or {}
        self.search_size_per_page = min(self.search_size_per_page, 10)
        allowed_music_sources = copy.deepcopy(self.allowed_music_sources)
        # construct search urls based on search rules
        base_url = 'https://www.jbsou.cn/'
        search_urls, page_size = [], self.search_size_per_page
        for source in JBSouMusicClient.ALLOWED_SITES:
            if source not in allowed_music_sources: continue
            source_default_rule, count = {'input': keyword, 'filter': 'name', 'type': source, 'page': 1}, 0
            source_default_rule.update(rule)
            while self.search_size_per_source > count:
                page_rule = copy.deepcopy(source_default_rule)
                page_rule['page'] = str(int(count // page_size) + 1)
                search_urls.append({'url': base_url, 'data': page_rule})
                count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = None, request_overrides: dict = None, song_infos: list = [], progress: Progress = None, progress_id: int = 0):
        # init
        request_overrides, base_url = request_overrides or {}, "https://www.jbsou.cn/"
        source = search_url['data']['type']
        # successful
        try:
            # --search results
            resp = self.post(**search_url, **request_overrides)
            resp.raise_for_status()
            search_results = resp2json(resp)['data']
            for search_result in search_results:
                # --download results
                if not isinstance(search_result, dict) or ('songid' not in search_result) or ('url' not in search_result): continue
                search_result['source'] = source
                song_info = SongInfo(source=self.source, root_source=search_result['source'])
                download_url = urljoin(base_url, search_result['url'])
                try: (resp := self.session.head(download_url, allow_redirects=True, **request_overrides)).raise_for_status(); download_url = resp.url
                except Exception: continue
                cover_url = urljoin(base_url, search_result.get('cover', "") or "")
                try: (resp := self.session.head(cover_url, timeout=10, allow_redirects=True, **request_overrides)).raise_for_status(); cover_url = resp.url
                except Exception: cover_url = cover_url
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(safeextractfromdict(search_result, ['name'], None)),
                    singers=legalizestring(str(safeextractfromdict(search_result, ['artist'], "")).replace('/', ', ')), album=legalizestring(search_result.get('album')),
                    ext=download_url.split('?')[0].split('.')[-1], file_size='NULL', identifier=search_result['songid'], duration='-:-:-', lyric=None, cover_url=cover_url, 
                    download_url=download_url, download_url_status=self.audio_link_tester.test(download_url, request_overrides), root_source=search_result['source'],
                )
                if not song_info.with_valid_download_url: continue
                song_info.download_url_status['probe_status'] = self.audio_link_tester.probe(song_info.download_url, request_overrides)
                song_info.file_size = song_info.download_url_status['probe_status']['file_size']
                song_info.ext = song_info.download_url_status['probe_status']['ext'] if (song_info.download_url_status['probe_status']['ext'] and song_info.download_url_status['probe_status']['ext'] not in ('NULL', )) else song_info.ext
                # --lyric results
                try:
                    resp = self.get(urljoin(base_url, search_result['lrc']), **request_overrides)
                    resp.raise_for_status()
                    lyric, lyric_result = cleanlrc(resp.text), {'lyric': resp.text}
                    song_info.duration_s = extractdurationsecondsfromlrc(lyric)
                    song_info.duration = seconds2hms(song_info.duration_s)
                except:
                    lyric_result, lyric = dict(), 'NULL'
                song_info.lyric = lyric
                song_info.raw_data['lyric'] = lyric_result
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