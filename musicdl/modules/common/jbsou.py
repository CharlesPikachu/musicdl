'''
Function:
    Implementation of JBSouMusicClient: https://www.jbsou.cn/
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import copy
from typing import Unpack
from contextlib import suppress
from urllib.parse import urljoin
from rich.progress import Progress
from ..sources import BaseMusicClient, BaseMusicClientKwargs
from ..utils import legalizestring, resp2json, usesearchheaderscookies, extractdurationsecondsfromlrc, cleanlrc, SongInfo, AudioLinkTester, SongInfoUtils


'''JBSouMusicClient'''
class JBSouMusicClient(BaseMusicClient):
    source = 'JBSouMusicClient'
    ALLOWED_SITES = ['netease', 'qq', 'kugou', 'kuwo', 'migu', 'qianqian'][:-2] # it seems qianqian and migu are useless, recorded in 2026-01-29
    def __init__(self, allowed_music_sources: list = None, **kwargs: Unpack[BaseMusicClientKwargs]):
        self.allowed_music_sources = list(set(allowed_music_sources or JBSouMusicClient.ALLOWED_SITES)); kwargs['maintain_session'] = True
        super(JBSouMusicClient, self).__init__(**kwargs)
        self.default_search_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",}
        self.default_download_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",}
        self.default_headers = self.default_search_headers
        self._initsession()
    '''_constructsearchurls'''
    def _constructsearchurls(self, keyword: str, rule: dict = None, request_overrides: dict = None):
        # init
        rule, request_overrides, self.search_size_per_page, allowed_music_sources = rule or {}, request_overrides or {}, min(self.search_size_per_page, 10), copy.deepcopy(self.allowed_music_sources)
        # construct search urls
        base_url, search_urls, page_size = 'https://www.jbsou.cn/', [], self.search_size_per_page
        (resp := self.get(base_url, headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "Accept-Encoding": "gzip, deflate, br, zstd", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",}, **request_overrides)).raise_for_status()
        for source in JBSouMusicClient.ALLOWED_SITES:
            if source not in allowed_music_sources: continue
            (source_default_rule := {'input': keyword, 'filter': 'name', 'type': source, 'page': 1}).update(rule); count = 0
            while self.search_size_per_source > count:
                (page_rule := copy.deepcopy(source_default_rule))['page'] = str(int(count // page_size) + 1)
                search_urls.append({'url': base_url, 'data': page_rule})
                count += page_size
        # return
        return search_urls
    '''_search'''
    @usesearchheaderscookies
    def _search(self, keyword: str = '', search_url: dict = None, request_overrides: dict = None, song_infos: list = [], progress: Progress = None):
        # init
        request_overrides, base_url, root_source, page_no, search_result_idx = request_overrides or {}, "https://www.jbsou.cn/", search_url['data']['type'], search_url['data']['page'], -1
        headers = {"Origin": "https://www.jbsou.cn", "X-Requested-With": "XMLHttpRequest", "Referer": "https://www.jbsou.cn/", "Accept": "application/json, text/javascript, */*; q=0.01", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Accept-Encoding": "gzip, deflate, br, zstd", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",}
        task_id = progress.add_task(f"{self.source}.{root_source}._search >>> Start to process the 0th search result on page {page_no}", total=None, completed=0)
        # successful
        try:
            # --search results
            (resp := self.post(**search_url, headers=headers, verify=False, timeout=30, **request_overrides)).raise_for_status()
            for search_result_idx, search_result in enumerate(resp2json(resp)['data']):
                # --update progress
                progress.update(task_id, description=f'{self.source}.{root_source}._search >>> Start to process the {search_result_idx+1}th search result on page {page_no}', completed=search_result_idx+1, total=search_result_idx+1)
                # --download results
                if not isinstance(search_result, dict) or (not search_result.get('songid')) or (not search_result.get('url')): continue
                song_info, download_url = SongInfo(source=self.source, root_source=root_source), urljoin(base_url, search_result['url'])
                with suppress(Exception): download_url = self.session.head(download_url, allow_redirects=True, **request_overrides).url
                cover_url, song_id = urljoin(base_url, search_result.get('cover', "") or ""), search_result['songid']
                with suppress(Exception): cover_url = self.session.head(cover_url, timeout=10, allow_redirects=True, **request_overrides).url
                download_url_status: dict = self.audio_link_tester.test(url=download_url, request_overrides=request_overrides, renew_session=True)
                song_info = SongInfo(
                    raw_data={'search': search_result, 'download': {}, 'lyric': {}}, source=self.source, song_name=legalizestring(search_result.get('name')), singers=legalizestring(str(search_result.get('artist') or '').replace('/', ', ')), album=legalizestring(search_result.get('album')), ext=download_url_status['ext'], 
                    file_size_bytes=download_url_status['file_size_bytes'], file_size=download_url_status['file_size'], identifier=song_id, duration_s=None, duration='-:-:-', lyric=None, cover_url=cover_url, download_url=download_url_status['download_url'], download_url_status=download_url_status, root_source=root_source,
                )
                if not song_info.with_valid_download_url or song_info.ext not in AudioLinkTester.VALID_AUDIO_EXTS: continue
                # --lyric results
                with suppress(Exception): lyric_result, lyric = dict(), 'NULL'; (resp := self.get(urljoin(base_url, search_result['lrc']), **request_overrides)).raise_for_status(); lyric, lyric_result = cleanlrc(resp.text.split('</script>', 1)[-1]), {'lyric': resp.text}; song_info.duration_s = extractdurationsecondsfromlrc(lyric); song_info.duration = SongInfoUtils.seconds2hms(song_info.duration_s)
                song_info.raw_data['lyric'] = lyric_result if lyric_result else song_info.raw_data['lyric']
                song_info.lyric = lyric if (lyric and (lyric not in {'NULL'})) else song_info.lyric
                # --append to song_infos
                if song_info.with_valid_download_url: song_infos.append(song_info)
                # --judgement for search_size
                if self.strict_limit_search_size_per_page and len(song_infos) >= self.search_size_per_page: break
            # --update progress
            progress.update(task_id, description=f'{self.source}.{root_source}._search >>> {search_result_idx+1} search results processed on page {page_no}')
        # failure
        except Exception as err:
            progress.update(task_id, description=f'{self.source}.{root_source}._search >>> {keyword} on page {page_no} (Error: {err})')
            self.logger_handle.error(f'{self.source}.{root_source}._search >>> {keyword} on page {page_no} (Error: {err})', disable_print=self.disable_print)
        # return
        return song_infos